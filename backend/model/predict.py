"""Model loading and inference utilities for location-specific LSTM models."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple
import os

import numpy as np
from dotenv import load_dotenv
from tensorflow import keras

load_dotenv()

MODEL_DIR = Path(os.getenv("MODEL_DIR", "model/saved_model"))


def _safe_name(location: str) -> str:
    """Convert location names to filesystem-safe model identifiers."""
    return location.lower().replace(" ", "_")


def model_path_for_location(location: str) -> Path:
    """Return model path for a given corridor."""
    return MODEL_DIR / f"lstm_{_safe_name(location)}.keras"


def predict_next(location: str, sequence: list[list[float]]) -> Tuple[float, float]:
    """Run model inference and return (congestion_index, confidence)."""
    model_path = model_path_for_location(location)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found for {location}: {model_path}")

    arr = np.asarray(sequence, dtype=np.float32)
    if arr.shape != (12, 4):
        raise ValueError("Expected sequence shape (12, 4)")

    model = keras.models.load_model(model_path)
    pred = float(model.predict(arr[None, :, :], verbose=0)[0][0])
    pred = float(np.clip(pred, 0.0, 1.0))
    confidence = float(np.clip(1.0 - abs(pred - 0.5), 0.5, 0.99))
    return pred, confidence


def congestion_label(ci: float) -> str:
    """Map numeric congestion index to severity label."""
    if ci < 0.25:
        return "low"
    if ci < 0.5:
        return "medium"
    if ci < 0.75:
        return "high"
    return "severe"
