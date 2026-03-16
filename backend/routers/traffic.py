"""Traffic API router exposing live and historical endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Query

from database import SessionLocal, RawTraffic, ProcessedTraffic
from schemas import LiveTrafficItem, LiveTrafficResponse, ProcessedHistoryResponse, ProcessedTrafficItem

router = APIRouter(prefix="/traffic", tags=["traffic"])


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
    """Return processed history for one location for the requested lookback window."""
    session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = (
            session.query(ProcessedTraffic)
            .filter(
                ProcessedTraffic.location_name == location,
                ProcessedTraffic.window_end >= cutoff,
            )
            .order_by(ProcessedTraffic.window_start.asc())
            .all()
        )

        records = [
            ProcessedTrafficItem(
                location_name=r.location_name,
                window_start=r.window_start,
                window_end=r.window_end,
                avg_speed=r.avg_speed,
                min_speed=r.min_speed,
                max_speed=r.max_speed,
                avg_congestion_index=r.avg_congestion_index,
                avg_confidence=r.avg_confidence,
                sample_count=r.sample_count,
                norm_speed=r.norm_speed,
                norm_congestion=r.norm_congestion,
                hour_sin=r.hour_sin,
                hour_cos=r.hour_cos,
                congestion_label=r.congestion_label,
            )
            for r in rows
        ]
        return ProcessedHistoryResponse(location=location, hours=hours, records=records)
    finally:
        session.close()
