"""Traffic API router exposing live and historical endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import List

from fastapi import APIRouter, Query

from database import SessionLocal, RawTraffic
from schemas import LiveTrafficItem, LiveTrafficResponse, ProcessedHistoryResponse, ProcessedTrafficItem

router = APIRouter(prefix="/traffic", tags=["traffic"])


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
    """Return latest raw traffic record for each monitored Bengaluru corridor."""
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

        items: List[LiveTrafficItem] = [
            LiveTrafficItem(
                location_name=r.location_name,
                latitude=r.latitude,
                longitude=r.longitude,
                timestamp=r.timestamp,
                current_speed=r.current_speed,
                free_flow_speed=r.free_flow_speed,
                current_travel_time=r.current_travel_time,
                free_flow_travel_time=r.free_flow_travel_time,
                confidence=r.confidence,
                road_closure=r.road_closure,
                congestion_index=r.congestion_index,
            )
            for r in latest_by_location.values()
        ]
        items.sort(key=lambda x: x.location_name)
        return LiveTrafficResponse(items=items)
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
            if b is None:
                bins[start] = {
                    "sum_speed": r.current_speed,
                    "min_speed": r.current_speed,
                    "max_speed": r.current_speed,
                    "sum_ci": r.congestion_index,
                    "sum_conf": r.confidence,
                    "count": 1.0,
                }
            else:
                b["sum_speed"] += r.current_speed
                b["min_speed"] = min(b["min_speed"], r.current_speed)
                b["max_speed"] = max(b["max_speed"], r.current_speed)
                b["sum_ci"] += r.congestion_index
                b["sum_conf"] += r.confidence
                b["count"] += 1.0

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
                last_known = {
                    "avg_speed": float(avg_speed),
                    "min_speed": float(b["min_speed"]),
                    "max_speed": float(b["max_speed"]),
                    "avg_ci": float(avg_ci),
                    "avg_conf": float(avg_conf),
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
                    "sample_count": count,
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
                )
            )

        return ProcessedHistoryResponse(location=location, hours=hours, records=records)
    finally:
        session.close()
