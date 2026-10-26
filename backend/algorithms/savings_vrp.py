
"""Clarke-Wright savings algorithm for capacitated vehicle routing."""

def clarke_wright(matrix, demands, capacity, n_couriers=None):
    """Create capacity-safe courier routes using Clarke-Wright savings.

    Args:
        matrix: Square cost matrix. Index 0 is the courier hub.
        demands: Demand at each location. demands[0] is ignored.
        capacity: Maximum demand carried by one courier.
        n_couriers: Requested maximum number of couriers, or None.

    Returns:
        List of routes, each beginning and ending at hub index 0.

    Raises:
        ValueError: If an individual stop exceeds capacity, or if the
                    requested courier count cannot satisfy capacity.
    """
    n = len(matrix)

    if n == 0:
        return []

    if any(len(row) != n for row in matrix):
        raise ValueError("The cost matrix must be square.")

    if len(demands) != n:
        raise ValueError("Demands must match the number of locations.")

    if capacity < 1:
        raise ValueError("Courier capacity must be at least 1.")

    if n_couriers is not None and n_couriers < 1:
        raise ValueError("Courier count must be at least 1.")

    if n == 1:
        return []

    for i in range(1, n):
        if demands[i] > capacity:
            raise ValueError(
                f"Stop {i} requires {demands[i]} parcels, "
                f"but courier capacity is {capacity}."
            )

    total_demand = sum(demands[1:])

    if n_couriers is not None and total_demand > n_couriers * capacity:
        raise ValueError(
            f"Total load {total_demand} exceeds fleet capacity "
            f"{n_couriers} x {capacity}."
        )

    # One initial route per delivery stop.
    routes = {i: [i] for i in range(1, n)}
    loads = {i: demands[i] for i in range(1, n)}
    where = {i: i for i in range(1, n)}

    # Savings: distance from hub to i and j minus distance i to j.
    savings = sorted(
        (
            (
                matrix[0][i] + matrix[0][j] - matrix[i][j],
                i,
                j,
            )
            for i in range(1, n)
            for j in range(i + 1, n)
        ),
        reverse=True,
    )

    for saving, i, j in savings:
        if saving <= 0:
            break

        ri = where[i]
        rj = where[j]

        if ri == rj:
            continue

        if loads[ri] + loads[rj] > capacity:
            continue

        route_i = routes[ri]
        route_j = routes[rj]

        # Merge only when i and j are route endpoints.
        if route_i[-1] == i and route_j[0] == j:
            merged = route_i + route_j
        elif route_i[0] == i and route_j[-1] == j:
            merged = route_j + route_i
        elif route_i[0] == i and route_j[0] == j:
            merged = route_i[::-1] + route_j
        elif route_i[-1] == i and route_j[-1] == j:
            merged = route_i + route_j[::-1]
        else:
            continue

        routes[ri] = merged
        loads[ri] += loads[rj]

        del routes[rj]
        del loads[rj]

        for customer in merged:
            where[customer] = ri

    result = [
        [0] + route + [0]
        for route in sorted(routes.values(), key=lambda r: r[0])
    ]

    # Do not silently violate capacity or claim to use more couriers
    # than the user requested.
    if n_couriers is not None and len(result) > n_couriers:
        raise ValueError(
            f"Capacity constraints require {len(result)} courier routes, "
            f"but only {n_couriers} couriers were requested. "
            "Increase capacity or the number of couriers."
        )

    return result
