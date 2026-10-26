"""Shared helpers for all route algorithms. Node 0 is always the hub."""


def validate_matrix(matrix):
    n = len(matrix)
    if n == 0:
        raise ValueError("The distance matrix cannot be empty.")
    if any(len(row) != n for row in matrix):
        raise ValueError("The distance matrix must be square.")
    return n


def route_cost(matrix, route):
    """Total cost of walking `route` (list of node indices) on `matrix`."""
    return sum(matrix[a][b] for a, b in zip(route, route[1:]))