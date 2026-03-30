"""Preprocessing pipeline for feature engineering and sequence export."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backend.database import ProcessedTraffic, RawTraffic, SessionLocal, init_db

SEQUENCE_LEN = 3
# Exported feature columns (must match `backend/model/train.py` FEATURE_COLUMNS)
FEATURE_COLUMNS = [
    "norm_speed",
    "avg_congestion_index",
    "hour_sin",
    "hour_cos",
    "eta_seconds",
    "weather_temp",
    "weather_humidity",
    "weather_rain",
]
MIN_TRAINING_WINDOWS = 8


def _label(ci: float) -> str:
    """Map congestion index to categorical class label."""
    if ci < 0.25:
        return "low"
    if ci < 0.5:
        return "medium"
    if ci < 0.75:
        return "high"
    return "severe"


def _to_sequences(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Convert processed feature rows into model-ready sliding windows."""
    x_rows: list[np.ndarray] = []
    y_rows: list[float] = []

    feats = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    target = df["avg_congestion_index"].to_numpy(dtype=np.float32)

    for idx in range(SEQUENCE_LEN, len(df)):
        x_rows.append(feats[idx - SEQUENCE_LEN : idx])
        y_rows.append(target[idx])

    if not x_rows:
        return np.empty((0, SEQUENCE_LEN, 4), dtype=np.float32), np.empty((0,), dtype=np.float32)

    return np.stack(x_rows).astype(np.float32), np.array(y_rows, dtype=np.float32)


def _bootstrap_windows(agg: pd.DataFrame, min_windows: int = MIN_TRAINING_WINDOWS) -> pd.DataFrame:
    """Expand sparse corridor history into minimally trainable 5-minute windows.

    This is only used when a corridor has very few real windows (for newly added
    corridors) so initial models can be trained before enough live data accumulates.
    """
    if len(agg) >= min_windows or agg.empty:
        return agg

    base = agg.iloc[-1].copy()
    extra_rows = []
    needed = min_windows - len(agg)

    for idx in range(needed, 0, -1):
        ws = base["window_start"] - pd.Timedelta(minutes=5 * idx)
        we = ws + pd.Timedelta(minutes=5)
        # Small deterministic jitter keeps synthetic windows non-identical.
        jitter = (idx % 5) * 0.3
        speed = max(2.0, float(base["avg_speed"]) - jitter)
        ci = min(1.0, max(0.0, float(base["avg_congestion_index"]) + (0.005 * (idx % 3))))
        extra_rows.append(
            {
                "window_start": ws,
                "avg_speed": speed,
                "min_speed": max(0.0, speed - 1.0),
                "max_speed": speed + 1.0,
                "avg_congestion_index": ci,
                "avg_confidence": float(base["avg_confidence"]),
                "sample_count": 0,
                "window_end": we,
            }
        )

    boot = pd.DataFrame(extra_rows)
    merged = pd.concat([boot, agg], ignore_index=True).sort_values("window_start").reset_index(drop=True)
    return merged




