"""FastAPI application entry point for Bengaluru Smart Traffic AI backend."""
from __future__ import annotations

# Ensure .env is loaded for FastAPI
from dotenv import load_dotenv
import os
# Explicitly load the .env file from the backend directory
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers.explanation import router as explanation_router
from backend.routers.prediction import router as prediction_router
from backend.routers.traffic import router as traffic_router
from backend.schemas import HealthResponse
from backend.database import SessionLocal, RawTraffic
from backend.routers.traffic import _safe_float, _safe_bool

app = FastAPI(title="Smart-City Traffic Prediction and Explainable Decision Support System", debug=True)


@app.get("/traffic/live")
async def live_override():
    """Temporary override route to serve live traffic safely while debugging route issues."""
    session = SessionLocal()
    try:
        rows = (
            session.query(RawTraffic)
            .order_by(RawTraffic.location_name.asc(), RawTraffic.timestamp.desc())
            .all()
        )
        latest_by_location = {}
        for row in rows:
            if row.location_name not in latest_by_location:
                latest_by_location[row.location_name] = row

        items = []
        for r in latest_by_location.values():
            items.append({
                "location_name": r.location_name,
                "latitude": _safe_float(getattr(r, "latitude", None)),
                "longitude": _safe_float(getattr(r, "longitude", None)),
                "timestamp": r.timestamp,
                "current_speed": _safe_float(getattr(r, "current_speed", None)),
                "free_flow_speed": _safe_float(getattr(r, "free_flow_speed", None)),
                "current_travel_time": _safe_float(getattr(r, "current_travel_time", None)),
                "free_flow_travel_time": _safe_float(getattr(r, "free_flow_travel_time", None)),
                "confidence": _safe_float(getattr(r, "confidence", None)),
                "road_closure": _safe_bool(getattr(r, "road_closure", False)),
                "congestion_index": _safe_float(getattr(r, "congestion_index", None)),
                "crowd_density": (None if getattr(r, "crowd_density", None) is None else _safe_float(r.crowd_density)),
                "eta_seconds": (None if getattr(r, "eta_seconds", None) is None else _safe_float(r.eta_seconds)),
                "weather_main": getattr(r, "weather_main", None),
                "weather_description": getattr(r, "weather_description", None),
                "weather_temp": (None if getattr(r, "weather_temp", None) is None else _safe_float(r.weather_temp)),
                "weather_humidity": (None if getattr(r, "weather_humidity", None) is None else _safe_float(r.weather_humidity)),
                "weather_rain": (None if getattr(r, "weather_rain", None) is None else _safe_float(r.weather_rain)),
            })
        items.sort(key=lambda x: x["location_name"])
        return {"items": items}
    finally:
        session.close()
 
cors_allow_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://your-frontend-domain",
    ).split(",")
    if origin.strip()
]

cors_allow_origin_regex = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
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
