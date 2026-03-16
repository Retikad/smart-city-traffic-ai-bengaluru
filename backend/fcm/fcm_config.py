"""Static FCM concepts and causal weight matrix configuration."""

from __future__ import annotations

import numpy as np

CONCEPTS = [
    "traffic_density",
    "vehicle_speed",
    "time_of_day",
    "road_capacity_utilisation",
    "congestion_level",
    "travel_time_delay",
]

WEIGHT_MATRIX = np.array(
    [
        [0.0, -0.7, 0.0, 0.8, 0.9, 0.6],
        [-0.6, 0.0, 0.0, -0.5, -0.8, -0.7],
        [0.4, 0.0, 0.0, 0.3, 0.5, 0.2],
        [0.5, -0.4, 0.0, 0.0, 0.7, 0.5],
        [0.3, -0.6, 0.0, 0.4, 0.0, 0.8],
        [0.2, 0.0, 0.0, 0.3, 0.4, 0.0],
    ],
    dtype=float,
)
