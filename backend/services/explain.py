"""Transparent, model-derived explanations.

Contributions are indicators from the fitted model (coefficients or
importance-weighted deviations), not proof of fraud.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from services.ml_pipeline import CATEGORICAL_FEATURES, NUMERIC_FEATURES

REASON_MAP = {
    "amount": ("Unusual transaction amount", "Transaction value differs from typical customer spend."),
    "hour": ("Abnormal transaction timing", "Activity occurred outside typical purchasing hours."),
    "customer_age": ("Customer age profile", "Age-related pattern contributed to the score."),
    "account_age_days": ("New or young account", "Short account tenure increased modeled risk."),
    "num_transactions": ("Transaction volume", "Historical volume pattern influenced the score."),
    "previous_chargebacks": ("Previous chargeback history", "Prior chargebacks are a strong defensive risk signal."),
    "previous_returns": ("Return history", "Elevated return activity contributed to the score."),
    "transaction_frequency": ("High transaction frequency", "Burst-like activity relative to the baseline."),
    "failed_payment_attempts": ("Failed payment attempts", "Repeated failed authorizations raised the score."),
    "is_new_device": ("New or unrecognized device", "Device novelty was a contributing indicator."),
    "days_since_last_transaction": ("Activity gap", "Time since last purchase differed from the baseline."),
    "avg_transaction_amount": ("Spend baseline shift", "Average historical spend influenced the prediction."),
    "device_type": ("Device type", "Device category contributed to the modeled risk."),
    "payment_method": ("Payment method", "Payment rail was associated with higher modeled risk."),
    "location": ("Location / region", "Geographic pattern contributed to the score."),
    "merchant_category": ("Merchant category", "Category mix influenced the prediction."),
}


def _original_feature(transformed_name: str) -> str:
    name = transformed_name.replace("num__", "").replace("cat__", "")
    for feat in NUMERIC_FEATURES + CATEGORICAL_FEATURES:
        if name == feat or name.startswith(f"{feat}_"):
            return feat
    return name.split("_")[0]


def explain_instance(
    pipeline: Pipeline,
    row: pd.DataFrame,
    background: pd.DataFrame,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    pre = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    names = [str(n) for n in pre.get_feature_names_out()]
    x = pre.transform(row[NUMERIC_FEATURES + CATEGORICAL_FEATURES])[0]
    bg = pre.transform(background[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    bg_mean = bg.mean(axis=0)
    delta = x - bg_mean

    if hasattr(model, "coef_"):
        contrib = model.coef_[0] * x
    elif hasattr(model, "feature_importances_"):
        contrib = model.feature_importances_ * delta
    else:
        contrib = delta

    grouped: dict[str, float] = {}
    for name, value in zip(names, contrib):
        orig = _original_feature(name)
        grouped[orig] = grouped.get(orig, 0.0) + float(value)

    items = sorted(grouped.items(), key=lambda kv: abs(kv[1]), reverse=True)
    explanations: list[dict[str, Any]] = []
    for feat, value in items[:top_k]:
        title, detail = REASON_MAP.get(
            feat, (feat.replace("_", " ").title(), "Model-derived indicator.")
        )
        raw_val = row.iloc[0][feat] if feat in row.columns else None
        explanations.append(
            {
                "feature": feat,
                "title": title,
                "detail": detail,
                "contribution": round(float(value), 4),
                "direction": "increases_risk" if value > 0 else "decreases_risk",
                "value": None if raw_val is None or (isinstance(raw_val, float) and np.isnan(raw_val)) else (
                    int(raw_val) if isinstance(raw_val, (np.integer,)) else (
                        float(raw_val) if isinstance(raw_val, (float, np.floating)) else str(raw_val)
                    )
                ),
                "disclaimer": "Model-derived indicator, not proof of fraud.",
            }
        )
    return explanations
