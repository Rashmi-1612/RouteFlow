import numpy as np
from .common import validate_matrix

MAX_NODES = 16  # hub + 15 stops -> 2^15 * 15 table


def held_karp(distance_matrix):
    """Exact TSP with Held-Karp dynamic programming over bitmasks.

    dp[mask][j] = cheapest cost to start at the hub, visit exactly the stops in
    `mask`, and finish at stop j.  Works for asymmetric matrices (e.g. one-way
    streets).  Time O(n^2 * 2^n), space O(n * 2^n).  Hub is index 0.
    Returns (cost, route) with route = [0, ..., 0].
    """
    n = validate_matrix(distance_matrix)
    if n == 1:
        return 0.0, [0, 0]
    if n > MAX_NODES:
        raise ValueError(f"Held-Karp supports at most {MAX_NODES} nodes (got {n}).")

    D = np.asarray(distance_matrix, dtype=float)
    m = n - 1                       # stops excluding hub
    size = 1 << m
    inner = D[1:, 1:]               # inner[k][j] = stop k+1 -> stop j+1
    dp = np.full((size, m), np.inf)
    parent = np.full((size, m), -1, dtype=np.int16)

    for j in range(m):              # base case: hub -> j directly
        dp[1 << j, j] = D[0, j + 1]

    for mask in range(1, size):
        for j in range(m):
            bit = 1 << j
            if not mask & bit:
                continue
            prev = mask ^ bit
            if prev == 0:
                continue
            cand = dp[prev] + inner[:, j]   # non-members of `prev` are +inf
            k = int(cand.argmin())
            dp[mask, j] = cand[k]
            parent[mask, j] = k

    full = size - 1
    closing = dp[full] + D[1:, 0]           # return to hub
    last = int(closing.argmin())
    best = float(closing[last])

    order, mask, j = [], full, last         # walk the parent pointers back
    while j != -1:
        order.append(j + 1)
        prev_j = int(parent[mask, j])
        mask ^= 1 << j
        j = prev_j
    order.reverse()
    return best, [0] + order + [0]


if __name__ == "__main__":
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    cost, route = held_karp(d)
    print("Minimum distance:", cost)
    print("Route:", " -> ".join(map(str, route)))