"""FastAPI application entry point for Bengaluru Smart Traffic AI backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers.explanation import router as explanation_router
from routers.prediction import router as prediction_router
from routers.traffic import router as traffic_router
from schemas import HealthResponse

app = FastAPI(title="Smart-City Traffic Prediction and Explainable Decision Support System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database tables at startup."""
    init_db()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return backend service health status."""
    return HealthResponse(status="ok")


app.include_router(traffic_router)
app.include_router(prediction_router)
app.include_router(explanation_router)
