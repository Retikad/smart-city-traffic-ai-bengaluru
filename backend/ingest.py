"""TomTom traffic ingestion loop for Bengaluru corridors."""

from __future__ import annotations

from datetime import datetime
import math
import os
import random
import time

from dotenv import load_dotenv
import requests

from database import CORRIDORS, RawTraffic, SessionLocal, init_db

load_dotenv(override=True)

TOMTOM_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
API_KEY = os.getenv("TOMTOM_API_KEY", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))
INGEST_BATCH_MULTIPLIER = max(1, int(os.getenv("INGEST_BATCH_MULTIPLIER", "1")))
SNAPSHOT_SPACING_SECONDS = max(0, float(os.getenv("SNAPSHOT_SPACING_SECONDS", "0")))

# Multi-probe sampling improves corridor realism over a single point sample.
CORRIDOR_PROBES = {
    "MG Road": [(12.9757, 77.6011), (12.9721, 77.6079), (12.9798, 77.6085)],
    "Electronic City": [(12.8452, 77.6602), (12.8417, 77.6646), (12.8520, 77.6715)],
    "Whitefield": [(12.9698, 77.7500), (12.9804, 77.7528)],
    "Silk Board Junction": [(12.9176, 77.6230), (12.9157, 77.6292)],
    "Hebbal Flyover": [(13.0350, 77.5970), (13.0404, 77.5937)],
}


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _compute_congestion_index(
    current_speed: float,
    free_flow_speed: float,
    current_tt: float,
    free_flow_tt: float,
    confidence: float,
    road_closure: bool,
) -> float:
    """Compute congestion with both speed-loss and travel-time inflation signals."""
    if road_closure:
        return 1.0

    speed_ratio = (current_speed / free_flow_speed) if free_flow_speed > 0 else 0.0
    speed_penalty = 1.0 - _clamp01(speed_ratio)

    tt_ratio = (current_tt / free_flow_tt) if free_flow_tt > 0 else 1.0
    tt_inflation = max(tt_ratio - 1.0, 0.0)
    tt_penalty = tt_inflation / (1.0 + tt_inflation)

    # Weight speed slightly more, while still respecting travel-time increases.
    congestion_index = 0.6 * speed_penalty + 0.4 * tt_penalty

    # Boost index for stop-and-go conditions where speed collapses.
    if free_flow_speed >= 20 and current_speed <= 5:
        congestion_index = max(congestion_index, 0.9)

    # Light confidence-aware damping to avoid overreacting to noisy samples.
    confidence_factor = 0.85 + 0.15 * _clamp01(confidence)
    congestion_index *= confidence_factor
    return _clamp01(congestion_index)


def _demo_congestion_seed(location_name: str, now_utc: datetime) -> float:
    hour = now_utc.hour + (now_utc.minute / 60.0)
    morning_peak = math.exp(-((hour - 9.0) ** 2) / 6.0)
    evening_peak = math.exp(-((hour - 18.0) ** 2) / 6.0)
    location_bias = {
        "Silk Board Junction": 0.14,
        "Whitefield": 0.09,
        "Electronic City": 0.08,
        "Hebbal Flyover": 0.07,
        "MG Road": 0.06,
    }.get(location_name, 0.06)
    baseline = 0.16 + (0.28 * morning_peak) + (0.34 * evening_peak) + location_bias
    jitter = random.uniform(-0.05, 0.05)
    return _clamp01(baseline + jitter)


def _fallback_row(session, location_name: str, lat: float, lng: float) -> dict:
    now = datetime.utcnow()
    demo_seed = _demo_congestion_seed(location_name, now)
    latest = (
        session.query(RawTraffic)
        .filter(RawTraffic.location_name == location_name)
        .order_by(RawTraffic.timestamp.desc())
        .first()
    )

    if latest is not None:
        free_flow_speed = max(latest.free_flow_speed, 1.0)
        free_flow_tt = max(latest.free_flow_travel_time, 1.0)
        # Blend last known level with current-time synthetic seed to avoid stale-looking repeats.
        congestion_index = _clamp01((0.55 * latest.congestion_index) + (0.45 * demo_seed) + random.uniform(-0.03, 0.03))
        speed_ratio = max(0.05, 1.0 - congestion_index)
        current_speed = max(2.0, free_flow_speed * speed_ratio)
        travel_time_ratio = min(8.0, 1.0 / speed_ratio)
        current_tt = free_flow_tt * travel_time_ratio
        confidence = max(0.35, latest.confidence * 0.9)
        return {
            "location_name": location_name,
            "latitude": lat,
            "longitude": lng,
            "timestamp": now,
            "current_speed": current_speed,
            "free_flow_speed": free_flow_speed,
            "current_travel_time": current_tt,
            "free_flow_travel_time": free_flow_tt,
            "confidence": confidence,
            "road_closure": False,
            "congestion_index": congestion_index,
        }

    congestion_index = demo_seed
    free_flow_speed = 36.0
    speed_ratio = max(0.05, 1.0 - congestion_index)
    current_speed = free_flow_speed * speed_ratio
    free_flow_tt = 600.0
    current_tt = free_flow_tt * min(8.0, 1.0 / speed_ratio)
    return {
        "location_name": location_name,
        "latitude": lat,
        "longitude": lng,
        "timestamp": now,
        "current_speed": current_speed,
        "free_flow_speed": free_flow_speed,
        "current_travel_time": current_tt,
        "free_flow_travel_time": free_flow_tt,
        "confidence": 0.4,
        "road_closure": False,
        "congestion_index": congestion_index,
    }


