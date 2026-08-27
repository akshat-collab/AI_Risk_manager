"""Defensive monitoring: spike detection, alerts, and trend aggregates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from services.ml_pipeline import RANDOM_SEED, TARGET_COL, risk_level


def score_transactions(df: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> pd.DataFrame:
    out = df.copy()
    out["fraud_probability"] = probabilities
    out["risk_score"] = np.clip(np.round(probabilities * 100, 1), 0, 100)
    out["risk_level"] = out["risk_score"].map(risk_level)
    out["predicted_fraud"] = (probabilities >= threshold).astype(int)
    if TARGET_COL in out.columns:
        out["actual_fraud"] = out[TARGET_COL].astype(int)
    else:
        out["actual_fraud"] = np.nan
    return out


def key_signal(row: pd.Series) -> str:
    checks = [
        (row.get("previous_chargebacks", 0) >= 1, "Prior chargebacks"),
        (row.get("failed_payment_attempts", 0) >= 3, "Failed payments"),
        (row.get("is_new_device", 0) == 1, "New device"),
        (row.get("account_age_days", 999) < 14, "New account"),
        (row.get("hour", 12) <= 5 or row.get("hour", 12) >= 23, "Off-hours timing"),
        (row.get("transaction_frequency", 0) >= 9, "High frequency"),
        (row.get("amount", 0) >= 700, "High amount"),
        (row.get("previous_returns", 0) >= 5, "Return history"),
    ]
    for cond, label in checks:
        if cond:
            return label
    return "Composite score"


def transactions_payload(scored: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    frame = scored.sort_values("timestamp", ascending=False) if "timestamp" in scored.columns else scored
    if limit:
        frame = frame.head(limit)
    rows = []
    for _, row in frame.iterrows():
        ts = row["timestamp"] if "timestamp" in row else None
        status = "REVIEW" if row["risk_level"] in {"HIGH", "CRITICAL"} else "MONITOR" if row["risk_level"] == "MEDIUM" else "CLEAR"
        rows.append(
            {
                "transaction_id": str(row.get("transaction_id")),
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") and pd.notna(ts) else None,
                "amount": float(row.get("amount", 0) or 0),
                "risk_score": float(row["risk_score"]),
                "risk_level": row["risk_level"],
                "key_signal": key_signal(row),
                "status": status,
                "payment_method": str(row.get("payment_method", "")),
                "device_type": str(row.get("device_type", "")),
                "location": str(row.get("location", "")),
                "predicted_fraud": int(row["predicted_fraud"]),
                "actual_fraud": None if pd.isna(row.get("actual_fraud")) else int(row["actual_fraud"]),
            }
        )
    return rows


def risk_distribution(scored: pd.DataFrame) -> dict[str, Any]:
    counts = scored["risk_level"].value_counts().to_dict()
    n = max(len(scored), 1)
    order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    items = []
    for level in order:
        c = int(counts.get(level, 0))
        items.append({"level": level, "count": c, "pct": round(100.0 * c / n, 2)})
    return {"n": int(len(scored)), "items": items}


def kpis(scored: pd.DataFrame, test_metrics: dict[str, Any] | None) -> dict[str, Any]:
    high_risk = scored[scored["risk_level"].isin(["HIGH", "CRITICAL"])]
    fraud_prevented = 0
    loss_avoided = 0.0
    if "actual_fraud" in scored.columns and scored["actual_fraud"].notna().any():
        caught = scored[(scored["predicted_fraud"] == 1) & (scored["actual_fraud"] == 1)]
        fraud_prevented = int(len(caught))
        loss_avoided = float(caught["amount"].sum()) if "amount" in caught.columns else 0.0

    week = None
    prev = None
    if "timestamp" in scored.columns:
        ts = pd.to_datetime(scored["timestamp"], utc=True)
        latest = ts.max()
        week = scored[ts >= latest - pd.Timedelta(days=7)]
        prev = scored[(ts >= latest - pd.Timedelta(days=14)) & (ts < latest - pd.Timedelta(days=7))]

    def trend(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return round(100.0 * (current - previous) / previous, 1)

    high_now = len(week[week["risk_level"].isin(["HIGH", "CRITICAL"])]) if week is not None and len(week) else len(high_risk)
    high_prev = len(prev[prev["risk_level"].isin(["HIGH", "CRITICAL"])]) if prev is not None and len(prev) else high_now

    avg_risk = float(scored["risk_score"].mean()) if len(scored) else 0.0
    return {
        "transactions_analyzed": int(len(scored)),
        "high_risk_transactions": int(len(high_risk)),
        "fraud_prevented": fraud_prevented,
        "estimated_loss_avoided": round(loss_avoided, 2),
        "average_risk_score": round(avg_risk, 1),
        "model_precision": test_metrics.get("precision") if test_metrics else None,
        "model_recall": test_metrics.get("recall") if test_metrics else None,
        "trends": {
            "transactions_analyzed": trend(len(week) if week is not None else len(scored), len(prev) if prev is not None else len(scored)),
            "high_risk_transactions": trend(high_now, high_prev),
            "fraud_prevented": 0.0,
            "estimated_loss_avoided": 0.0,
            "model_precision": 0.0,
            "model_recall": 0.0,
        },
    }


def build_trends(scored: pd.DataFrame) -> dict[str, Any]:
    if "timestamp" not in scored.columns:
        return {}
    frame = scored.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.tz_convert("UTC").dt.date.astype(str)

    daily = (
        frame.groupby("date")
        .agg(
            transactions=("transaction_id", "count"),
            high_risk=("risk_level", lambda s: int(s.isin(["HIGH", "CRITICAL"]).sum())),
            avg_amount=("amount", "mean"),
            avg_risk=("risk_score", "mean"),
            predicted_rate=("predicted_fraud", "mean"),
            chargebacks=("previous_chargebacks", "mean"),
            returns=("previous_returns", "mean"),
        )
        .reset_index()
        .sort_values("date")
    )
    if "actual_fraud" in frame.columns and frame["actual_fraud"].notna().any():
        fraud_daily = frame.groupby("date")["actual_fraud"].mean().reset_index(name="fraud_rate")
        daily = daily.merge(fraud_daily, on="date", how="left")
    else:
        daily["fraud_rate"] = daily["predicted_rate"]

    daily["high_risk_rate"] = daily["high_risk"] / daily["transactions"].clip(lower=1)

    def group_risk(col: str) -> list[dict[str, Any]]:
        g = (
            frame.groupby(col)
            .agg(
                count=("transaction_id", "count"),
                avg_risk=("risk_score", "mean"),
                high_risk=("risk_level", lambda s: int(s.isin(["HIGH", "CRITICAL"]).sum())),
            )
            .reset_index()
        )
        return [
            {
                "name": str(r[col]),
                "count": int(r["count"]),
                "avg_risk": round(float(r["avg_risk"]), 2),
                "high_risk": int(r["high_risk"]),
            }
            for _, r in g.iterrows()
        ]

    return {
        "daily": [
            {
                "date": r["date"],
                "transactions": int(r["transactions"]),
                "high_risk": int(r["high_risk"]),
                "high_risk_rate": round(float(r["high_risk_rate"]), 4),
                "avg_amount": round(float(r["avg_amount"]), 2),
                "avg_risk": round(float(r["avg_risk"]), 2),
                "fraud_rate": round(float(r["fraud_rate"]), 4) if pd.notna(r["fraud_rate"]) else None,
                "chargebacks": round(float(r["chargebacks"]), 3),
                "returns": round(float(r["returns"]), 3),
            }
            for _, r in daily.iterrows()
        ],
        "by_payment_method": group_risk("payment_method"),
        "by_device_type": group_risk("device_type"),
        "by_location": group_risk("location"),
    }


def detect_spike(scored: pd.DataFrame, window: int = 14, z_thresh: float = 2.35) -> dict[str, Any] | None:
    if "timestamp" not in scored.columns or len(scored) < 30:
        return None
    frame = scored.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.date
    daily = frame.groupby("date").agg(
        n=("transaction_id", "count"),
        high_risk=("risk_level", lambda s: s.isin(["HIGH", "CRITICAL"]).sum()),
    )
    daily["rate"] = daily["high_risk"] / daily["n"].clip(lower=1)
    if len(daily) < 8:
        return None

    rates = daily["rate"].to_numpy(dtype=float)
    iso_flag = False
    if len(rates) >= 12:
        iso = IsolationForest(contamination=0.08, random_state=RANDOM_SEED)
        iso_pred = iso.fit_predict(rates.reshape(-1, 1))
        iso_flag = iso_pred[-1] == -1

    series = daily["rate"]
    roll_mean = series.rolling(window=min(window, len(series) - 1), min_periods=5).mean()
    roll_std = series.rolling(window=min(window, len(series) - 1), min_periods=5).std().replace(0, np.nan)
    z = (series - roll_mean) / roll_std
    last_date = series.index[-1]
    last_rate = float(series.iloc[-1])
    last_z = float(z.iloc[-1]) if pd.notna(z.iloc[-1]) else 0.0
    baseline = float(roll_mean.iloc[-1]) if pd.notna(roll_mean.iloc[-1]) else float(series.iloc[:-1].mean())
    last_n = int(daily.iloc[-1]["n"])
    last_high = int(daily.iloc[-1]["high_risk"])

    if last_z >= z_thresh or (iso_flag and last_rate > baseline * 1.35):
        return {
            "detected": True,
            "title": "RISK SPIKE DETECTED",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "window_date": str(last_date),
            "current_risk_rate": round(last_rate, 4),
            "expected_baseline": round(baseline, 4),
            "deviation_z": round(last_z, 2),
            "affected_transactions": last_n,
            "high_risk_in_window": last_high,
            "method": "rolling z-score + Isolation Forest",
        }
    return {
        "detected": False,
        "title": "No spike detected",
        "detection_time": datetime.now(timezone.utc).isoformat(),
        "window_date": str(last_date),
        "current_risk_rate": round(last_rate, 4),
        "expected_baseline": round(baseline, 4),
        "deviation_z": round(last_z, 2),
        "affected_transactions": last_n,
        "high_risk_in_window": last_high,
        "method": "rolling z-score + Isolation Forest",
    }


def build_alerts(
    scored: pd.DataFrame,
    spike: dict[str, Any] | None,
    test_metrics: dict[str, Any] | None,
    is_demo: bool,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    alerts: list[dict[str, Any]] = []

    if spike and spike.get("detected"):
        alerts.append(
            {
                "id": "spike-critical",
                "severity": "CRITICAL",
                "color": "red",
                "title": "Critical fraud-risk spike",
                "timestamp": spike.get("detection_time") or now,
                "description": (
                    f"High-risk rate {spike['current_risk_rate']:.2%} vs baseline "
                    f"{spike['expected_baseline']:.2%} (z={spike['deviation_z']}). "
                    f"{spike['affected_transactions']} transactions in the latest window."
                ),
                "recommended_action": "Increase manual review coverage and inspect recent high-risk clusters. Do not auto-block customers.",
            }
        )

    unusual = scored[scored["risk_level"] == "CRITICAL"]
    if len(unusual) >= max(8, int(0.02 * len(scored))):
        alerts.append(
            {
                "id": "unusual-activity",
                "severity": "HIGH",
                "color": "orange",
                "title": "Unusual transaction activity",
                "timestamp": now,
                "description": f"{len(unusual)} transactions currently sit in CRITICAL risk. Review device, location, and chargeback clusters.",
                "recommended_action": "Open the transaction table filtered to CRITICAL and assign reviewers.",
            }
        )

    if test_metrics:
        prec = test_metrics.get("precision") or 0
        rec = test_metrics.get("recall") or 0
        if prec < 0.45:
            alerts.append(
                {
                    "id": "fp-rate",
                    "severity": "MEDIUM",
                    "color": "yellow",
                    "title": "High false-positive pressure",
                    "timestamp": now,
                    "description": f"Held-out test precision is {prec:.1%}. Legitimate customers may be over-flagged at the current threshold.",
                    "recommended_action": "Raise the decision threshold in Cost Analysis until precision recovers, then re-check recall.",
                }
            )
        if rec < 0.40:
            alerts.append(
                {
                    "id": "fn-rate",
                    "severity": "HIGH",
                    "color": "orange",
                    "title": "Model may miss fraud cases",
                    "timestamp": now,
                    "description": f"Held-out test recall is {rec:.1%}. False negatives can translate directly into chargeback losses.",
                    "recommended_action": "Review feature coverage and consider a lower threshold only if false-positive cost remains acceptable.",
                }
            )

    alerts.append(
        {
            "id": "model-status",
            "severity": "INFO",
            "color": "blue",
            "title": "Model performance snapshot",
            "timestamp": now,
            "description": (
                "Metrics are computed on a completely held-out test split. "
                + ("Results use DEMO / SYNTHETIC DATA and are not real-world performance." if is_demo else "Results reflect the uploaded dataset only.")
            ),
            "recommended_action": "Treat scores as decision support. Keep a human in the loop for HIGH and CRITICAL cases.",
        }
    )
    return alerts


def cost_curve(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    amounts: np.ndarray | None,
    fp_cost: float,
    fn_cost: float,
    avg_value: float,
) -> dict[str, Any]:
    points = []
    best = None
    for t in np.linspace(0.05, 0.95, 37):
        pred = (y_proba >= t).astype(int)
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        tp = int(((pred == 1) & (y_true == 1)).sum())
        tn = int(((pred == 0) & (y_true == 0)).sum())
        fn_dollar = fn_cost
        if amounts is not None:
            missed = amounts[(pred == 0) & (y_true == 1)]
            fn_dollar = float(missed.sum()) if len(missed) else fn * avg_value
        else:
            fn_dollar = fn * max(fn_cost, avg_value)
        fp_dollar = fp * fp_cost
        total = fp_dollar + fn_dollar
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        point = {
            "threshold": round(float(t), 3),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "true_negatives": tn,
            "fp_cost": round(float(fp_dollar), 2),
            "fn_cost": round(float(fn_dollar), 2),
            "total_cost": round(float(total), 2),
        }
        points.append(point)
        if best is None or total < best["total_cost"]:
            best = point
    return {"points": points, "recommended": best}
