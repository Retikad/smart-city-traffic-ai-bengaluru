"""Pydantic schemas for API input and output payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class LiveTrafficItem(BaseModel):
    """Latest traffic reading for one monitored corridor."""

    location_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    current_speed: float
    free_flow_speed: float
    current_travel_time: float
    free_flow_travel_time: float
    confidence: float
    road_closure: bool
    congestion_index: float


class LiveTrafficResponse(BaseModel):
    """Response schema for latest readings across all corridors."""

    items: List[LiveTrafficItem]


class ProcessedTrafficItem(BaseModel):
    """History record schema from processed traffic table."""

    location_name: str
    window_start: datetime
    window_end: datetime
    avg_speed: float
    min_speed: float
    max_speed: float
    avg_congestion_index: float
    avg_confidence: float
    sample_count: int
    norm_speed: float
    norm_congestion: float
    hour_sin: float
    hour_cos: float
    congestion_label: str


class ProcessedHistoryResponse(BaseModel):
    """Response schema for processed history endpoint."""

    location: str
    hours: int
    records: List[ProcessedTrafficItem]


class PredictRequest(BaseModel):
    """Prediction request with a fixed 12-step sequence of 4 features."""

    location: str
    sequence: List[List[float]] = Field(min_length=12, max_length=12)


class PredictResponse(BaseModel):
    """Prediction response with congestion score, severity label, and confidence."""

    congestion_index: float
    label: str
    confidence: float


class ExplainRequest(BaseModel):
    """FCM explanation request payload."""

    location: str
    congestion_index: float = Field(ge=0, le=1)
    speed: float = Field(ge=0)
    hour: int = Field(ge=0, le=23)


class ExplainResponse(BaseModel):
    """FCM explanation response payload."""

    fcm_vector: Dict[str, float]
    dominant_cause: str
    explanation: str


class HealthResponse(BaseModel):
    """Service health response."""

    status: str
