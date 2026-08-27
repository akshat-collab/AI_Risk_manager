"""AI Risk Manager — defensive fraud-risk API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.api import router
from services.state import state


@asynccontextmanager
async def lifespan(_: FastAPI):
    state.bootstrap_demo()
    yield


app = FastAPI(
    title="AI Risk Manager",
    description="Defense-only AI/ML risk detection for fraud, returns, and chargebacks.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "name": "AI Risk Manager",
        "tagline": "Stop revenue leakage before it happens.",
        "mode": "DEFENSE-FIRST • AI RISK INTELLIGENCE",
        "docs": "/docs",
    }