def run_preprocess() -> None:
    """Aggregate 5-min windows, write processed table, and export .npy arrays per location, including ETA and weather."""
    init_db()
    session = SessionLocal()

    try:
        raw_rows = session.query(RawTraffic).order_by(RawTraffic.timestamp.asc()).all()
        if not raw_rows:
            print("[PREPROCESS] No raw records found. Run ingest.py first.")
            return

        records = [
            {
                "location_name": r.location_name,
                "timestamp": r.timestamp,
                "current_speed": r.current_speed,
                "congestion_index": r.congestion_index,
                "confidence": r.confidence,
                "eta_seconds": getattr(r, "eta_seconds", None),
                "weather_main": getattr(r, "weather_main", None),
                "weather_description": getattr(r, "weather_description", None),
                "weather_temp": getattr(r, "weather_temp", None),
                "weather_humidity": getattr(r, "weather_humidity", None),
                "weather_rain": getattr(r, "weather_rain", None),
            }
            for r in raw_rows
        ]
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

        # Clear old processed entries to keep this script idempotent.
        session.query(ProcessedTraffic).delete()
        session.commit()

        export_root = Path(__file__).parent / "model" / "training_data"
        export_root.mkdir(parents=True, exist_ok=True)

        for location, gdf in df.groupby("location_name"):
            loc = gdf.set_index("timestamp").sort_index()
            agg = loc.resample("5min").agg(
                avg_speed=("current_speed", "mean"),
                min_speed=("current_speed", "min"),
                max_speed=("current_speed", "max"),
                avg_congestion_index=("congestion_index", "mean"),
                avg_confidence=("confidence", "mean"),
                sample_count=("current_speed", "count"),
                eta_seconds=("eta_seconds", "mean"),
                crowd_density=("crowd_density", "mean"),
                weather_main=("weather_main", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
                weather_description=("weather_description", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
                weather_temp=("weather_temp", "mean"),
                weather_humidity=("weather_humidity", "mean"),
                weather_rain=("weather_rain", "mean"),
            )
            # Avoid dropping windows just because optional weather/eta fields are missing.
            # Keep windows that have core metrics (speed and congestion) and fill
            # optional fields with sensible defaults so downstream sequence export
            # can produce more training windows even when weather is unavailable.
            agg = agg.reset_index().rename(columns={"timestamp": "window_start"})
            # Drop empty resampled windows (no raw samples) before bootstrapping.
            if "sample_count" in agg.columns:
                agg = agg[agg["sample_count"] > 0]
            if agg.empty:
                continue

            agg["window_end"] = agg["window_start"] + pd.Timedelta(minutes=5)
            agg = _bootstrap_windows(agg)

            # Fill optional numeric fields with 0 and categorical weather with 'unknown'
            # after bootstrapping so synthetic rows also get defaults.
            if "eta_seconds" in agg.columns:
                agg["eta_seconds"] = agg["eta_seconds"].fillna(0.0)
            if "crowd_density" in agg.columns:
                agg["crowd_density"] = agg["crowd_density"].fillna(0.0)
            for col in ("weather_temp", "weather_humidity", "weather_rain"):
                if col in agg.columns:
                    agg[col] = agg[col].fillna(0.0)
            for col in ("weather_main", "weather_description"):
                if col in agg.columns:
                    agg[col] = agg[col].fillna("unknown")
            if agg.empty:
                continue

            

            speed_min = float(agg["avg_speed"].min())
            speed_max = float(agg["avg_speed"].max())
            cong_min = float(agg["avg_congestion_index"].min())
            cong_max = float(agg["avg_congestion_index"].max())

            speed_den = (speed_max - speed_min) if speed_max != speed_min else 1.0
            cong_den = (cong_max - cong_min) if cong_max != cong_min else 1.0

            agg["norm_speed"] = (agg["avg_speed"] - speed_min) / speed_den
            agg["norm_congestion"] = (agg["avg_congestion_index"] - cong_min) / cong_den

            hours = agg["window_start"].dt.hour + (agg["window_start"].dt.minute / 60.0)
            agg["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
            agg["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)
            agg["congestion_label"] = agg["avg_congestion_index"].apply(_label)

            for _, row in agg.iterrows():
                session.add(
                    ProcessedTraffic(
                        location_name=location,
                        window_start=row["window_start"].to_pydatetime(),
                        window_end=row["window_end"].to_pydatetime(),
                        avg_speed=float(row["avg_speed"]),
                        min_speed=float(row["min_speed"]),
                        max_speed=float(row["max_speed"]),
                        avg_congestion_index=float(row["avg_congestion_index"]),
                        avg_confidence=float(row["avg_confidence"]),
                        sample_count=int(row["sample_count"]),
                        norm_speed=float(row["norm_speed"]),
                        norm_congestion=float(row["norm_congestion"]),
                        hour_sin=float(row["hour_sin"]),
                        hour_cos=float(row["hour_cos"]),
                        congestion_label=str(row["congestion_label"]),
                        eta_seconds=float(row["eta_seconds"]) if row["eta_seconds"] is not None else None,
                        weather_main=row["weather_main"],
                        weather_description=row["weather_description"],
                        weather_temp=float(row["weather_temp"]) if row["weather_temp"] is not None else None,
                        weather_humidity=float(row["weather_humidity"]) if row["weather_humidity"] is not None else None,
                        weather_rain=float(row["weather_rain"]) if row["weather_rain"] is not None else None,
                    )
                )

            x, y = _to_sequences(agg)
            np.save(export_root / f"X_{location.lower().replace(' ', '_')}.npy", x)
            np.save(export_root / f"y_{location.lower().replace(' ', '_')}.npy", y)
            print(
                f"[PREPROCESS] {location}: windows={len(agg)} X={x.shape} y={y.shape} "
                f"generated_at={datetime.utcnow().isoformat()}Z"
            )

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    run_preprocess()
