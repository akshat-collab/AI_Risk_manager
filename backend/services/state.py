"""In-memory application state for the MVP runtime."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from services.explain import explain_instance
from services.ml_pipeline import (
    RANDOM_SEED,
    TARGET_COL,
    dataset_health,
    normalize_dataset,
    recommendation,
    required_feature_columns,
    risk_level,
    score_frame,
    train_and_evaluate,
    validate_training_frame,
)
from services.monitoring import (
    build_alerts,
    build_trends,
    cost_curve,
    detect_spike,
    kpis,
    risk_distribution,
    score_transactions,
    transactions_payload,
)
from services.synthetic_data import generate_synthetic_transactions
from utils.security import MAX_ROWS, MAX_UPLOAD_BYTES

MODELS_DIR = None  # set from main


class AppState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.is_demo = True
        self.dataset = pd.DataFrame()
        self.scored = pd.DataFrame()
        self.pipelines: dict[str, Pipeline] = {}
        self.best_model_name: str | None = None
        self.metrics: dict[str, Any] = {}
        self.split_counts: dict[str, Any] = {}
        self.feature_importances: list[dict[str, Any]] = []
        self.curves: dict[str, Any] = {}
        self.threshold = 0.5
        self.y_test: np.ndarray | None = None
        self.y_proba_test: np.ndarray | None = None
        self.X_test: pd.DataFrame | None = None
        self.background: pd.DataFrame | None = None
        self.alerts: list[dict[str, Any]] = []
        self.spike: dict[str, Any] | None = None
        self.trends: dict[str, Any] = {}
        self.health: dict[str, Any] = {}
        self.last_trained: str | None = None
        self.model_online = False
        self.error: str | None = None
        self.dataset_name = "DEMO DATASET"

    def bootstrap_demo(self) -> None:
        df = generate_synthetic_transactions(n=8_000, seed=RANDOM_SEED, inject_spike=True)
        self.fit_dataframe(df, is_demo=True, dataset_name="DEMO / SYNTHETIC DATASET")

    def fit_dataframe(self, df: pd.DataFrame, is_demo: bool, dataset_name: str) -> dict[str, Any]:
        df = normalize_dataset(df)
        if len(df) > MAX_ROWS:
            df = df.sample(n=MAX_ROWS, random_state=RANDOM_SEED).reset_index(drop=True)
        missing = validate_training_frame(df)
        if missing:
            raise ValueError(
                "Dataset is missing required columns: "
                + ", ".join(missing)
                + ". Expected features: "
                + ", ".join(required_feature_columns())
                + " and target is_fraud."
            )

        result = train_and_evaluate(df)
        best = result.pipelines[result.best_model_name]
        proba = score_frame(best, df)
        scored = score_transactions(df, proba, result.threshold)
        test_metrics = result.metrics[result.best_model_name]["test"]
        spike = detect_spike(scored)
        alerts = build_alerts(scored, spike, test_metrics, is_demo=is_demo)

        with self.lock:
            self.dataset = df
            self.scored = scored
            self.pipelines = result.pipelines
            self.best_model_name = result.best_model_name
            self.metrics = result.metrics
            self.split_counts = result.split_counts
            self.feature_importances = result.feature_importances
            self.curves = result.curves
            self.threshold = result.threshold
            self.y_test = result.y_test
            self.y_proba_test = result.y_proba_test
            self.X_test = result.X_test
            self.background = result.background
            self.alerts = alerts
            self.spike = spike
            self.trends = build_trends(scored)
            self.health = dataset_health(df)
            self.last_trained = datetime.now(timezone.utc).isoformat()
            self.model_online = True
            self.is_demo = is_demo
            self.dataset_name = dataset_name
            self.error = None

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        test = self._test_metrics()
        return {
            "model_online": self.model_online,
            "is_demo": self.is_demo,
            "dataset_name": self.dataset_name,
            "last_trained": self.last_trained,
            "best_model": self.best_model_name,
            "threshold": self.threshold,
            "dataset_health": self.health,
            "kpis": kpis(self.scored, test) if len(self.scored) else None,
            "risk_distribution": risk_distribution(self.scored) if len(self.scored) else None,
            "split_counts": self.split_counts,
        }

    def _test_metrics(self) -> dict[str, Any] | None:
        if not self.best_model_name:
            return None
        return self.metrics[self.best_model_name]["test"]

    def predict_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.model_online or self.best_model_name is None:
            raise RuntimeError("Model is not online.")
        row = pd.DataFrame(
            [
                {
                    "amount": payload["amount"],
                    "hour": payload["hour"],
                    "customer_age": payload["customer_age"],
                    "account_age_days": payload["account_age_days"],
                    "num_transactions": payload["num_transactions"],
                    "previous_chargebacks": payload["previous_chargebacks"],
                    "previous_returns": payload["previous_returns"],
                    "device_type": payload["device_type"],
                    "payment_method": payload["payment_method"],
                    "location": payload["location"],
                    "transaction_frequency": payload["transaction_frequency"],
                    "failed_payment_attempts": payload["failed_payment_attempts"],
                    "is_new_device": int(payload["is_new_device"]),
                    "days_since_last_transaction": payload["days_since_last_transaction"],
                    "avg_transaction_amount": payload["avg_transaction_amount"],
                    "merchant_category": payload["merchant_category"],
                }
            ]
        )
        pipe = self.pipelines[self.best_model_name]
        proba = float(pipe.predict_proba(row)[0, 1])
        score = float(np.clip(round(proba * 100, 1), 0, 100))
        level = risk_level(score)
        background = self.background if self.background is not None else row
        explanations = explain_instance(pipe, row, background)
        return {
            "risk_score": score,
            "probability": round(proba, 4),
            "risk_level": level,
            "recommendation": recommendation(level),
            "threshold": self.threshold,
            "predicted_fraud": bool(proba >= self.threshold),
            "model": self.best_model_name,
            "is_demo": self.is_demo,
            "explanations": explanations,
            "disclaimer": (
                "These are model-derived indicators, not proof of fraud. "
                "This platform is defensive decision-support only and does not block payments."
            ),
        }

    def performance_payload(self) -> dict[str, Any]:
        return {
            "is_demo": self.is_demo,
            "best_model": self.best_model_name,
            "threshold": self.threshold,
            "split": self.split_counts,
            "models": self.metrics,
            "feature_importances": self.feature_importances,
            "curves": self.curves,
            "disclaimer": (
                "DEMO / SYNTHETIC DATA — not real-world performance."
                if self.is_demo
                else "Metrics are from a held-out test set for the uploaded data only."
            ),
        }

    def cost_payload(self, fp_cost: float, fn_cost: float, avg_value: float, threshold: float | None) -> dict[str, Any]:
        if self.y_test is None or self.y_proba_test is None:
            raise RuntimeError("Model is not online.")
        amounts = None
        if self.X_test is not None and "amount" in self.X_test.columns:
            amounts = self.X_test["amount"].to_numpy()
        curve = cost_curve(self.y_test, self.y_proba_test, amounts, fp_cost, fn_cost, avg_value)
        t = float(threshold if threshold is not None else self.threshold)
        nearest = min(curve["points"], key=lambda p: abs(p["threshold"] - t))
        return {
            "is_demo": self.is_demo,
            "operating_threshold": t,
            "selected": nearest,
            "recommended": curve["recommended"],
            "curve": curve["points"],
            "config": {
                "cost_false_positive": fp_cost,
                "cost_false_negative": fn_cost,
                "average_transaction_value": avg_value,
            },
            "note": "False positives can incorrectly flag legitimate customers. Tune the threshold with cost, not accuracy alone.",
        }

    def load_upload(self, filename: str, raw: bytes) -> dict[str, Any]:
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("File exceeds the 10 MB upload limit.")
        name = filename.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        elif name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(raw))
        else:
            raise ValueError("Only CSV or XLSX files are supported.")
        if df.empty:
            raise ValueError("The uploaded file has no rows.")
        return self.fit_dataframe(df, is_demo=False, dataset_name=filename)


state = AppState()