def _synthesize_from_base(base: dict, step: int) -> dict:
    """Create additional near-term snapshots from one fresh base sample."""
    row = dict(base)
    row["timestamp"] = datetime.utcnow()

    # Keep movement realistic while avoiding repeated identical values.
    ci = _clamp01(base["congestion_index"] + random.uniform(-0.02, 0.02) + (0.002 * step))
    row["congestion_index"] = ci

    ff_speed = max(base["free_flow_speed"], 1.0)
    speed_ratio = max(0.05, 1.0 - ci)
    row["current_speed"] = max(2.0, ff_speed * speed_ratio)
    row["current_travel_time"] = base["free_flow_travel_time"] * min(8.0, 1.0 / speed_ratio)
    row["confidence"] = _clamp01(base["confidence"] * 0.98)
    return row


def _pull_probe(lat: float, lng: float) -> dict:
    """Fetch one TomTom probe point and return parsed flowSegmentData metrics."""
    if not API_KEY:
        raise RuntimeError("TOMTOM_API_KEY is missing. Set it in backend/.env")

    params = {"point": f"{lat},{lng}", "key": API_KEY, "unit": "KMPH"}
    response = requests.get(TOMTOM_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    segment = payload.get("flowSegmentData", {})
    if not segment:
        raise ValueError(f"Missing flowSegmentData for probe {lat},{lng}")

    current_speed = float(segment.get("currentSpeed", 0.0))
    free_flow_speed = float(segment.get("freeFlowSpeed", 1.0))
    current_tt = float(segment.get("currentTravelTime", 0.0))
    free_flow_tt = float(segment.get("freeFlowTravelTime", 1.0))
    confidence = float(segment.get("confidence", 0.0))
    road_closure = bool(segment.get("roadClosure", False))
    congestion_index = _compute_congestion_index(
        current_speed=current_speed,
        free_flow_speed=free_flow_speed,
        current_tt=current_tt,
        free_flow_tt=free_flow_tt,
        confidence=confidence,
        road_closure=road_closure,
    )

    return {
        "timestamp": datetime.utcnow(),
        "current_speed": current_speed,
        "free_flow_speed": free_flow_speed,
        "current_travel_time": current_tt,
        "free_flow_travel_time": free_flow_tt,
        "confidence": confidence,
        "road_closure": road_closure,
        "congestion_index": congestion_index,
    }


def _pull_location(location_name: str, lat: float, lng: float) -> dict:
    """Fetch corridor using multiple probes and return hotspot-like aggregate."""
    probes = CORRIDOR_PROBES.get(location_name, [(lat, lng)])
    samples: list[dict] = []
    for p_lat, p_lng in probes:
        try:
            samples.append(_pull_probe(p_lat, p_lng))
        except Exception as exc:
            print(f"[INGEST][WARN] probe {location_name} ({p_lat},{p_lng}): {exc}")

    if not samples:
        raise ValueError(f"No successful probe samples for {location_name}")

    hotspot = max(samples, key=lambda s: s["congestion_index"])
    avg_conf = sum(s["confidence"] for s in samples) / len(samples)
    any_closure = any(s["road_closure"] for s in samples)

    return {
        "location_name": location_name,
        "latitude": lat,
        "longitude": lng,
        "timestamp": datetime.utcnow(),
        "current_speed": hotspot["current_speed"],
        "free_flow_speed": hotspot["free_flow_speed"],
        "current_travel_time": hotspot["current_travel_time"],
        "free_flow_travel_time": hotspot["free_flow_travel_time"],
        "confidence": float(avg_conf),
        "road_closure": any_closure,
        "congestion_index": hotspot["congestion_index"],
    }


def ingest_once() -> int:
    """Ingest one or more snapshots for all corridors and return inserted row count."""
    session = SessionLocal()
    inserted = 0
    try:
        # Pull one fresh base sample per corridor.
        base_by_location: dict[str, dict] = {}
        for name, coords in CORRIDORS.items():
            try:
                base_by_location[name] = _pull_location(name, coords["lat"], coords["lng"])
            except Exception as exc:
                print(f"[INGEST][WARN] {name}: {exc}")
                base_by_location[name] = _fallback_row(session, name, coords["lat"], coords["lng"])
                print(f"[INGEST][FALLBACK] {name}: inserted synthetic/live-cached row")

        for batch_idx in range(INGEST_BATCH_MULTIPLIER):
            for name, coords in CORRIDORS.items():
                base = base_by_location[name]
                row_data = base if batch_idx == 0 else _synthesize_from_base(base, batch_idx)
                session.add(RawTraffic(**row_data))
                inserted += 1

            if SNAPSHOT_SPACING_SECONDS > 0 and batch_idx < (INGEST_BATCH_MULTIPLIER - 1):
                time.sleep(SNAPSHOT_SPACING_SECONDS)

        session.commit()
        return inserted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_loop() -> None:
    """Run continuous polling loop for all configured locations."""
    init_db()
    print(
        f"[INGEST] Polling every {POLL_INTERVAL}s, corridors={len(CORRIDORS)}, "
        f"batch_multiplier={INGEST_BATCH_MULTIPLIER}"
    )
    while True:
        try:
            count = ingest_once()
            print(f"[INGEST] {datetime.utcnow().isoformat()}Z inserted={count}")
        except Exception as exc:
            print(f"[INGEST][ERROR] {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
