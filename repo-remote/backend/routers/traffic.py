
"""Traffic API router exposing live and historical endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import List

from fastapi import APIRouter, Query

from backend.database import SessionLocal, RawTraffic
from backend.schemas import LiveTrafficItem, LiveTrafficResponse, ProcessedHistoryResponse, ProcessedTrafficItem
from fastapi import Response

from backend.database import CORRIDORS
from backend.ingest import _pull_probe, CORRIDOR_PROBES
router = APIRouter(prefix="/traffic", tags=["traffic"])


def _safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def _safe_bool(v, default=False):
    try:
        return bool(v)
    except Exception:
        return default

# Endpoint: Get all probe points for a corridor (for heatmap)
@router.get("/probes")
async def get_corridor_probes(location: str):
    """Return all probe points (lat, lng, congestion_index) for a corridor."""
    if location not in CORRIDOR_PROBES:
        return {"error": f"Unknown corridor: {location}"}
    probe_coords = CORRIDOR_PROBES[location]
    points = []
    for lat, lng in probe_coords:
        try:
            probe = _pull_probe(lat, lng)
            points.append({
                "lat": lat,
                "lng": lng,
                "congestion_index": probe["congestion_index"]
            })
        except Exception as exc:
            points.append({
                "lat": lat,
                "lng": lng,
                "congestion_index": None,
                "error": str(exc)
            })
    return {"location": location, "probes": points}


def _round_down_5min(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


def _label(ci: float) -> str:
    if ci < 0.25:
        return "low"
    if ci < 0.5:
        return "medium"
    if ci < 0.75:
        return "high"
    return "severe"



@router.get("/live", response_model=LiveTrafficResponse)
async def get_live_traffic() -> LiveTrafficResponse:
    """Return latest raw traffic record for each monitored Bengaluru corridor, including ETA and weather."""
    session = SessionLocal()
    try:
        rows = (
            session.query(RawTraffic)
            .order_by(RawTraffic.location_name.asc(), RawTraffic.timestamp.desc())
            .all()
        )

        latest_by_location: dict[str, RawTraffic] = {}
        for row in rows:
            if row.location_name not in latest_by_location:
                latest_by_location[row.location_name] = row

        items: List[dict] = []
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


# Heat map endpoint: returns congestion and density for all corridors
@router.get("/heatmap")
async def get_heatmap() -> list:
    print("HEATMAP ENDPOINT CALLED")
    session = SessionLocal()
    try:
        rows = (
            session.query(RawTraffic)
            .order_by(RawTraffic.location_name.asc(), RawTraffic.timestamp.desc())
            .all()
        )
        latest_by_location: dict[str, RawTraffic] = {}
        for row in rows:
            if row.location_name not in latest_by_location:
                latest_by_location[row.location_name] = row
        heatmap = []
        for r in latest_by_location.values():
            heatmap.append({
                "location_name": r.location_name,
                "lat": r.latitude,
                "lng": r.longitude,
                "congestion_index": r.congestion_index,
                "density": getattr(r, "confidence", None),
                "crowd_density": getattr(r, "crowd_density", None),
                "eta_seconds": getattr(r, "eta_seconds", None),
            })
        return heatmap
    except Exception as e:
        print("HEATMAP ERROR:", e)
        raise
    finally:
        session.close()

@router.get("/history", response_model=ProcessedHistoryResponse)
async def get_history(
    location: str = Query(..., description="Corridor name"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
) -> ProcessedHistoryResponse:
    """Return rolling 5-min history for one location with real-time gap filling."""
    session = SessionLocal()
    try:
        now = _round_down_5min(datetime.utcnow())
        cutoff = now - timedelta(hours=hours)
        rows = (
            session.query(RawTraffic)
            .filter(
                RawTraffic.location_name == location,
                RawTraffic.timestamp >= cutoff,
            )
            .order_by(RawTraffic.timestamp.asc())
            .all()
        )

        # Aggregate raw rows into 5-minute bins.
        bins: dict[datetime, dict[str, float]] = {}
        for r in rows:
            start = _round_down_5min(r.timestamp)
            b = bins.get(start)
            eta_val = float(r.eta_seconds) if getattr(r, "eta_seconds", None) is not None else 0.0
            weather_temp = float(r.weather_temp) if getattr(r, "weather_temp", None) is not None else 0.0
            weather_humidity = float(r.weather_humidity) if getattr(r, "weather_humidity", None) is not None else 0.0
            weather_rain = float(r.weather_rain) if getattr(r, "weather_rain", None) is not None else 0.0
            crowd_val = float(r.crowd_density) if getattr(r, "crowd_density", None) is not None else 0.0
            if b is None:
                bins[start] = {
                    "sum_speed": r.current_speed,
                    "min_speed": r.current_speed,
                    "max_speed": r.current_speed,
                    "sum_ci": r.congestion_index,
                    "sum_conf": r.confidence,
                    "sum_crowd": crowd_val,
                    "count": 1.0,
                    "sum_eta": eta_val,
                    "sum_weather_temp": weather_temp,
                    "sum_weather_humidity": weather_humidity,
                    "sum_weather_rain": weather_rain,
                }
            else:
                b["sum_speed"] += r.current_speed
                b["min_speed"] = min(b["min_speed"], r.current_speed)
                b["max_speed"] = max(b["max_speed"], r.current_speed)
                b["sum_ci"] += r.congestion_index
                b["sum_conf"] += r.confidence
                b["sum_crowd"] += crowd_val
                b["count"] += 1.0
                b["sum_eta"] += eta_val
                b["sum_weather_temp"] += weather_temp
                b["sum_weather_humidity"] += weather_humidity
                b["sum_weather_rain"] += weather_rain

        timeline: list[dict[str, float | datetime]] = []
        cursor = _round_down_5min(cutoff)
        last_known: dict[str, float] | None = None

        while cursor <= now:
            b = bins.get(cursor)
            if b is not None:
                count = int(b["count"])
                avg_speed = b["sum_speed"] / b["count"]
                avg_ci = b["sum_ci"] / b["count"]
                avg_conf = b["sum_conf"] / b["count"]
                avg_crowd = b.get("sum_crowd", 0.0) / b["count"]
                last_known = {
                    "avg_speed": float(avg_speed),
                    "min_speed": float(b["min_speed"]),
                    "max_speed": float(b["max_speed"]),
                    "avg_ci": float(avg_ci),
                    "avg_conf": float(avg_conf),
                    "avg_crowd": float(avg_crowd),
                }
            elif last_known is not None:
                count = 0
                avg_speed = last_known["avg_speed"]
                avg_ci = last_known["avg_ci"]
                avg_conf = last_known["avg_conf"]
            else:
                count = 0
                avg_speed = 0.0
                avg_ci = 0.0
                avg_conf = 0.0

            timeline.append(
                {
                    "window_start": cursor,
                    "window_end": cursor + timedelta(minutes=5),
                    "avg_speed": float(avg_speed),
                    "min_speed": float(last_known["min_speed"] if last_known else avg_speed),
                    "max_speed": float(last_known["max_speed"] if last_known else avg_speed),
                    "avg_congestion_index": float(avg_ci),
                    "avg_confidence": float(avg_conf),
                    "avg_crowd": float(last_known["avg_crowd"] if last_known else 0.0),
                    "sample_count": count,
                    "eta_seconds": float(b["sum_eta"] / b["count"]) if b is not None else 0.0,
                    "weather_temp": float(b["sum_weather_temp"] / b["count"]) if b is not None else 0.0,
                    "weather_humidity": float(b["sum_weather_humidity"] / b["count"]) if b is not None else 0.0,
                    "weather_rain": float(b["sum_weather_rain"] / b["count"]) if b is not None else 0.0,
                }
            )
            cursor += timedelta(minutes=5)

        speeds = [x["avg_speed"] for x in timeline]
        cis = [x["avg_congestion_index"] for x in timeline]
        speed_min = min(speeds) if speeds else 0.0
        speed_max = max(speeds) if speeds else 1.0
        ci_min = min(cis) if cis else 0.0
        ci_max = max(cis) if cis else 1.0
        speed_den = (speed_max - speed_min) if speed_max != speed_min else 1.0
        ci_den = (ci_max - ci_min) if ci_max != ci_min else 1.0

        records = []
        for t in timeline:
            ws = t["window_start"]
            we = t["window_end"]
            avg_ci = float(t["avg_congestion_index"])
            hours_of_day = ws.hour + (ws.minute / 60.0)
            # Try to get eta_seconds from t, else default to 0.0
            eta_seconds = float(t.get("eta_seconds", 0.0))
            records.append(
                ProcessedTrafficItem(
                    location_name=location,
                    window_start=ws,
                    window_end=we,
                    avg_speed=float(t["avg_speed"]),
                    min_speed=float(t["min_speed"]),
                    max_speed=float(t["max_speed"]),
                    avg_congestion_index=avg_ci,
                    avg_confidence=float(t["avg_confidence"]),
                    sample_count=int(t["sample_count"]),
                    norm_speed=float((t["avg_speed"] - speed_min) / speed_den),
                    norm_congestion=float((avg_ci - ci_min) / ci_den),
                    hour_sin=float(math.sin(2 * math.pi * hours_of_day / 24.0)),
                    hour_cos=float(math.cos(2 * math.pi * hours_of_day / 24.0)),
                    congestion_label=_label(avg_ci),
                    crowd_density=float(t.get("avg_crowd", 0.0)),
                    eta_seconds=eta_seconds,
                    weather_main=t.get("weather_main", "unknown"),
                    weather_description=t.get("weather_description", "unknown"),
                    weather_temp=float(t.get("weather_temp", 0.0)),
                    weather_humidity=float(t.get("weather_humidity", 0.0)),
                    weather_rain=float(t.get("weather_rain", 0.0)),
                )
            )

        return ProcessedHistoryResponse(location=location, hours=hours, records=records)
    finally:
        session.close()
