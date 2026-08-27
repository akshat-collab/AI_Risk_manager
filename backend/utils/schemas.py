from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from utils.security import (
    ALLOWED_DEVICE_TYPES,
    ALLOWED_LOCATIONS,
    ALLOWED_MERCHANT_CATEGORIES,
    ALLOWED_PAYMENT_METHODS,
)

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class PredictRequest(BaseModel):
    amount: float = Field(..., ge=0, le=1_000_000_000)
    hour: int = Field(..., ge=0, le=23)
    customer_age: int = Field(..., ge=18, le=100)
    account_age_days: int = Field(..., ge=0, le=20_000)
    num_transactions: int = Field(..., ge=0, le=100_000)
    previous_chargebacks: int = Field(..., ge=0, le=100)
    previous_returns: int = Field(..., ge=0, le=1_000)
    device_type: str
    payment_method: str
    location: str
    transaction_frequency: float = Field(..., ge=0, le=1_000)
    failed_payment_attempts: int = Field(..., ge=0, le=50)
    is_new_device: bool = False
    days_since_last_transaction: int = Field(3, ge=0, le=3_650)
    avg_transaction_amount: float = Field(85.0, ge=0, le=1_000_000_000)
    merchant_category: str = "electronics"

    @field_validator("device_type")
    @classmethod
    def _device(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_DEVICE_TYPES:
            raise ValueError(f"device_type must be one of {sorted(ALLOWED_DEVICE_TYPES)}")
        return v

    @field_validator("payment_method")
    @classmethod
    def _pay(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(ALLOWED_PAYMENT_METHODS)}")
        return v

    @field_validator("location")
    @classmethod
    def _loc(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ALLOWED_LOCATIONS:
            raise ValueError(f"location must be one of {sorted(ALLOWED_LOCATIONS)}")
        return v

    @field_validator("merchant_category")
    @classmethod
    def _cat(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_MERCHANT_CATEGORIES:
            raise ValueError(
                f"merchant_category must be one of {sorted(ALLOWED_MERCHANT_CATEGORIES)}"
            )
        return v


class CostConfig(BaseModel):
    cost_false_positive: float = Field(25.0, ge=0, le=1_000_000)
    cost_false_negative: float = Field(250.0, ge=0, le=1_000_000)
    average_transaction_value: float = Field(120.0, ge=0, le=1_000_000)
    threshold: float = Field(0.5, ge=0.05, le=0.95)


class TrainRequest(BaseModel):
    use_demo: bool = False
