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
_MODEL_CACHE: dict[str, tuple[float, keras.Model]] = {}


def _safe_name(location: str) -> str:
    """Convert location names to filesystem-safe model identifiers."""
    return location.lower().replace(" ", "_")


def model_path_for_location(location: str) -> Path:
    """Return model path for a given corridor."""
    return MODEL_DIR / f"lstm_{_safe_name(location)}.keras"


def _get_model_cached(model_path: Path) -> keras.Model:
    """Load model from disk once and reuse until file changes on disk."""
    key = str(model_path)
    mtime = model_path.stat().st_mtime
    cached = _MODEL_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    model = keras.models.load_model(model_path)
    _MODEL_CACHE[key] = (mtime, model)
    return model


def _prediction_confidence(pred: float, sequence: np.ndarray) -> float:
    """Estimate confidence from decision-margin and short-term stability."""
    thresholds = np.array([0.25, 0.5, 0.75], dtype=np.float32)
    nearest_boundary = float(np.min(np.abs(thresholds - pred)))
    boundary_score = float(np.clip(nearest_boundary / 0.25, 0.0, 1.0))

    # Sequence column 1 is absolute congestion index in this project.
    volatility = float(np.std(sequence[:, 1]))
    stability_score = float(1.0 - np.clip(volatility / 0.25, 0.0, 1.0))

    confidence = 0.6 + (0.25 * boundary_score) + (0.14 * stability_score)
    return float(np.clip(confidence, 0.55, 0.99))


def predict_next(location: str, sequence: list[list[float]]) -> Tuple[float, float]:
    """Run model inference and return (congestion_index, confidence)."""
    model_path = model_path_for_location(location)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found for {location}: {model_path}")

    arr = np.asarray(sequence, dtype=np.float32)
    if arr.shape != (3, 4):
        raise ValueError("Expected sequence shape (3, 4)")

    model = _get_model_cached(model_path)
    pred = float(model.predict(arr[None, :, :], verbose=0)[0][0])
    pred = float(np.clip(pred, 0.0, 1.0))
    confidence = _prediction_confidence(pred, arr)
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
