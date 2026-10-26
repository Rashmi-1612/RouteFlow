
"""RouteFlow planning logic.

Features:
- Assign delivery stops to couriers.
- Solve routes using exact and heuristic algorithms.
- Calculate road distance and driving duration.
- Generate arrival/departure schedules.
- Compare algorithms and benchmark their performance.

Units:
- Distance: kilometres
- Duration matrices: seconds
- Reported driving times: minutes
"""

import math
import random
import time
from datetime import timedelta
from urllib.parse import quote

from algorithms import (
    brute_force_tsp,
    clarke_wright,
    greedy_tsp,
    held_karp,
    local_search_tsp,
)


# Algorithm name -> (function, maximum nodes including hub, description)
ALGORITHMS = {
    "Held-Karp DP (exact)": (
        held_karp,
        16,
        "Bitmask dynamic programming, O(n^2 2^n)",
    ),
    "Brute Force (exact)": (
        brute_force_tsp,
        11,
        "Tries every ordering, O(n!)",
    ),
    "Nearest Neighbour": (
        greedy_tsp,
        None,
        "Greedy heuristic, O(n^2)",
    ),
    "NN + 2-opt/Or-opt": (
        local_search_tsp,
        80,
        "Greedy start + local search improvement",
    ),
}

EXACT = {
    "Held-Karp DP (exact)",
    "Brute Force (exact)",
}


class LimitExceeded(Exception):
    """Raised when an algorithm exceeds its supported route size."""


def submatrix(matrix, idx):
    """Extract a square submatrix using the specified indices."""
    return [
        [matrix[a][b] for b in idx]
        for a in idx
    ]


def solve_cluster(obj, stops, algorithm):
    """Solve a courier route starting and ending at hub index 0.

    Args:
        obj: Objective cost matrix.
        stops: Global location indices to visit.
        algorithm: Registered algorithm name.

    Returns:
        Route as global location indices, including hub at both ends.
    """
    if not stops:
        return [0, 0]

    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    fn, cap, _ = ALGORITHMS[algorithm]

    if cap and len(stops) + 1 > cap:
        raise LimitExceeded(
            f"{algorithm} handles at most {cap - 1} stops per route "
            f"(this route has {len(stops)})."
        )

    indices = [0] + list(stops)
    local_matrix = submatrix(obj, indices)

    _, local_route = fn(local_matrix)

    # Convert local submatrix indices back to global location indices.
    return [indices[i] for i in local_route]



def assign_stops(obj, demands, n_couriers, capacity):
    """Assign delivery stops to couriers.

    Returns:
        (clusters, warnings)

    Each cluster contains global location indices, excluding the hub.
    """
    n = len(obj)
    warnings = []

    if len(demands) != n:
        raise ValueError(
            "Demands must contain one entry per location."
        )

    if n <= 1:
        return [], warnings

    if n_couriers < 1:
        raise ValueError("At least one courier is required.")

    if capacity < 1:
        raise ValueError("Courier capacity must be at least 1.")

    for i in range(1, n):
        if demands[i] > capacity:
            raise ValueError(
                f"Stop {i} requires {demands[i]} parcels, "
                f"but courier capacity is {capacity}."
            )

    total_demand = sum(demands[1:])

    if total_demand > n_couriers * capacity:
        raise ValueError(
            f"Total delivery load {total_demand} exceeds fleet capacity "
            f"{n_couriers} x {capacity}. Increase capacity or add couriers."
        )

    # A single courier receives all stops, provided capacity allows it.
    if n_couriers == 1:
        if total_demand > capacity:
            raise ValueError(
                f"Total delivery load {total_demand} exceeds the "
                f"single courier capacity of {capacity}."
            )

        return [list(range(1, n))], warnings

    # Clarke-Wright builds routes while respecting capacity.
    routes = clarke_wright(
        obj,
        demands,
        capacity,
        n_couriers=n_couriers,
    )

    # If fewer routes were created than requested, split the longest
    # routes at customer boundaries, without changing customer coverage.
    routes = [route[1:-1] for route in routes]

    while len(routes) < min(n_couriers, n - 1):
        candidates = [
            (len(route), index)
            for index, route in enumerate(routes)
            if len(route) >= 2
        ]

        if not candidates:
            break

        _, index = max(candidates)
        route = routes.pop(index)

        midpoint = len(route) // 2
        left = route[:midpoint]
        right = route[midpoint:]

        if left and right:
            routes.extend([left, right])
        else:
            routes.append(route)
            break

    # Verify that all stops are assigned exactly once and each route
    # respects the capacity constraint.
    assigned = []

    for route in routes:
        if sum(demands[i] for i in route) > capacity:
            raise ValueError(
                "A generated courier route exceeds its capacity."
            )
        assigned.extend(route)

    expected = list(range(1, n))

    if sorted(assigned) != expected:
        raise ValueError(
            "Route assignment failed: a stop is missing or duplicated."
        )

    return routes, warnings

def route_totals(route, dist_km, dur_s):
    """Calculate distance and driving time for one route.

    Args:
        route: Ordered location indices.
        dist_km: Distance matrix in kilometres.
        dur_s: Duration matrix in seconds.

    Returns:
        (distance_km, driving_minutes)
    """
    total_km = 0.0
    total_seconds = 0.0

    for a, b in zip(route, route[1:]):
        total_km += float(dist_km[a][b])
        total_seconds += float(dur_s[a][b])

    return total_km, total_seconds / 60.0


