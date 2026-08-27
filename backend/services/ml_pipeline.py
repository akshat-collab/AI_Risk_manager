"""Fraud-risk training pipeline.

Splits happen BEFORE any resampling. Class imbalance is handled with
class weights (and XGBoost scale_pos_weight). Oversampling is never
applied to validation or test data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from services.synthetic_data import RANDOM_SEED

NUMERIC_FEATURES = [
    "amount",
    "hour",
    "customer_age",
    "account_age_days",
    "num_transactions",
    "previous_chargebacks",
    "previous_returns",
    "transaction_frequency",
    "failed_payment_attempts",
    "is_new_device",
    "days_since_last_transaction",
    "avg_transaction_amount",
]
CATEGORICAL_FEATURES = [
    "device_type",
    "payment_method",
    "location",
    "merchant_category",
]
TARGET_COL = "is_fraud"

COLUMN_ALIASES: dict[str, list[str]] = {
    "amount": ["amount", "transaction_amount", "amt", "transactionamount"],
    "hour": ["hour", "transaction_hour", "tx_hour", "hour_of_day"],
    "customer_age": ["customer_age", "age"],
    "account_age_days": ["account_age_days", "account_age", "tenure_days"],
    "num_transactions": ["num_transactions", "n_transactions", "transaction_count"],
    "previous_chargebacks": ["previous_chargebacks", "chargebacks", "n_chargebacks"],
    "previous_returns": ["previous_returns", "returns", "n_returns"],
    "device_type": ["device_type", "device"],
    "payment_method": ["payment_method", "payment_type", "pay_method"],
    "location": ["location", "region", "geo", "country"],
    "transaction_frequency": ["transaction_frequency", "freq", "tx_frequency"],
    "failed_payment_attempts": ["failed_payment_attempts", "failed_attempts"],
    "is_new_device": ["is_new_device", "new_device"],
    "days_since_last_transaction": ["days_since_last_transaction", "days_since_last"],
    "avg_transaction_amount": ["avg_transaction_amount", "avg_amount", "mean_amount"],
    "merchant_category": ["merchant_category", "category", "mcc_group"],
    "is_fraud": ["is_fraud", "fraud", "class", "label", "target"],
    "timestamp": ["timestamp", "time", "datetime", "date", "trans_date_trans_time"],
    "transaction_id": ["transaction_id", "id", "txn_id", "trans_num"],
}


@dataclass
class SplitData:
    X_train: pd.DataFrame
    X_val: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series
    y_test: pd.Series


@dataclass
class TrainResult:
    best_model_name: str
    pipelines: dict[str, Pipeline]
    metrics: dict[str, Any]
    split_counts: dict[str, Any]
    feature_importances: list[dict[str, Any]]
    curves: dict[str, Any]
    threshold: float
    y_test: np.ndarray
    y_proba_test: np.ndarray
    X_test: pd.DataFrame
    background: pd.DataFrame


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    lower_map = {c.lower().strip(): c for c in df.columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                rename[lower_map[alias]] = canonical
                break
    out = df.rename(columns=rename).copy()
    return out


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    out = map_columns(df)
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
        if "hour" not in out.columns:
            out["hour"] = out["timestamp"].dt.hour.fillna(12).astype(int)
    if "transaction_id" not in out.columns:
        out["transaction_id"] = [f"TXN-{100000 + i}" for i in range(len(out))]
    if "is_new_device" in out.columns:
        out["is_new_device"] = (
            out["is_new_device"]
            .map({True: 1, False: 0, "true": 1, "false": 0, "1": 1, "0": 0, 1: 1, 0: 0})
            .fillna(0)
            .astype(int)
        )
    return out


def required_feature_columns() -> list[str]:
    return NUMERIC_FEATURES + CATEGORICAL_FEATURES


def validate_training_frame(df: pd.DataFrame) -> list[str]:
    missing = [c for c in required_feature_columns() + [TARGET_COL] if c not in df.columns]
    return missing


def dataset_health(df: pd.DataFrame) -> dict[str, Any]:
    fraud_cases = int(df[TARGET_COL].sum()) if TARGET_COL in df.columns else None
    n = int(len(df))
    missing_total = int(df.isna().sum().sum())
    return {
        "rows": n,
        "columns": int(df.shape[1]),
        "missing_values": missing_total,
        "fraud_cases": fraud_cases,
        "fraud_rate": (fraud_cases / n) if fraud_cases is not None and n else None,
        "column_names": list(df.columns),
    }


def _build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ]
    )


def _candidate_models(y_train: pd.Series) -> dict[str, Any]:
    n_pos = max(int(y_train.sum()), 1)
    n_neg = max(int(len(y_train) - n_pos), 1)
    scale_pos_weight = n_neg / n_pos

    models: dict[str, Any] = {
        "Logistic Regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=RANDOM_SEED,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=220,
            max_depth=12,
            min_samples_leaf=4,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_SEED,
        ),
    }
    try:
        from xgboost import XGBClassifier

        models["XGBoost"] = XGBClassifier(
            n_estimators=280,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=4,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            n_jobs=-1,
            random_state=RANDOM_SEED,
        )
    except Exception:
        pass
    return models


def stratified_splits(df: pd.DataFrame, seed: int = RANDOM_SEED) -> SplitData:
    features = required_feature_columns()
    X = df[features].copy()
    y = df[TARGET_COL].astype(int)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=seed
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=seed
    )
    return SplitData(X_train, X_val, X_test, y_train, y_val, y_test)


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def classification_metrics(y_true: np.ndarray, y_proba: np.ndarray, threshold: float) -> dict[str, Any]:
    y_pred = (y_proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    fpr = fp / (tn + fp) if (tn + fp) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": _safe_auc(y_true, y_proba),
        "pr_auc": float(average_precision_score(y_true, y_proba)) if len(np.unique(y_true)) > 1 else None,
        "specificity": float(spec),
        "false_positive_rate": float(fpr),
        "false_negative_rate": float(fnr),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "support": {
            "positives": int(y_true.sum()),
            "negatives": int((1 - y_true).sum()),
            "n": int(len(y_true)),
        },
        "threshold": float(threshold),
    }


def _downsample_curve(x: np.ndarray, y: np.ndarray, max_points: int = 80) -> tuple[list[float], list[float]]:
    if len(x) <= max_points:
        return x.astype(float).tolist(), y.astype(float).tolist()
    idx = np.linspace(0, len(x) - 1, max_points).astype(int)
    return x[idx].astype(float).tolist(), y[idx].astype(float).tolist()


def _curves(y_true: np.ndarray, y_proba: np.ndarray) -> dict[str, Any]:
    if len(np.unique(y_true)) < 2:
        return {"roc": {"fpr": [0, 1], "tpr": [0, 1]}, "pr": {"precision": [1, 0], "recall": [0, 1]}}
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    precision, recall, _ = precision_recall_curve(y_true, y_proba)
    fpr_s, tpr_s = _downsample_curve(fpr, tpr)
    rec_s, prec_s = _downsample_curve(recall, precision)
    return {
        "roc": {"fpr": fpr_s, "tpr": tpr_s},
        "pr": {"precision": prec_s, "recall": rec_s},
    }


def select_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """Pick a validation threshold that balances F1 with precision (defensive)."""
    best_t = 0.5
    best_score = -1.0
    for t in np.linspace(0.20, 0.80, 25):
        pred = (y_proba >= t).astype(int)
        f1 = f1_score(y_true, pred, zero_division=0)
        prec = precision_score(y_true, pred, zero_division=0)
        rec = recall_score(y_true, pred, zero_division=0)
        # Prefer balanced F1, with a small precision bonus to limit false positives
        score = f1 + 0.08 * prec + 0.04 * rec
        if score > best_score:
            best_score = score
            best_t = float(t)
    return round(best_t, 3)


def _transformed_feature_names(pipeline: Pipeline) -> list[str]:
    pre = pipeline.named_steps["preprocessor"]
    return [str(n) for n in pre.get_feature_names_out()]


def extract_feature_importances(pipeline: Pipeline) -> list[dict[str, Any]]:
    model = pipeline.named_steps["model"]
    names = _transformed_feature_names(pipeline)
    if hasattr(model, "coef_"):
        values = np.abs(model.coef_[0])
    elif hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    else:
        return []
    total = values.sum() or 1.0
    items = [
        {"feature": n.replace("num__", "").replace("cat__", ""), "importance": float(v / total)}
        for n, v in zip(names, values)
    ]
    items.sort(key=lambda x: x["importance"], reverse=True)
    return items[:18]


def train_and_evaluate(df: pd.DataFrame, seed: int = RANDOM_SEED) -> TrainResult:
    missing = validate_training_frame(df)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if df[TARGET_COL].nunique() < 2:
        raise ValueError("Target column must contain both fraud and non-fraud classes.")

    splits = stratified_splits(df, seed=seed)
    models = _candidate_models(splits.y_train)
    pipelines: dict[str, Pipeline] = {}
    metrics: dict[str, Any] = {}
    val_ranking: list[tuple[str, float]] = []

    for name, clf in models.items():
        pipe = Pipeline(
            steps=[
                ("preprocessor", _build_preprocessor()),
                ("model", clf),
            ]
        )
        pipe.fit(splits.X_train, splits.y_train)
        pipelines[name] = pipe

        train_proba = pipe.predict_proba(splits.X_train)[:, 1]
        val_proba = pipe.predict_proba(splits.X_val)[:, 1]
        test_proba = pipe.predict_proba(splits.X_test)[:, 1]
        threshold = select_threshold(splits.y_val.to_numpy(), val_proba)

        model_metrics = {
            "train": classification_metrics(splits.y_train.to_numpy(), train_proba, threshold),
            "validation": classification_metrics(splits.y_val.to_numpy(), val_proba, threshold),
            "test": classification_metrics(splits.y_test.to_numpy(), test_proba, threshold),
            "threshold": threshold,
        }
        metrics[name] = model_metrics
        val_f1 = model_metrics["validation"]["f1"]
        val_prec = model_metrics["validation"]["precision"]
        val_rec = model_metrics["validation"]["recall"]
        val_pr = model_metrics["validation"]["pr_auc"] or 0.0
        val_ranking.append((name, 0.40 * val_prec + 0.30 * val_f1 + 0.20 * val_pr + 0.10 * val_rec))

    val_ranking.sort(key=lambda x: x[1], reverse=True)
    best_name = val_ranking[0][0]
    best_pipe = pipelines[best_name]
    best_threshold = metrics[best_name]["threshold"]
    y_test = splits.y_test.to_numpy()
    y_proba_test = best_pipe.predict_proba(splits.X_test)[:, 1]

    split_counts = {
        "train": int(len(splits.X_train)),
        "validation": int(len(splits.X_val)),
        "test": int(len(splits.X_test)),
        "train_fraud_rate": float(splits.y_train.mean()),
        "validation_fraud_rate": float(splits.y_val.mean()),
        "test_fraud_rate": float(splits.y_test.mean()),
        "seed": seed,
        "strategy": "stratified 70/15/15 — resampling never applied before the split",
    }

    return TrainResult(
        best_model_name=best_name,
        pipelines=pipelines,
        metrics=metrics,
        split_counts=split_counts,
        feature_importances=extract_feature_importances(best_pipe),
        curves=_curves(y_test, y_proba_test),
        threshold=best_threshold,
        y_test=y_test,
        y_proba_test=y_proba_test,
        X_test=splits.X_test.reset_index(drop=True),
        background=splits.X_train.sample(n=min(400, len(splits.X_train)), random_state=seed),
    )


def score_frame(pipeline: Pipeline, df: pd.DataFrame) -> np.ndarray:
    features = required_feature_columns()
    return pipeline.predict_proba(df[features])[:, 1]


def risk_level(score_0_100: float) -> str:
    if score_0_100 >= 75:
        return "CRITICAL"
    if score_0_100 >= 50:
        return "HIGH"
    if score_0_100 >= 25:
        return "MEDIUM"
    return "LOW"


def recommendation(level: str) -> str:
    return {
        "LOW": "Allow — continue standard monitoring.",
        "MEDIUM": "Monitor — no automatic block; watch subsequent activity.",
        "HIGH": "Manual review recommended.",
        "CRITICAL": "Manual review required. Simulated hold only - this app does not block payments.",
    }[level]
