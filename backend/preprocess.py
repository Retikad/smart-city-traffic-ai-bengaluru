"""Preprocessing pipeline for feature engineering and sequence export."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from database import ProcessedTraffic, RawTraffic, SessionLocal, init_db

SEQUENCE_LEN = 12
FEATURE_COLUMNS = ["norm_speed", "norm_congestion", "hour_sin", "hour_cos"]


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
    target = df["norm_congestion"].to_numpy(dtype=np.float32)

    for idx in range(SEQUENCE_LEN, len(df)):
        x_rows.append(feats[idx - SEQUENCE_LEN : idx])
        y_rows.append(target[idx])

    if not x_rows:
        return np.empty((0, SEQUENCE_LEN, 4), dtype=np.float32), np.empty((0,), dtype=np.float32)

    return np.stack(x_rows).astype(np.float32), np.array(y_rows, dtype=np.float32)


def run_preprocess() -> None:
    """Aggregate 15-min windows, write processed table, and export .npy arrays per location."""
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
            agg = loc.resample("15min").agg(
                avg_speed=("current_speed", "mean"),
                min_speed=("current_speed", "min"),
                max_speed=("current_speed", "max"),
                avg_congestion_index=("congestion_index", "mean"),
                avg_confidence=("confidence", "mean"),
                sample_count=("current_speed", "count"),
            )
            agg = agg.dropna().reset_index().rename(columns={"timestamp": "window_start"})
            if agg.empty:
                continue

            agg["window_end"] = agg["window_start"] + pd.Timedelta(minutes=15)

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
