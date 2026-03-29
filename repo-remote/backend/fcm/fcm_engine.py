"""Fuzzy Cognitive Map inference engine for traffic explanation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from .fcm_config import CONCEPTS, WEIGHT_MATRIX


@dataclass
class FCMResult:
    """FCM result container for final activation vector and explanation metadata."""

    vector: Dict[str, float]
    dominant_cause: str
    explanation: str


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Stable sigmoid used for bounded concept activations."""
    return 1.0 / (1.0 + np.exp(-x))


def _build_initial_vector(congestion_index: float, speed: float, hour: int) -> np.ndarray:
    """Map external inputs to the six FCM concept activations."""
    speed_norm = float(np.clip(speed / 80.0, 0.0, 1.0))
    density = float(np.clip(congestion_index, 0.0, 1.0))
    capacity_util = float(np.clip(0.5 * density + 0.5 * (1.0 - speed_norm), 0.0, 1.0))
    time_peak = float(0.5 * (np.sin(2 * np.pi * hour / 24.0 - np.pi / 2) + 1.0))
    travel_delay = float(np.clip(0.6 * congestion_index + 0.4 * (1.0 - speed_norm), 0.0, 1.0))

    return np.array(
        [density, speed_norm, time_peak, capacity_util, congestion_index, travel_delay],
        dtype=float,
    )


def _dominant_driver(final_vec: np.ndarray) -> Tuple[str, int, float]:
    """Select dominant driver by signed contribution into congestion_level node."""
    candidate_indices = [0, 1, 2, 3, 5]
    # Contribution to congestion node is concept activation times its causal weight.
    contributions = {i: float(final_vec[i] * WEIGHT_MATRIX[i, 4]) for i in candidate_indices}
    idx = max(candidate_indices, key=lambda i: contributions[i])
    return CONCEPTS[idx], idx, contributions[idx]


def explain(location: str, congestion_index: float, speed: float, hour: int) -> FCMResult:
    """Run FCM inference and generate plain-English explanation."""
    state = _build_initial_vector(congestion_index, speed, hour)

    for _ in range(20):
        updated = _sigmoid(state @ WEIGHT_MATRIX)
        if np.max(np.abs(updated - state)) < 1e-4:
            state = updated
            break
        state = updated

    dominant_name, dominant_idx, dominant_contribution = _dominant_driver(state)
    vector = {name: round(float(val), 4) for name, val in zip(CONCEPTS, state)}

    speed_contribution = float(state[1] * WEIGHT_MATRIX[1, 4])
    delay_contribution = float(state[5] * WEIGHT_MATRIX[5, 4])
    dominant_effect = "increases" if dominant_contribution >= 0 else "reduces"

    explanation = (
        f"{location} shows predicted congestion index {congestion_index:.2f}. "
        f"The FCM indicates {dominant_name.replace('_', ' ')} as the strongest factor and it {dominant_effect} congestion, "
        f"with congestion level activation {state[4]:.2f}. "
        f"Vehicle speed contribution is {speed_contribution:+.2f} and travel-time delay contribution is {delay_contribution:+.2f}."
    )

    if dominant_idx == 0 and (hour in range(7, 11) or hour in range(16, 21)):
        explanation += " This pattern is consistent with Bengaluru peak-hour density pressure."

    return FCMResult(vector=vector, dominant_cause=dominant_name, explanation=explanation)
