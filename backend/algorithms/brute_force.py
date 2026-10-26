from itertools import permutations
from .common import validate_matrix

MAX_NODES = 11  # 10! = 3.6M permutations is already slow in pure Python


def brute_force_tsp(distance_matrix):
    """Exact TSP by checking every ordering. Hub is index 0. O(n!)."""
    n = validate_matrix(distance_matrix)
    if n == 1:
        return 0.0, [0, 0]
    if n > MAX_NODES:
        raise ValueError(f"Brute force supports at most {MAX_NODES} nodes (got {n}).")
    best_cost, best_route = float("inf"), []
    for order in permutations(range(1, n)):
        route = (0,) + order + (0,)
        cost = sum(distance_matrix[route[i]][route[i + 1]] for i in range(n))
        if cost < best_cost:
            best_cost, best_route = cost, list(route)
    return float(best_cost), best_route


if __name__ == "__main__":
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    cost, route = brute_force_tsp(d)
    print("Brute Force distance:", cost)
    print("Brute Force route:", " -> ".join(map(str, route)))