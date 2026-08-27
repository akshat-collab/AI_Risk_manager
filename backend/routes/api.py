from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from services.state import state
from utils.schemas import CostConfig, PredictRequest, TrainRequest
from utils.security import MAX_UPLOAD_BYTES, validate_content_type, validate_upload_filename

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_online": state.model_online,
        "is_demo": state.is_demo,
        "last_trained": state.last_trained,
        "best_model": state.best_model_name,
        "dataset_name": state.dataset_name,
    }


@router.get("/overview")
def overview() -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    snap = state.snapshot()
    snap["hero"] = state._test_metrics()
    snap["spike"] = state.spike
    return snap


@router.post("/predict")
def predict(body: PredictRequest) -> dict:
    try:
        return state.predict_row(body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"Prediction failed: {exc}") from exc


@router.post("/analyze")
def analyze(body: PredictRequest) -> dict:
    return predict(body)


@router.get("/transactions")
def transactions(
    q: str | None = None,
    risk_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    sort: str = "timestamp",
    order: str = "desc",
) -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    from services.monitoring import transactions_payload

    rows = transactions_payload(state.scored)
    if q:
        needle = q.lower()
        rows = [
            r
            for r in rows
            if needle in str(r["transaction_id"]).lower()
            or needle in str(r["key_signal"]).lower()
            or needle in str(r["location"]).lower()
        ]
    if risk_level and risk_level.upper() != "ALL":
        rows = [r for r in rows if r["risk_level"] == risk_level.upper()]
    if date_from:
        rows = [r for r in rows if r.get("timestamp") and r["timestamp"][:10] >= date_from]
    if date_to:
        rows = [r for r in rows if r.get("timestamp") and r["timestamp"][:10] <= date_to]
    reverse = order.lower() != "asc"
    key = sort if sort in {"timestamp", "amount", "risk_score"} else "timestamp"
    rows.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=reverse)
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "is_demo": state.is_demo,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": page_rows,
    }


@router.get("/transactions/{transaction_id}")
def transaction_detail(transaction_id: str) -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    hit = state.scored[state.scored["transaction_id"].astype(str) == transaction_id]
    if hit.empty:
        raise HTTPException(404, "Transaction not found.")
    row = hit.iloc[0]
    payload = {
        "amount": float(row["amount"]),
        "hour": int(row["hour"]),
        "customer_age": int(row["customer_age"]),
        "account_age_days": int(row["account_age_days"]),
        "num_transactions": int(row["num_transactions"]),
        "previous_chargebacks": int(row["previous_chargebacks"]),
        "previous_returns": int(row["previous_returns"]),
        "device_type": str(row["device_type"]),
        "payment_method": str(row["payment_method"]),
        "location": str(row["location"]),
        "transaction_frequency": float(row["transaction_frequency"]),
        "failed_payment_attempts": int(row["failed_payment_attempts"]),
        "is_new_device": bool(row["is_new_device"]),
        "days_since_last_transaction": int(row["days_since_last_transaction"]),
        "avg_transaction_amount": float(row["avg_transaction_amount"]),
        "merchant_category": str(row["merchant_category"]),
    }
    result = state.predict_row(payload)
    result["transaction"] = {
        "transaction_id": transaction_id,
        "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else None,
        "amount": payload["amount"],
        "risk_score": float(row["risk_score"]),
        "risk_level": str(row["risk_level"]),
        "actual_fraud": None if row.get("actual_fraud") != row.get("actual_fraud") else int(row["actual_fraud"]),
    }
    return result


@router.get("/metrics")
def metrics() -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    return {
        "is_demo": state.is_demo,
        "best_model": state.best_model_name,
        "kpis": state.snapshot()["kpis"],
        "test": state._test_metrics(),
        "split": state.split_counts,
    }


@router.get("/model-performance")
def model_performance() -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    return state.performance_payload()


@router.get("/risk-distribution")
def distribution() -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    from services.monitoring import risk_distribution

    payload = risk_distribution(state.scored)
    payload["is_demo"] = state.is_demo
    return payload


@router.get("/alerts")
def alerts() -> dict:
    return {
        "is_demo": state.is_demo,
        "spike": state.spike,
        "items": state.alerts,
    }


@router.get("/trends")
def trends() -> dict:
    if not state.model_online:
        raise HTTPException(503, "Model is not online.")
    return {"is_demo": state.is_demo, **state.trends}


@router.get("/cost-analysis")
def cost_analysis(
    cost_false_positive: float = Query(25.0, ge=0),
    cost_false_negative: float = Query(250.0, ge=0),
    average_transaction_value: float = Query(120.0, ge=0),
    threshold: float | None = Query(None, ge=0.05, le=0.95),
) -> dict:
    try:
        return state.cost_payload(
            cost_false_positive, cost_false_negative, average_transaction_value, threshold
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/cost-analysis")
def cost_analysis_post(body: CostConfig) -> dict:
    try:
        return state.cost_payload(
            body.cost_false_positive,
            body.cost_false_negative,
            body.average_transaction_value,
            body.threshold,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/train")
def train(body: TrainRequest | None = None) -> dict:
    try:
        if body and body.use_demo:
            df = __import__("services.synthetic_data", fromlist=["generate_synthetic_transactions"]).generate_synthetic_transactions()
            return state.fit_dataframe(df, is_demo=True, dataset_name="DEMO / SYNTHETIC DATASET")
        if not len(state.dataset):
            state.bootstrap_demo()
            return state.snapshot()
        return state.fit_dataframe(state.dataset, is_demo=state.is_demo, dataset_name=state.dataset_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Training failed: {exc}") from exc


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    try:
        validate_upload_filename(file.filename or "")
        validate_content_type(file.content_type)
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("File exceeds the 10 MB upload limit.")
        return state.load_upload(file.filename or "upload.csv", raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"Upload failed: {exc}") from exc


@router.get("/options")
def options() -> dict:
    from utils.security import (
        ALLOWED_DEVICE_TYPES,
        ALLOWED_LOCATIONS,
        ALLOWED_MERCHANT_CATEGORIES,
        ALLOWED_PAYMENT_METHODS,
    )

    return {
        "device_types": sorted(ALLOWED_DEVICE_TYPES),
        "payment_methods": sorted(ALLOWED_PAYMENT_METHODS),
        "locations": sorted(ALLOWED_LOCATIONS),
        "merchant_categories": sorted(ALLOWED_MERCHANT_CATEGORIES),
    }
