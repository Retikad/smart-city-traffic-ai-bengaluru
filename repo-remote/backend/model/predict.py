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


def _get_model_cached(model_path: Path) -> keras.Model | None:
    """Load model from disk once and reuse until file changes on disk."""
    key = str(model_path)
    mtime = model_path.stat().st_mtime
    cached = _MODEL_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        model = keras.models.load_model(model_path, compile=False)
    except Exception as primary_exc:
        print(f"[MODEL][WARN] Primary load failed for {model_path}: {primary_exc}")
        try:
            model = keras.models.load_model(
                model_path,
                compile=False,
                custom_objects={
                    "InputLayer": keras.layers.InputLayer,
                    "GRU": keras.layers.GRU,
                    "LSTM": keras.layers.LSTM,
                    "Dense": keras.layers.Dense,
                },
            )
        except Exception as fallback_exc:
            print(f"[MODEL][ERROR] Fallback load failed for {model_path}: {fallback_exc}")
            _MODEL_CACHE[key] = (mtime, None)
            return None

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


def _normalize_sequence(sequence: list[list[float | None]]) -> np.ndarray:
    """Coerce incoming sequence into a safe numeric (3, 4) array.

    This keeps inference resilient even when clients send nulls, shorter rows,
    or longer history windows.
    """
    if not sequence:
        return np.zeros((3, 4), dtype=np.float32)

    normalized_rows: list[list[float]] = []
    for row in sequence:
        cleaned: list[float] = []
        for value in row[:4]:
            if value is None:
                cleaned.append(0.0)
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                num = 0.0
            if not np.isfinite(num):
                num = 0.0
            cleaned.append(num)

        if len(cleaned) < 4:
            cleaned.extend([0.0] * (4 - len(cleaned)))
        normalized_rows.append(cleaned)

    # Use the most recent 3 timesteps; pad with earliest known row if needed.
    rows = normalized_rows[-3:]
    while len(rows) < 3:
        rows.insert(0, rows[0] if rows else [0.0, 0.0, 0.0, 0.0])

    return np.asarray(rows, dtype=np.float32)


def predict_next(location: str, sequence: list[list[float | None]]) -> Tuple[float, float]:
    """Run model inference and return (congestion_index, confidence)."""
    model_path = model_path_for_location(location)
    arr = _normalize_sequence(sequence)

    # For newly added corridors without a trained model yet, fall back to a
    # stable baseline using the most recent congestion signal.
    if not model_path.exists():
        pred = float(np.clip(arr[-1, 1], 0.0, 1.0))
        confidence = 0.58
        return pred, confidence

    model = _get_model_cached(model_path)
    if model is None:
        # unable to load model; fall back to no-model baseline
        pred = float(np.clip(arr[-1, 1], 0.0, 1.0))
        confidence = 0.58
        return pred, confidence

    try:
        pred = float(model.predict(arr[None, :, :], verbose=0)[0][0])
    except Exception as exc:
        print(f"[MODEL][ERROR] Inference failed for {model_path}: {exc}")
        pred = float(np.clip(arr[-1, 1], 0.0, 1.0))
        confidence = 0.58
        return pred, confidence

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
