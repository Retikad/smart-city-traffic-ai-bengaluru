"""TomTom traffic ingestion loop for Bengaluru corridors."""

from __future__ import annotations

from datetime import datetime
import os
import time

from dotenv import load_dotenv
import requests

from database import CORRIDORS, RawTraffic, SessionLocal, init_db

load_dotenv()

TOMTOM_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
API_KEY = os.getenv("TOMTOM_API_KEY", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))


def _pull_location(location_name: str, lat: float, lng: float) -> dict:
    """Fetch one location from TomTom and return parsed flowSegmentData."""
    if not API_KEY:
        raise RuntimeError("TOMTOM_API_KEY is missing. Set it in backend/.env")

    params = {"point": f"{lat},{lng}", "key": API_KEY, "unit": "KMPH"}
    response = requests.get(TOMTOM_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    segment = payload.get("flowSegmentData", {})
    if not segment:
        raise ValueError(f"Missing flowSegmentData for {location_name}")

    current_speed = float(segment.get("currentSpeed", 0.0))
    free_flow_speed = float(segment.get("freeFlowSpeed", 1.0))
    current_tt = float(segment.get("currentTravelTime", 0.0))
    free_flow_tt = float(segment.get("freeFlowTravelTime", 1.0))
    confidence = float(segment.get("confidence", 0.0))
    road_closure = bool(segment.get("roadClosure", False))
    congestion_index = 1.0 - (current_speed / free_flow_speed) if free_flow_speed > 0 else 1.0
    congestion_index = min(max(congestion_index, 0.0), 1.0)

    return {
        "location_name": location_name,
        "latitude": lat,
        "longitude": lng,
        "timestamp": datetime.utcnow(),
        "current_speed": current_speed,
        "free_flow_speed": free_flow_speed,
        "current_travel_time": current_tt,
        "free_flow_travel_time": free_flow_tt,
        "confidence": confidence,
        "road_closure": road_closure,
        "congestion_index": congestion_index,
    }


def ingest_once() -> int:
    """Ingest one batch for all corridors and return inserted row count."""
    session = SessionLocal()
    inserted = 0
    try:
        for name, coords in CORRIDORS.items():
            try:
                row_data = _pull_location(name, coords["lat"], coords["lng"])
                row = RawTraffic(**row_data)
                session.add(row)
                inserted += 1
            except Exception as exc:
                print(f"[INGEST][WARN] {name}: {exc}")
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
    print(f"[INGEST] Polling every {POLL_INTERVAL} seconds for {len(CORRIDORS)} corridors")
    while True:
        try:
            count = ingest_once()
            print(f"[INGEST] {datetime.utcnow().isoformat()}Z inserted={count}")
        except Exception as exc:
            print(f"[INGEST][ERROR] {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
