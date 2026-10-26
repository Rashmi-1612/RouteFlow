from .common import validate_matrix


def greedy_tsp(distance_matrix):
    """Nearest-neighbour heuristic. Hub is index 0. O(n^2), not optimal."""
    n = validate_matrix(distance_matrix)
    if n == 1:
        return 0.0, [0, 0]
    unvisited = set(range(1, n))
    route, current, total = [0], 0, 0.0
    while unvisited:
        nxt = min(unvisited, key=lambda k: distance_matrix[current][k])
        total += distance_matrix[current][nxt]
        route.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    total += distance_matrix[current][0]
    route.append(0)
    return float(total), route


if __name__ == "__main__":
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    cost, route = greedy_tsp(d)
    print("Greedy distance:", cost)
    print("Greedy route:", " -> ".join(map(str, route)))