"""Database models and session management for Bengaluru traffic system."""

from __future__ import annotations

from datetime import datetime
import os

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, mapped_column, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bengaluru_traffic.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


CORRIDORS = {
    "MG Road": {"lat": 12.9757, "lng": 77.6011},
    "Silk Board Junction": {"lat": 12.9176, "lng": 77.6230},
    "Whitefield": {"lat": 12.9698, "lng": 77.7500},
    "Electronic City": {"lat": 12.8452, "lng": 77.6602},
    "Hebbal Flyover": {"lat": 13.0350, "lng": 77.5970},
    "Koramangala": {"lat": 12.9352, "lng": 77.6245},
    "Church Street": {"lat": 12.9755, "lng": 77.6058},
    "JP Nagar": {"lat": 12.9077, "lng": 77.5850},
    "Jayanagar": {"lat": 12.9250, "lng": 77.5938},
    "Commercial Street": {"lat": 12.9826, "lng": 77.6088},
    "KR Market": {"lat": 12.9633, "lng": 77.5760},
    # New corridors
    "Banashankari": {"lat": 12.9182, "lng": 77.5736},
    "Yeshwanthpur": {"lat": 13.0285, "lng": 77.5505},
    "Marathahalli": {"lat": 12.9569, "lng": 77.7011},
    "Indiranagar": {"lat": 12.9716, "lng": 77.6401},
    "BTM Layout": {"lat": 12.9166, "lng": 77.6101},
}



class RawTraffic(Base):
    """Raw traffic readings pulled from TomTom flow API, with ETA and weather."""

    __tablename__ = "raw_traffic"

    id = mapped_column(Integer, primary_key=True, index=True)
    location_name = mapped_column(String(100), index=True, nullable=False)
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)
    timestamp = mapped_column(DateTime, index=True, nullable=False)
    current_speed = mapped_column(Float, nullable=False)
    free_flow_speed = mapped_column(Float, nullable=False)
    current_travel_time = mapped_column(Float, nullable=False)
    free_flow_travel_time = mapped_column(Float, nullable=False)
    confidence = mapped_column(Float, nullable=False)
    road_closure = mapped_column(Boolean, nullable=False, default=False)
    congestion_index = mapped_column(Float, nullable=False)
    crowd_density = mapped_column(Float, nullable=True)
    # ETA prediction (seconds)
    eta_seconds = mapped_column(Float, nullable=True)
    # Weather fields
    weather_main = mapped_column(String(32), nullable=True)
    weather_description = mapped_column(String(64), nullable=True)
    weather_temp = mapped_column(Float, nullable=True)
    weather_humidity = mapped_column(Float, nullable=True)
    weather_rain = mapped_column(Float, nullable=True)



class ProcessedTraffic(Base):
    """Windowed and engineered traffic features for model training/inference, with ETA and weather."""

    __tablename__ = "processed_traffic"

    id = mapped_column(Integer, primary_key=True, index=True)
    location_name = mapped_column(String(100), index=True, nullable=False)
    window_start = mapped_column(DateTime, index=True, nullable=False)
    window_end = mapped_column(DateTime, index=True, nullable=False)
    avg_speed = mapped_column(Float, nullable=False)
    min_speed = mapped_column(Float, nullable=False)
    max_speed = mapped_column(Float, nullable=False)
    avg_congestion_index = mapped_column(Float, nullable=False)
    avg_confidence = mapped_column(Float, nullable=False)
    sample_count = mapped_column(Integer, nullable=False)
    norm_speed = mapped_column(Float, nullable=False)
    norm_congestion = mapped_column(Float, nullable=False)
    hour_sin = mapped_column(Float, nullable=False)
    hour_cos = mapped_column(Float, nullable=False)
    congestion_label = mapped_column(String(20), nullable=False)
    crowd_density = mapped_column(Float, nullable=True)
    # ETA prediction (seconds)
    eta_seconds = mapped_column(Float, nullable=True)
    # Weather fields
    weather_main = mapped_column(String(32), nullable=True)
    weather_description = mapped_column(String(64), nullable=True)
    weather_temp = mapped_column(Float, nullable=True)
    weather_humidity = mapped_column(Float, nullable=True)
    weather_rain = mapped_column(Float, nullable=True)


def init_db() -> None:
    """Create all database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_URL} ({datetime.utcnow().isoformat()}Z)")