def build_schedule(route, names, dur_s, dist_km, service_min, start):
    """Build an ETA schedule for one courier.

    Duration matrix values are seconds. They may already include
    a traffic adjustment applied by the calling code.

    Service time is added after arriving at each delivery stop.
    The final return to the hub has zero service time.
    """
    current_time = start
    rows = []

    for a, b in zip(route, route[1:]):
        leg_seconds = float(dur_s[a][b])
        leg_km = float(dist_km[a][b])

        current_time += timedelta(seconds=leg_seconds)
        arrival_time = current_time

        service = float(service_min[b]) if b != 0 else 0.0
        current_time += timedelta(minutes=service)

        rows.append({
            "From": names[a],
            "To": names[b] + (" (return)" if b == 0 else ""),
            "Leg km": round(leg_km, 2),
            "Leg min": round(leg_seconds / 60.0, 1),
            "Arrive": arrival_time.strftime("%H:%M"),
            "Depart": (
                current_time.strftime("%H:%M")
                if b != 0
                else "-"
            ),
            "Service min": round(service, 1),
        })

    return rows


def run_algorithm(algorithm, obj, dist_km, dur_s, clusters):
    """Solve courier routes and calculate summary metrics.

    Returns:
        algorithm: Selected algorithm.
        routes: Ordered routes, including hub at start and end.
        total_km: Sum of route distances across all couriers.
        total_min: Sum of driving minutes across all couriers.
        total_drive_min: Alias for total_min.
        makespan_min: Longest individual courier driving duration.
        route_metrics: Per-courier distance and driving time.
        time_ms: Solver runtime, excluding external routing API calls.

    Note:
        total_min is retained for compatibility with the existing API.
        With multiple couriers, total_min is fleet driving time, whereas
        makespan_min is the longest driving time of any one courier.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if not (
        len(obj) == len(dist_km) == len(dur_s)
    ):
        raise ValueError(
            "Objective, distance, and duration matrices must have "
            "the same number of rows."
        )

    start_time = time.perf_counter()

    routes = [
        solve_cluster(obj, cluster, algorithm)
        for cluster in clusters
    ]

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    total_km = 0.0
    total_drive_min = 0.0
    makespan_min = 0.0
    route_metrics = []

    for courier_number, route in enumerate(routes, start=1):
        distance_km, drive_min = route_totals(
            route,
            dist_km,
            dur_s,
        )

        total_km += distance_km
        total_drive_min += drive_min
        makespan_min = max(makespan_min, drive_min)

        route_metrics.append({
            "courier": courier_number,
            "route": route,
            "distance_km": round(distance_km, 2),
            "drive_min": round(drive_min, 2),
        })

    return {
        "algorithm": algorithm,
        "routes": routes,
        "total_km": total_km,
        "total_min": total_drive_min,
        "total_drive_min": total_drive_min,
        "makespan_min": makespan_min,
        "route_metrics": route_metrics,
        "time_ms": elapsed_ms,
    }


def compare(algorithms, obj, dist_km, dur_s, clusters):
    """Run multiple algorithms on the same clusters.

    Returns:
        (results, skipped_messages)
    """
    results = []
    skipped = []

    for name in algorithms:
        try:
            results.append(
                run_algorithm(
                    name,
                    obj,
                    dist_km,
                    dur_s,
                    clusters,
                )
            )
        except LimitExceeded as exc:
            skipped.append(str(exc))

    return results, skipped


def google_maps_url(route, points):
    """Create a Google Maps directions URL.

    Google Maps supports a limited number of waypoints in a URL.
    Long routes may need to be split into multiple links.
    """
    route_points = [
        points[index]
        for index in route
    ]

    path = "/".join(
        quote(f"{lat},{lon}")
        for lat, lon in route_points
    )

    return f"https://www.google.com/maps/dir/{path}"


# ---------------------------------------------------------------------
# Benchmark lab
# ---------------------------------------------------------------------

def _random_matrix(n_nodes, rng):
    """Create a random symmetric Euclidean distance matrix."""
    points = [
        (rng.random() * 100, rng.random() * 100)
        for _ in range(n_nodes)
    ]

    return [
        [
            math.dist(a, b)
            for b in points
        ]
        for a in points
    ]


def benchmark(stop_counts, trials=3, seed=42):
    """Benchmark algorithm runtime and optimality gap.

    The test instances are random Euclidean matrices, not road networks.

    Returns:
        List of dictionaries with n_stops, algorithm, time_ms and gap_pct.
    """
    rng = random.Random(seed)
    rows = []

    for n_stops in stop_counts:
        if n_stops < 1:
            continue

        accumulator = {
            name: {"times": [], "gaps": []}
            for name in ALGORITHMS
        }

        for _ in range(trials):
            matrix = _random_matrix(n_stops + 1, rng)
            optimum = None

            if n_stops + 1 <= ALGORITHMS[
                "Held-Karp DP (exact)"
            ][1]:
                optimum, _ = held_karp(matrix)

            for name, (fn, cap, _) in ALGORITHMS.items():
                if cap and n_stops + 1 > cap:
                    continue

                start_time = time.perf_counter()
                cost, _ = fn(matrix)

                runtime_ms = (
                    time.perf_counter() - start_time
                ) * 1000.0

                accumulator[name]["times"].append(runtime_ms)

                if optimum is not None and optimum > 0:
                    gap = max(
                        0.0,
                        (cost - optimum) / optimum * 100.0,
                    )

                    accumulator[name]["gaps"].append(gap)

        for name, values in accumulator.items():
            times = values["times"]
            gaps = values["gaps"]

            if not times:
                continue

            rows.append({
                "n_stops": n_stops,
                "algorithm": name,
                "time_ms": sum(times) / len(times),
                "gap_pct": (
                    sum(gaps) / len(gaps)
                    if gaps
                    else None
                ),
            })

    return rows
