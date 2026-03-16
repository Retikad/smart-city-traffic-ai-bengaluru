"""Keras LSTM model definition for short-term congestion forecasting."""

from __future__ import annotations

from tensorflow import keras


def build_model(input_shape: tuple[int, int] = (3, 4)) -> keras.Model:
    """Create and compile the required LSTM architecture."""
    model = keras.Sequential(
        [
            keras.layers.Input(shape=input_shape),
            keras.layers.LSTM(64, return_sequences=True),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(32),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model
