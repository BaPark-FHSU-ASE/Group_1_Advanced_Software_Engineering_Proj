"""
Generic min-cost flow.

Every arc has nonnegative cost (fij, hij, ck are all >= 0),
so a Bellman-Ford / SPFA shortest-path search is sufficient to find each
augmenting path; we don't need Dijkstra-with-potentials (Johnson's trick)
at the scale this project targets. 

The underlying constraint matrix is totally unimodular, so integer
capacities/supplies always yield an integral optimal flow - no rounding
is needed here.

Requirements traced: REQ-18. Once the set of open routes is fixed, this is
what solves the remaining transportation problem exactly, and the
minimum-cost plan REQ-18 asks for is built on top of it.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class _Edge:
    to: int
    cap: int
    cost: float
    flow: int = 0

    def residual_cap(self) -> int:
        return self.cap - self.flow


class MinCostFlow:
    """Directed graph with integer capacities and float costs per unit of
    flow. Edges are stored in pairs (forward, backward) so residual
    capacity/cost falls out of the pair automatically."""

    def __init__(self, n: int):
        self.n = n
        self.graph: list[list[int]] = [[] for _ in range(n)]  # node -> edge indices
        self.edges: list[_Edge] = []

    def add_edge(self, u: int, v: int, cap: int, cost: float) -> None:
        self.graph[u].append(len(self.edges))
        self.edges.append(_Edge(v, cap, cost))
        self.graph[v].append(len(self.edges))
        self.edges.append(_Edge(u, 0, -cost))

    def _shortest_path(self, s: int, t: int) -> tuple[list[float], list[int]] | None:
        """Bellman-Ford over the residual graph. Returns (dist, prev_edge)
        or None if t is unreachable from s."""
        dist = [float("inf")] * self.n
        prev_edge = [-1] * self.n
        in_queue = [False] * self.n
        dist[s] = 0.0
        q = deque([s])
        in_queue[s] = True
        while q:
            u = q.popleft()
            in_queue[u] = False
            for ei in self.graph[u]:
                e = self.edges[ei]
                if e.residual_cap() <= 0:
                    continue
                nd = dist[u] + e.cost
                if nd < dist[e.to] - 1e-9:
                    dist[e.to] = nd
                    prev_edge[e.to] = ei
                    if not in_queue[e.to]:
                        q.append(e.to)
                        in_queue[e.to] = True
        if dist[t] == float("inf"):
            return None
        return dist, prev_edge

    def min_cost_flow(self, s: int, t: int, max_flow: int) -> tuple[int, float]:
        """Push up to max_flow units from s to t via successive shortest
        augmenting paths. Returns (flow_pushed, total_cost). Raises if
        max_flow cannot be fully pushed (network is infeasible for the
        required demand)."""
        flow = 0
        cost = 0.0
        while flow < max_flow:
            found = self._shortest_path(s, t)
            if found is None:
                raise ValueError(
                    f"infeasible: only {flow} of {max_flow} units routable "
                    f"(source supply cannot cover sink demand on the opened routes)"
                )
            dist, prev_edge = found
            bottleneck = max_flow - flow
            v = t
            while v != s:
                ei = prev_edge[v]
                e = self.edges[ei]
                bottleneck = min(bottleneck, e.residual_cap())
                v = self.edges[ei ^ 1].to
            v = t
            while v != s:
                ei = prev_edge[v]
                self.edges[ei].flow += bottleneck
                self.edges[ei ^ 1].flow -= bottleneck
                v = self.edges[ei ^ 1].to
            flow += bottleneck
            cost += bottleneck * dist[t]
        return flow, cost

    def flow_on(self, u: int, v: int) -> int:
        """Sum of flow on all u->v edges (there's normally just one, but
        this stays correct if callers add parallel edges)."""
        total = 0
        for ei in self.graph[u]:
            e = self.edges[ei]
            if e.to == v and e.cap > 0:
                total += e.flow
        return total
