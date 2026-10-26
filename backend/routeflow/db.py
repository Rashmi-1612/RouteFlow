"""Persistence with SQLAlchemy. SQLite by default (zero setup); MySQL if configured.

  DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/courier_optimizer
or the original variables COURIER_DB_HOST / _PORT / _USER / _PASSWORD / _NAME.
"""
import functools
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, func, insert, select, update)

metadata = MetaData()

locations = Table(
    "locations", metadata,
    Column("location_id", Integer, primary_key=True, autoincrement=True),
    Column("location_name", String(100), nullable=False),
    Column("address", String(255), nullable=False, default=""),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    Column("location_type", String(10), nullable=False, default="Delivery"),   # Hub | Delivery
    Column("demand", Integer, nullable=False, default=1),                      # parcels / load units
    Column("service_min", Integer, nullable=False, default=5),                 # minutes at the stop
)

optimization_runs = Table(
    "optimization_runs", metadata,
    Column("run_id", Integer, primary_key=True, autoincrement=True),
    Column("algorithm_name", String(50), nullable=False),
    Column("objective", String(20), nullable=False),
    Column("n_stops", Integer, nullable=False),
    Column("n_couriers", Integer, nullable=False),
    Column("total_distance_km", Float, nullable=False),
    Column("total_duration_min", Float, nullable=False),
    Column("route_sequence", Text, nullable=False),
    Column("execution_time_ms", Float, nullable=False),
    Column("data_source", String(20), nullable=False),
    Column("delay_factor", Float, nullable=False, default=1.0),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)),
)

DEMO_LOCATIONS = [  # name, address, lat, lon, type, demand, service_min
    ("Courier Hub", "Connaught Place, New Delhi", 28.6315, 77.2167, "Hub", 0, 0),
    ("India Gate", "India Gate, New Delhi", 28.6129, 77.2295, "Delivery", 3, 5),
    ("Red Fort", "Red Fort, Old Delhi", 28.6562, 77.2410, "Delivery", 2, 6),
    ("Jama Masjid", "Jama Masjid, Old Delhi", 28.6507, 77.2334, "Delivery", 4, 5),
    ("Humayun's Tomb", "Humayun's Tomb, Nizamuddin", 28.5933, 77.2507, "Delivery", 2, 4),
    ("Akshardham", "Akshardham Temple, Delhi", 28.6127, 77.2773, "Delivery", 5, 7),
    ("Lotus Temple", "Lotus Temple, Kalkaji", 28.5535, 77.2588, "Delivery", 3, 5),
    ("Hauz Khas Village", "Hauz Khas Village, South Delhi", 28.5494, 77.2001, "Delivery", 2, 5),
    ("Qutub Minar", "Qutub Minar, Mehrauli", 28.5245, 77.1855, "Delivery", 4, 6),
]


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.getenv("COURIER_DB_HOST") or os.getenv("COURIER_DB_PASSWORD"):
        user = os.getenv("COURIER_DB_USER", "root")
        pw = os.getenv("COURIER_DB_PASSWORD", "")
        host = os.getenv("COURIER_DB_HOST", "localhost")
        port = os.getenv("COURIER_DB_PORT", "3306")
        name = os.getenv("COURIER_DB_NAME", "courier_optimizer")
        return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{name}"
    return "sqlite:///routeflow.db"


@functools.lru_cache(maxsize=1)
def get_engine():
    url = database_url()
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)
    metadata.create_all(engine)
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(locations)).scalar() == 0:
            _insert_demo(conn)
    return engine


def _insert_demo(conn):
    for name, addr, lat, lon, typ, demand, service in DEMO_LOCATIONS:
        conn.execute(insert(locations).values(
            location_name=name, address=addr, latitude=lat, longitude=lon,
            location_type=typ, demand=demand, service_min=service))


def backend_name():
    return get_engine().dialect.name


def list_locations():
    """Hub first, then deliveries in insertion order. Returns list of dicts."""
    with get_engine().connect() as conn:
        rows = conn.execute(select(locations).order_by(locations.c.location_id)).mappings().all()
    rows = [dict(r) for r in rows]
    rows.sort(key=lambda r: (r["location_type"] != "Hub", r["location_id"]))
    return rows


def add_location(name, address, lat, lon, demand=1, service_min=5):
    name = name.strip()
    if not name:
        raise ValueError("Enter a location name.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude/longitude out of range.")
    with get_engine().begin() as conn:
        exists = conn.execute(select(locations.c.location_id).where(
            func.lower(locations.c.location_name) == name.lower())).first()
        if exists:
            raise ValueError("A location with this name already exists.")
        conn.execute(insert(locations).values(
            location_name=name, address=address or "", latitude=lat, longitude=lon,
            location_type="Delivery", demand=int(demand), service_min=int(service_min)))


def update_location(location_id, demand, service_min):
    with get_engine().begin() as conn:
        conn.execute(update(locations).where(locations.c.location_id == location_id)
                     .values(demand=int(demand), service_min=int(service_min)))


def delete_location(location_id):
    with get_engine().begin() as conn:
        typ = conn.execute(select(locations.c.location_type)
                           .where(locations.c.location_id == location_id)).scalar()
        if typ == "Hub":
            raise ValueError("The hub cannot be deleted - make another location the hub first.")
        conn.execute(delete(locations).where(locations.c.location_id == location_id))


def set_hub(location_id):
    with get_engine().begin() as conn:
        conn.execute(update(locations).values(location_type="Delivery", demand=locations.c.demand))
        conn.execute(update(locations).where(locations.c.location_id == location_id)
                     .values(location_type="Hub", demand=0, service_min=0))


def reset_demo():
    with get_engine().begin() as conn:
        conn.execute(delete(locations))
        _insert_demo(conn)


def save_run(row):
    with get_engine().begin() as conn:
        conn.execute(insert(optimization_runs).values(**row))


def list_runs():
    with get_engine().connect() as conn:
        return pd.read_sql(select(optimization_runs).order_by(
            optimization_runs.c.created_at.desc(), optimization_runs.c.run_id.desc()), conn)


def clear_runs():
    with get_engine().begin() as conn:
        conn.execute(delete(optimization_runs))