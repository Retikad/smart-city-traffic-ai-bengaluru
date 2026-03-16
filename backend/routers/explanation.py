"""Explanation API router using FCM reasoning."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fcm.fcm_engine import explain
from schemas import ExplainRequest, ExplainResponse

router = APIRouter(tags=["explanation"])


@router.post("/explain", response_model=ExplainResponse)
async def explain_prediction(payload: ExplainRequest) -> ExplainResponse:
    """Explain predicted congestion using the Fuzzy Cognitive Map engine."""
    try:
        result = explain(
            location=payload.location,
            congestion_index=payload.congestion_index,
            speed=payload.speed,
            hour=payload.hour,
        )
        return ExplainResponse(
            fcm_vector=result.vector,
            dominant_cause=result.dominant_cause,
            explanation=result.explanation,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Explanation failed: {exc}") from exc
