"""Prediction API router powered by location-specific LSTM models."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.model.predict import congestion_label, predict_next
from backend.schemas import PredictRequest, PredictResponse

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    """Predict next congestion index for the selected location and input sequence."""
    try:
        pred, confidence = predict_next(payload.location, payload.sequence)
        return PredictResponse(
            congestion_index=round(pred, 4),
            label=congestion_label(pred),
            confidence=round(confidence, 4),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc
