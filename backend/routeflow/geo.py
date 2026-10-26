
"""India-wide geocoding, road distances and route geometry.

Free services:
- Nominatim / OpenStreetMap: location search
- OSRM: road distance, duration and route geometry

If routing is unavailable, estimated distances and durations are returned.
No API keys are required.

Distance units:
- distance_km: kilometres
- duration_s: seconds
- route geometry: (latitude, longitude) pairs
"""

import functools
import math
import os
import time

import requests

NOMINATIM_URL = os.getenv(
    "ROUTEFLOW_NOMINATIM_URL",
    "https://nominatim.openstreetmap.org",
).rstrip("/")

OSRM_URL = os.getenv(
    "ROUTEFLOW_OSRM_URL",
    "https://router.project-osrm.org",
).rstrip("/")

CONTACT = os.getenv("ROUTEFLOW_CONTACT", "student-project")
HEADERS = {"User-Agent": f"RouteFlow/2.0 ({CONTACT})"}

TIMEOUT = 15
CIRCUITY = 1.35
FALLBACK_KMH = 28.0


def ttl_cache(seconds):
    """Cache function results for a limited time."""

    def deco(fn):
        store = {}

        @functools.wraps(fn)
        def wrapper(*args):
            now = time.time()
            hit = store.get(args)

            if hit and now - hit[0] < seconds:
                return hit[1]

            value = fn(*args)
            store[args] = (now, value)
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return deco


def haversine_km(a, b):
    """Calculate straight-line distance between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        (a[0], a[1], b[0], b[1]),
    )

    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin((lon2 - lon1) / 2) ** 2
    )

    return 6371.0088 * 2 * math.asin(
        math.sqrt(min(1.0, h))
    )


def _valid_point(point):
    """Validate and normalize a latitude/longitude pair."""
    if len(point) != 2:
        raise ValueError("Each point must contain latitude and longitude.")

    lat = float(point[0])
    lon = float(point[1])

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError("Coordinates must be finite numbers.")

    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}")

    if not -180 <= lon <= 180:
        raise ValueError(f"Invalid longitude: {lon}")

    return lat, lon


@ttl_cache(3600)
def geocode(query):
    """Search Indian addresses and return up to five candidates.

    Returns:
        [
            {"label": "...", "lat": 26.9, "lon": 75.8},
            ...
        ]
    """
    query = (query or "").strip()

    if len(query) < 3:
        return []

    search_query = query

    if "india" not in query.lower():
        search_query = f"{query}, India"

    try:
        response = requests.get(
            f"{NOMINATIM_URL}/search",
            headers=HEADERS,
            timeout=TIMEOUT,
            params={
                "q": search_query,
                "format": "jsonv2",
                "limit": 5,
                "countrycodes": "in",
                "addressdetails": 1,
            },
        )

        response.raise_for_status()
        results = response.json()

        candidates = []

        for item in results:
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])

                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue

                candidates.append({
                    "label": item["display_name"],
                    "lat": lat,
                    "lon": lon,
                })

            except (KeyError, ValueError, TypeError):
                continue

        return candidates

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):
        return []


def _lonlat(points):
    """Convert (lat, lon) points to the coordinate format OSRM expects."""
    return ";".join(
        f"{lon:.6f},{lat:.6f}"
        for lat, lon in points
    )


def _estimate_matrices(points):
    """Estimate distance and duration matrices if road routing fails.

    The estimate uses straight-line distance multiplied by CIRCUITY.
    Estimated travel time uses FALLBACK_KMH.

    These estimates are not real road-network measurements.
    """
    n = len(points)

    dist = [[0.0] * n for _ in range(n)]
    dur = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            km = haversine_km(points[i], points[j]) * CIRCUITY

            dist[i][j] = km
            dur[i][j] = km / FALLBACK_KMH * 3600.0

    return dist, dur


@ttl_cache(900)
def road_matrix(points):
    """Return road distance and duration matrices.

    Input:
        tuple of (latitude, longitude) pairs

    Output:
        {
            "distance_km": matrix in kilometres,
            "duration_s": matrix in seconds,
            "source": "osrm", "mixed", or "estimate",
            "note": explanatory information
        }

    "osrm":
        All origin-destination pairs were routed by OSRM.

    "mixed":
        OSRM was used, but one or more pairs needed estimates.

    "estimate":
        The OSRM request failed and the whole matrix is estimated.
    """
    points = tuple(_valid_point(p) for p in points)

    estimated_dist, estimated_dur = _estimate_matrices(points)

    if len(points) < 2:
        return {
            "distance_km": estimated_dist,
            "duration_s": estimated_dur,
            "source": "estimate",
            "note": "At least two locations are required for road routing.",
        }

    try:
        response = requests.get(
            f"{OSRM_URL}/table/v1/driving/{_lonlat(points)}",
            headers=HEADERS,
            timeout=TIMEOUT,
            params={
                "annotations": "distance,duration",
            },
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok":
            raise ValueError(
                data.get("message", "OSRM routing error")
            )

        distances = data["distances"]
        durations = data["durations"]
        n = len(points)

        if (
            len(distances) != n
            or len(durations) != n
            or any(len(row) != n for row in distances)
            or any(len(row) != n for row in durations)
        ):
            raise ValueError("OSRM returned a matrix with an unexpected shape.")

        dist = []
        dur = []
        estimated_pairs = 0

        for i in range(n):
            drow = []
            trow = []

            for j in range(n):
                if i == j:
                    drow.append(0.0)
                    trow.append(0.0)
                    continue

                d = distances[i][j]
                t = durations[i][j]

                if d is None or t is None:
                    drow.append(estimated_dist[i][j])
                    trow.append(estimated_dur[i][j])
                    estimated_pairs += 1
                else:
                    d = float(d)
                    t = float(t)

                    if (
                        not math.isfinite(d)
                        or not math.isfinite(t)
                        or d < 0
                        or t < 0
                    ):
                        drow.append(estimated_dist[i][j])
                        trow.append(estimated_dur[i][j])
                        estimated_pairs += 1
                    else:
                        drow.append(d / 1000.0)
                        trow.append(t)

            dist.append(drow)
            dur.append(trow)

        note = ""

        if estimated_pairs:
            note = (
                f"{estimated_pairs} origin-destination pair(s) used "
                "estimated distances and durations because OSRM could "
                "not route them."
            )

        return {
            "distance_km": dist,
            "duration_s": dur,
            "source": "mixed" if estimated_pairs else "osrm",
            "note": note,
        }

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        return {
            "distance_km": estimated_dist,
            "duration_s": estimated_dur,
            "source": "estimate",
            "note": (
                f"OSRM road routing unavailable ({type(exc).__name__}); "
                f"using estimated distances and durations. Details: {exc}"
            ),
        }


@ttl_cache(900)
def route_geometry(points):
    """Return road-following geometry for an ordered route.

    Output:
        {
            "path": list of (latitude, longitude) pairs,
            "source": "osrm" or "estimate"
        }
    """
    points = tuple(_valid_point(p) for p in points)

    straight = {
        "path": list(points),
        "source": "estimate",
    }

    if len(points) < 2:
        return straight

    try:
        response = requests.get(
            f"{OSRM_URL}/route/v1/driving/{_lonlat(points)}",
            headers=HEADERS,
            timeout=TIMEOUT,
            params={
                "overview": "full",
                "geometries": "geojson",
            },
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return straight

        coordinates = data["routes"][0]["geometry"]["coordinates"]

        if not coordinates:
            return straight

        path = []

        for coordinate in coordinates:
            if len(coordinate) < 2:
                continue

            lon, lat = float(coordinate[0]), float(coordinate[1])

            if not (
                math.isfinite(lat)
                and math.isfinite(lon)
                and -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                continue

            path.append((lat, lon))

        if len(path) < 2:
            return straight

        return {
            "path": path,
            "source": "osrm",
        }

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ):
        return straight
