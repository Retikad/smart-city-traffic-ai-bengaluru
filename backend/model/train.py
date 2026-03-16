"""Training pipeline for per-corridor LSTM congestion forecasting models."""

from __future__ import annotations

from pathlib import Path
import os
import sys

import numpy as np
from dotenv import load_dotenv
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

# Allow running as `python model/train.py` from backend folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from model.lstm_model import build_model  # noqa: E402

load_dotenv()

MODEL_DIR = Path(os.getenv("MODEL_DIR", "model/saved_model"))
DATA_DIR = Path(__file__).resolve().parents[1] / "model" / "training_data"


def _safe_name(location: str) -> str:
    """Convert corridor name into file-safe model suffix."""
    return location.lower().replace(" ", "_")


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute root mean squared error."""
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def train_for_location(location: str) -> dict:
    """Train and evaluate LSTM model for one location's preprocessed arrays."""
    x_path = DATA_DIR / f"X_{_safe_name(location)}.npy"
    y_path = DATA_DIR / f"y_{_safe_name(location)}.npy"

    if not x_path.exists() or not y_path.exists():
        raise FileNotFoundError(f"Missing training arrays for {location}")

    x = np.load(x_path)
    y = np.load(y_path)
    if len(x) < 5:
        raise ValueError(f"Not enough samples for {location}; need >= 5, got {len(x)}")

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, shuffle=True
    )

    model = build_model(input_shape=(3, 4))
    model.fit(x_train, y_train, epochs=50, batch_size=32, verbose=0, validation_split=0.1)

    preds = model.predict(x_test, verbose=0).reshape(-1)
    preds = np.clip(preds, 0.0, 1.0)

    # Naive baseline: predict next value as previous timestep's norm_congestion in the sequence.
    baseline = x_test[:, -1, 1]

    metrics = {
        "location": location,
        "lstm_mae": float(mean_absolute_error(y_test, preds)),
        "lstm_rmse": _rmse(y_test, preds),
        "naive_mae": float(mean_absolute_error(y_test, baseline)),
        "naive_rmse": _rmse(y_test, baseline),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_DIR / f"lstm_{_safe_name(location)}.keras")
    return metrics


def _discover_locations() -> list[str]:
    """Find locations based on exported X files in training_data directory."""
    locations: list[str] = []
    for x_file in sorted(DATA_DIR.glob("X_*.npy")):
        stem = x_file.stem.replace("X_", "")
        locations.append(stem.replace("_", " ").title())
    return locations


def main() -> None:
    """Train all available location models and print evaluation table."""
    if not DATA_DIR.exists():
        raise FileNotFoundError("training_data directory not found. Run preprocess.py first.")

    locations = _discover_locations()
    if not locations:
        raise ValueError("No location arrays found. Run preprocess.py first.")

    print("\n=== LSTM Training Results (LSTM vs Naive Baseline) ===")
    print(
        f"{'Location':<24} {'LSTM_MAE':>10} {'LSTM_RMSE':>10} "
        f"{'NAIVE_MAE':>10} {'NAIVE_RMSE':>12}"
    )

    for location in locations:
        try:
            m = train_for_location(location)
            print(
                f"{m['location']:<24} {m['lstm_mae']:>10.4f} {m['lstm_rmse']:>10.4f} "
                f"{m['naive_mae']:>10.4f} {m['naive_rmse']:>12.4f}"
            )
        except Exception as exc:
            print(f"{location:<24} ERROR: {exc}")


if __name__ == "__main__":
    main()
