from .common import validate_matrix, route_cost
from .greedy import greedy_tsp


def improve_route(matrix, route, max_passes=50):
    """Local search: repeat 2-opt and Or-opt moves until no move helps.

    2-opt  : reverse a segment of the route (removes crossing paths).
    Or-opt : move a block of 1-3 consecutive stops elsewhere (either direction).
    Every candidate is scored with the full route cost, so it is also correct on
    asymmetric matrices.  Roughly O(n^3) per pass - fine for tens of stops.
    """
    best = list(route)
    best_cost = route_cost(matrix, best)
    n = len(best)
    if n <= 3:
        return best_cost, best

    for _ in range(max_passes):
        improved = False

        for i in range(1, n - 2):                       # --- 2-opt
            for j in range(i + 1, n - 1):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = route_cost(matrix, cand)
                if c < best_cost - 1e-9:
                    best, best_cost, improved = cand, c, True

        for seg in (1, 2, 3):                           # --- Or-opt
            for i in range(1, n - seg):
                block = best[i:i + seg]
                rest = best[:i] + best[i + seg:]
                for k in range(1, len(rest)):
                    for piece in (block, block[::-1]):
                        cand = rest[:k] + piece + rest[k:]
                        c = route_cost(matrix, cand)
                        if c < best_cost - 1e-9:
                            best, best_cost, improved = cand, c, True
                            break
        if not improved:
            break
    return float(best_cost), best


def local_search_tsp(distance_matrix):
    """Nearest-neighbour start, then 2-opt + Or-opt. Hub is index 0."""
    validate_matrix(distance_matrix)
    _, start = greedy_tsp(distance_matrix)
    return improve_route(distance_matrix, start)


if __name__ == "__main__":
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    cost, route = local_search_tsp(d)
    print("Local search distance:", cost)
    print("Route:", " -> ".join(map(str, route)))