"""Checks the hand-written min-heap and k_smallest against Python's own sorting."""
import random

from backend.algorithms.custom_algorithm import MinHeap, k_smallest

def test_heap_pops_in_ascending_order():
    rng = random.Random(1)
    values = [rng.randint(-50, 50) for _ in range(500)]
    heap = MinHeap()
    for v in values:
        heap.push((v, "zone"))
    popped = [heap.pop()[0] for _ in range(len(values))]
    assert popped == sorted(values)


def test_pop_on_empty_heap_returns_none():
    assert MinHeap().pop() is None


def test_k_smallest_matches_sorting():
    rng = random.Random(2)
    items = [{"id": i, "v": round(rng.uniform(0, 30), 1)} for i in range(300)]
    result = k_smallest(items, 12, lambda r: r["v"])
    assert [r["v"] for r in result] == sorted(r["v"] for r in items)[:12]


def test_k_smallest_largest_by_negating_the_key():
    items = [{"v": 3}, {"v": 9}, {"v": 5}]
    assert [r["v"] for r in k_smallest(items, 2, lambda r: -r["v"])] == [9, 5]


def test_k_smallest_edge_cases():
    assert k_smallest([], 5, lambda r: r) == []
    assert k_smallest([3, 1, 2], 0, lambda r: r) == []
    assert k_smallest([3, 1, 2], 10, lambda r: r) == [1, 2, 3]            # k larger than n
    assert k_smallest([None, 4, None, 2], 2, lambda r: r) == [2, 4]       # None keys are skipped

 