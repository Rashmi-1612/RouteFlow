import math
import random

import pytest

from algorithms import (brute_force_tsp, clarke_wright, greedy_tsp, held_karp,
                        local_search_tsp)
from algorithms.common import route_cost


def random_matrix(n, seed, asymmetric=False):
    rng = random.Random(seed)
    pts = [(rng.random(), rng.random()) for _ in range(n)]
    m = [[math.dist(a, b) for b in pts] for a in pts]
    if asymmetric:
        m = [[0 if i == j else x * rng.uniform(0.9, 1.3) for j, x in enumerate(r)]
             for i, r in enumerate(m)]
    return m


@pytest.mark.parametrize("n", [2, 3, 5, 7, 9])
@pytest.mark.parametrize("asym", [False, True])
def test_held_karp_matches_brute_force(n, asym):
    m = random_matrix(n, seed=n, asymmetric=asym)
    hk, bf = held_karp(m), brute_force_tsp(m)
    assert hk[0] == pytest.approx(bf[0])
    assert route_cost(m, hk[1]) == pytest.approx(hk[0])
    assert hk[1][0] == hk[1][-1] == 0 and sorted(hk[1][:-1]) == list(range(n))


def test_readme_example():
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    assert held_karp(d)[0] == 80 and greedy_tsp(d)[0] == 80


@pytest.mark.parametrize("n", [6, 10, 14])
def test_heuristic_ordering(n):
    m = random_matrix(n, seed=100 + n)
    opt, g, ls = held_karp(m)[0], greedy_tsp(m)[0], local_search_tsp(m)[0]
    assert opt - 1e-9 <= ls <= g + 1e-9


def test_single_node_and_validation():
    assert held_karp([[0]]) == (0.0, [0, 0])
    with pytest.raises(ValueError):
        held_karp([])
    with pytest.raises(ValueError):
        greedy_tsp([[0, 1], [1]])
    with pytest.raises(ValueError):
        brute_force_tsp(random_matrix(12, 1))


def test_clarke_wright_respects_capacity_and_covers_all():
    m = random_matrix(13, seed=7)
    demands = [0] + [random.Random(3).randint(1, 4) for _ in range(12)]
    routes = clarke_wright(m, demands, capacity=10)
    served = sorted(s for r in routes for s in r[1:-1])
    assert served == list(range(1, 13))
    assert all(sum(demands[s] for s in r[1:-1]) <= 10 for r in routes)
    assert all(r[0] == r[-1] == 0 for r in routes)


def test_clarke_wright_beats_one_trip_per_stop():
    m = random_matrix(10, seed=2)
    routes = clarke_wright(m, [0] + [1] * 9, capacity=9)
    assert sum(route_cost(m, r) for r in routes) < sum(m[0][i] + m[i][0] for i in range(1, 10))


def test_clarke_wright_rejects_oversized_stop():
    with pytest.raises(ValueError):
        clarke_wright(random_matrix(4, 1), [0, 99, 1, 1], capacity=10)