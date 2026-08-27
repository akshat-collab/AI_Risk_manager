"""Defensive input validation. No shell execution, no credential capture."""

from __future__ import annotations

ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 50_000

ALLOWED_DEVICE_TYPES = {"mobile", "desktop", "tablet"}
ALLOWED_PAYMENT_METHODS = {
    "credit_card",
    "debit_card",
    "paypal",
    "bank_transfer",
    "wallet",
}
ALLOWED_LOCATIONS = {
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
}
ALLOWED_MERCHANT_CATEGORIES = {
    "electronics",
    "fashion",
    "travel",
    "grocery",
    "digital_goods",
    "luxury",
    "subscriptions",
}


def validate_upload_filename(filename: str) -> str:
    name = (filename or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError("Invalid filename.")
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("Only .csv or .xlsx files are allowed.")
    return name


def validate_content_type(content_type: str | None) -> None:
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file type.")
