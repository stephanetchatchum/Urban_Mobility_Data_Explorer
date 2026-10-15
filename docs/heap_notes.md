# Heap section

The `MinHeap` code in `backend/algorithms/custom_algorithm.py`, is used by the `GET /api/zones/slowest` in `backend/app.py`.

## 1. Problem

Find the **K slowest pickup zones** out of roughly 260 taxi zones, where "slowest" means the lowest average `speed_mph` over all the trips picked up in that zone.

This matters to the dashboard because the average speed tells us if there are congestions. A ranked list of the slowest zones tells a city planner where traffic is worst without reading a map of 260 shapes. TRhe endpoint take `k` and `min_trips`. The `min_trips` filter stops a zone with only a handful of trips from topping the list because of noise.

## 2. Approach

we use a **min-heap** of `(average speed, zone) ` pairs. 

1. MySQL aggregates the 7.6 milliton trips into one row per zone: `AVG(speed_mph)` gounded by pickup zone, keeping only zones with at least `min_trips` trips. This leaves about 260 rows.
2. Push every `(avg_speed, zone)` pair into the heap.
3. Pop K times. Each pop return the next zone on the list, slowest first.

The reason why **the smallest comes out first** is because a min-heap keeps one rule all the time which is that every parent is less than or equal to both of its children. If every parent is at most its childre, then going down any path from the root only ever meets larger values. SO nothing in the tree can be smaller than the root, and the root is the minimum. `pop` takes ithe root, then repairs the tree so the rule holds agian and the new root is the next smallest. Popping K times gives the K smallest averages in increasing order, which is exaclty "slowest first".

the heap only compare the speed `(item[0])`. If two zones have exactly the same avergae, their order is not defined.

## 3. Pseudo-code

The heap is stored in a flat list. For the item at indez `i`: its parent is at `(i -1) // 2`, its left child at `2i + 1`, its right child at `2i+2`.

*push(item)*

1. Put the new item at the end of the list. 
2. Let `i` bet the index of the new item
3. While `i` is not the root:
    1. Find the parent of `i`
    2. If the item's speed is smaller than the parent's speed, swap them and set `i` to the parent's index
    3. Else stop.

*pop()*

1. If the heap is empty, return nothing.
2. remember the root.
3. remove the last item from the list
4. If the list is now empty, return the remembered rood.
5. Put the last item at the root position then let `i = 0`.
6. Repeat:
    1. If ``i has no left child, stop.
    2. Pick the smallest of its children 
    3. If that child's speed is smaller than the speed at `i`, swap them and set `i` to the child's index.
    4. else stop
7. Return the remembered root.

## 4. Complexity

| Operations | Time  | Reason |
|---|---|---|
| `push` | O(log n) | The item moves up at most oce per level. A heap with n items is a complete tree of height floor(log2 n), so the swap path is at most that long. |
| `pop` | O(log n) | The moved item goes down at most one level per step, again in at most the height of the tree. Each step does a constant amount of work. |
| Build with n pushes | O(n log n) | n pushes, each O(log n). |
| Extract K items | O(K log n) | K pops, each O(log n). |
| Space | O(n) | One list holding the n pairs. |

SO the total complexity for the em=ndpoints is O(N log n + K log n). Since K is at most 50 and n is about 260, the build step domminates.

## 5. Why not just sort everything?

Sorting all n zones is O(n log n) as well, and the standard sort is fast in practice. So the reason is because the differnece is small. WIth about 260 zones either approach finishes in well under a millisecond, and the heavy work is done by MySQL in both cases. SQL could even do `ORDER BY avg_speed LIMIT k` on its own.

The heap is the better choice when n is large and K is small. if we only the K smallest, we can keep a heap of size K instead of size n, which cost O(n log K) and O(K) space, and we never order the items we throw away. A full sort as to order all n. At n = 260 and K = 10 that saving is invisible. At millions of items it is not.

For this project, the heap is there to show thae algorithm working on a real ranking, not because the dataset needs.