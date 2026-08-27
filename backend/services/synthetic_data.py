"""Generate a clearly labeled DEMO / SYNTHETIC transaction dataset.

Fraud labels are simulated from defensive risk factors plus noise so the
model has a learnable signal without claiming real-world performance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

RANDOM_SEED = 42

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "bank_transfer", "wallet"]
LOCATIONS = [
    "US-CA",
    "US-NY",
    "US-TX",
    "GB-LON",
    "DE-BER",
    "IN-DEL",
    "FR-PAR",
    "AU-SYD",
    "BR-SAO",
    "SG-SIN",
]
MERCHANT_CATEGORIES = [
    "electronics",
    "fashion",
    "travel",
    "grocery",
    "digital_goods",
    "luxury",
    "subscriptions",
]

FEATURE_COLUMNS = [
    "transaction_id",
    "timestamp",
    "amount",
    "hour",
    "customer_age",
    "account_age_days",
    "num_transactions",
    "previous_chargebacks",
    "previous_returns",
    "device_type",
    "payment_method",
    "location",
    "transaction_frequency",
    "failed_payment_attempts",
    "is_new_device",
    "days_since_last_transaction",
    "avg_transaction_amount",
    "merchant_category",
    "is_fraud",
]


def generate_synthetic_transactions(
    n: int = 8_000,
    seed: int = RANDOM_SEED,
    inject_spike: bool = True,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)

    device_type = rng.choice(DEVICE_TYPES, size=n, p=[0.58, 0.32, 0.10])
    payment_method = rng.choice(
        PAYMENT_METHODS, size=n, p=[0.42, 0.28, 0.14, 0.08, 0.08]
    )
    location = rng.choice(LOCATIONS, size=n)
    merchant_category = rng.choice(MERCHANT_CATEGORIES, size=n)

    customer_age = rng.integers(18, 78, size=n)
    account_age_days = np.clip(
        rng.lognormal(mean=5.6, sigma=1.05, size=n).astype(int), 1, 4_000
    )
    num_transactions = np.clip(
        rng.lognormal(mean=3.2, sigma=0.9, size=n).astype(int), 1, 2_000
    )
    previous_chargebacks = rng.choice(
        [0, 1, 2, 3, 4], size=n, p=[0.91, 0.05, 0.025, 0.01, 0.005]
    )
    previous_returns = np.clip(rng.poisson(1.1, size=n), 0, 40)
    transaction_frequency = np.clip(rng.gamma(2.1, 1.4, size=n), 0.1, 40)
    failed_payment_attempts = rng.choice(
        [0, 1, 2, 3, 4, 5, 6], size=n, p=[0.62, 0.18, 0.09, 0.05, 0.03, 0.02, 0.01]
    )
    is_new_device = rng.binomial(1, 0.18, size=n)
    days_since_last_transaction = np.clip(
        rng.exponential(scale=6.5, size=n).astype(int), 0, 120
    )
    avg_transaction_amount = np.clip(rng.lognormal(4.1, 0.55, size=n), 8, 2_500)
    amount = np.clip(
        avg_transaction_amount * rng.lognormal(0.0, 0.55, size=n), 3, 8_000
    )

    # Mix of business-hour and off-hour activity
    hour = rng.choice(
        np.arange(24),
        size=n,
        p=_hour_probs(),
    )

    seconds_range = int((end - start).total_seconds())
    offsets = rng.integers(0, seconds_range, size=n)
    timestamps = [start + timedelta(seconds=int(s)) for s in offsets]

    if inject_spike:
        # Concentrate extra late-night, new-account activity in the last 48 hours
        spike_n = max(180, n // 45)
        spike_idx = rng.choice(n, size=spike_n, replace=False)
        for i in spike_idx:
            timestamps[i] = end - timedelta(hours=float(rng.uniform(1, 48)))
            hour[i] = int(rng.choice([0, 1, 2, 3, 4, 23]))
            amount[i] = float(amount[i] * rng.uniform(2.2, 6.0))
            account_age_days[i] = int(min(account_age_days[i], rng.integers(1, 12)))
            is_new_device[i] = 1
            failed_payment_attempts[i] = int(max(failed_payment_attempts[i], rng.integers(2, 6)))
            transaction_frequency[i] = float(max(transaction_frequency[i], rng.uniform(8, 22)))

    amount_ratio = amount / (avg_transaction_amount + 1e-6)
    late_night = ((hour <= 5) | (hour >= 23)).astype(float)
    new_account = (account_age_days < 14).astype(float)
    high_amount = (amount > 700).astype(float)
    spike_window = np.array(
        [(end - ts).total_seconds() < 48 * 3600 for ts in timestamps], dtype=float
    )

    logit = (
        -4.55
        + 1.55 * high_amount
        + 1.15 * late_night
        + 1.65 * new_account
        + 1.85 * (previous_chargebacks > 0).astype(float)
        + 0.55 * np.minimum(previous_chargebacks, 4)
        + 1.25 * (failed_payment_attempts >= 3).astype(float)
        + 0.95 * is_new_device
        + 0.85 * (transaction_frequency > 9).astype(float)
        + 1.05 * (amount_ratio > 4).astype(float)
        + 0.55 * (merchant_category == "luxury").astype(float)
        + 0.40 * (payment_method == "wallet").astype(float)
        + 1.35 * spike_window * inject_spike
    )
    logit += rng.normal(0, 0.55, size=n)
    p = 1.0 / (1.0 + np.exp(-logit))
    p = np.clip(p, 0.004, 0.92)
    is_fraud = rng.binomial(1, p)

    # Small label noise so the problem is not perfectly separable
    flip = rng.random(n) < 0.025
    is_fraud = np.where(flip, 1 - is_fraud, is_fraud)

    ids = [f"TXN-{100000 + i}" for i in range(n)]

    df = pd.DataFrame(
        {
            "transaction_id": ids,
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "amount": np.round(amount, 2),
            "hour": hour.astype(int),
            "customer_age": customer_age.astype(int),
            "account_age_days": account_age_days.astype(int),
            "num_transactions": num_transactions.astype(int),
            "previous_chargebacks": previous_chargebacks.astype(int),
            "previous_returns": previous_returns.astype(int),
            "device_type": device_type,
            "payment_method": payment_method,
            "location": location,
            "transaction_frequency": np.round(transaction_frequency, 2),
            "failed_payment_attempts": failed_payment_attempts.astype(int),
            "is_new_device": is_new_device.astype(int),
            "days_since_last_transaction": days_since_last_transaction.astype(int),
            "avg_transaction_amount": np.round(avg_transaction_amount, 2),
            "merchant_category": merchant_category,
            "is_fraud": is_fraud.astype(int),
            "is_demo": 1,
        }
    )
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["transaction_id"] = [f"TXN-{100000 + i}" for i in range(len(df))]
    return df


def _hour_probs() -> np.ndarray:
    weights = np.array(
        [1.0, 0.8, 0.7, 0.6, 0.7, 1.1, 2.0, 3.2, 4.0, 4.4, 4.6, 4.8]
        + [5.0, 4.8, 4.6, 4.4, 4.5, 4.8, 4.6, 4.0, 3.2, 2.4, 1.8, 1.3]
    )
    return weights / weights.sum()
