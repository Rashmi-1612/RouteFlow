
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from routeflow import db, geo, planner
from routeflow.live import live_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("routeflow")

app = FastAPI(title="RouteFlow API", version="1.0.0")

# Allow the React/Vite frontend to communicate with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    demand: int = Field(default=1, ge=0, le=5000)
    service_min: int = Field(default=5, ge=0, le=600)


class PlanRequest(BaseModel):
    objective: str = "distance"
    algorithm: str = "NN + 2-opt/Or-opt"
    couriers: int = Field(default=1, ge=1, le=8)
    capacity: int = Field(default=14, ge=1, le=5000)
    use_weather: bool = False
    use_traffic: bool = True


def clear_route_caches():
    """Clear cached geographic data when supported."""
    for function_name in ("road_matrix", "route_geometry"):
        function = getattr(geo, function_name, None)
        clear = getattr(function, "cache_clear", None)

        if callable(clear):
            clear()


def get_locations_safely():
    """Retrieve locations and log unexpected database errors."""
    try:
        locations = db.list_locations()
        return list(locations)
    except Exception:
        logger.exception("Could not retrieve locations from the database.")
        raise HTTPException(
            status_code=500,
            detail="Could not load locations. Check the backend terminal for details.",
        )


@app.get("/")
def root():
    return {
        "name": "RouteFlow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    try:
        return {
            "ok": True,
            "database": db.backend_name(),
        }
    except Exception:
        logger.exception("Health check failed.")
        raise HTTPException(
            status_code=500,
            detail="Health check failed. Check the backend terminal.",
        )


@app.get("/api/locations")
def get_locations():
    return get_locations_safely()


@app.post("/api/locations")
def create_location(payload: LocationCreate):
    try:
        db.add_location(
            payload.name,
            payload.address,
            payload.lat,
            payload.lon,
            payload.demand,
            payload.service_min,
        )

        clear_route_caches()

        return {
            "ok": True,
            "locations": get_locations_safely(),
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Failed to create a location.")
        raise HTTPException(
            status_code=500,
            detail="Could not save the location. Check the backend terminal.",
        )


@app.delete("/api/locations/{location_id}")
def remove_location(location_id: int):
    try:
        db.delete_location(location_id)
        clear_route_caches()

        return {
            "ok": True,
            "locations": get_locations_safely(),
        }

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Failed to delete location %s.", location_id)
        raise HTTPException(
            status_code=500,
            detail="Could not delete the location. Check the backend terminal.",
        )


@app.post("/api/locations/{location_id}/make-hub")
def make_hub(location_id: int):
    try:
        locations = get_locations_safely()
        known_ids = {
            location["location_id"]
            for location in locations
            if location.get("location_id") is not None
        }

        if location_id not in known_ids:
            raise HTTPException(
                status_code=404,
                detail="Location not found.",
            )

        db.set_hub(location_id)
        clear_route_caches()

        return {
            "ok": True,
            "locations": get_locations_safely(),
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to set hub %s.", location_id)
        raise HTTPException(
            status_code=500,
            detail="Could not update the hub. Check the backend terminal.",
        )


@app.get("/api/geocode")
def search_address(q: str):
    if len(q.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Enter at least 3 characters.",
        )

    try:
        return geo.geocode(q.strip())
    except Exception:
        logger.exception("Address search failed for query %r.", q)
        raise HTTPException(
            status_code=502,
            detail="Address search failed. Check your internet connection and backend terminal.",
        )


@app.get("/api/algorithms")
def get_algorithms():
    try:
        return [
            {
                "name": name,
                "description": description,
            }
            for name, (_, _, description) in planner.ALGORITHMS.items()
        ]
    except Exception:
        logger.exception("Could not load optimization algorithms.")
        raise HTTPException(
            status_code=500,
            detail="Could not load algorithms. Check the backend terminal.",
        )


@app.post("/api/plan")
def create_plan(payload: PlanRequest):
    locations = get_locations_safely()

    if len(locations) < 2:
        raise HTTPException(
            status_code=400,
            detail="Add at least one delivery stop and a hub before planning.",
        )

    if payload.objective not in {"distance", "time"}:
        raise HTTPException(
            status_code=400,
            detail="Objective must be 'distance' or 'time'.",
        )

    if payload.algorithm not in planner.ALGORITHMS:
        raise HTTPException(
            status_code=400,
            detail="Unknown algorithm. Refresh the algorithm list and try again.",
        )

    required_fields = {
        "location_id",
        "location_name",
        "latitude",
        "longitude",
        "demand",
        "service_min",
    }

    for index, location in enumerate(locations):
        missing = required_fields - location.keys()

        if missing:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Location at index {index} is missing required fields: "
                    f"{', '.join(sorted(missing))}."
                ),
            )

    try:
        points = tuple(
            (
                float(location["latitude"]),
                float(location["longitude"]),
            )
            for location in locations
        )

        matrix = geo.road_matrix(points)

        hub = locations[0]

        context = live_context(
            float(hub["latitude"]),
            float(hub["longitude"]),
            payload.use_weather,
            payload.use_traffic,
        )

        factor = float(context.get("factor", 1.0))

        adjusted_duration = [
            [value * factor for value in row]
            for row in matrix["duration_s"]
        ]

        if payload.objective == "distance":
            objective_matrix = matrix["distance_km"]
        else:
            objective_matrix = [
                [value / 60 for value in row]
                for row in adjusted_duration
            ]

        clusters, warnings = planner.assign_stops(
            objective_matrix,
            [location["demand"] for location in locations],
            payload.couriers,
            payload.capacity,
        )

        try:
            result = planner.run_algorithm(
                payload.algorithm,
                objective_matrix,
                matrix["distance_km"],
                adjusted_duration,
                clusters,
            )
        except planner.LimitExceeded as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        names = [
            location["location_name"]
            for location in locations
        ]

        coordinates = [
            (
                location["latitude"],
                location["longitude"],
            )
            for location in locations
        ]

        geometry_routes = []
        schedules = []

        for route_indices in result["routes"]:
            geometry = geo.route_geometry(
                tuple(coordinates[index] for index in route_indices)
            )

            geometry_routes.append(
                {
                    "indices": route_indices,
                    "path": geometry["path"],
                    "source": geometry["source"],
                    "names": [
                        names[index] for index in route_indices
                    ],
                }
            )

            schedules.append(
                planner.build_schedule(
                    route_indices,
                    names,
                    adjusted_duration,
                    matrix["distance_km"],
                    [
                        location["service_min"]
                        for location in locations
                    ],
                    datetime.now(),
                )
            )

        return {
            "algorithm": result["algorithm"],
            "total_km": round(result["total_km"], 2),
            "total_min": round(result["total_min"], 1),
            "time_ms": round(result["time_ms"], 3),
            "source": matrix["source"],
            "note": matrix["note"],
            "delay_factor": factor,
            "warnings": warnings,
            "locations": locations,
            "routes": geometry_routes,
            "schedules": schedules,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Route optimization failed.")
        raise HTTPException(
            status_code=500,
            detail="Route optimization failed. Check the backend terminal for the traceback.",
        )


@app.get("/api/history")
def history():
    try:
        frame = db.list_runs()

        if frame is None or frame.empty:
            return []

        return frame.fillna("").to_dict(orient="records")

    except Exception:
        logger.exception("Could not retrieve route history.")
        raise HTTPException(
            status_code=500,
            detail="Could not load route history. Check the backend terminal.",
        )
