from __future__ import annotations

from typing import Callable, Hashable, Optional, Sequence, Union

import networkx as nx
import numpy as np

from common.model_configs import model_config

NAVIGATION_GRID_CELL_SIZE = model_config.grid.nav_cell_m

Node = Hashable
WeightFn = Callable[[Node, Node, dict], float]
WeightSpec = Union[str, WeightFn]


def clamp01(x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x


def nonneg(x: float) -> float:
    return x if x >= 0.0 else 0.0


def safe_weight(weight: WeightFn) -> WeightFn:
    def w(u: Node, v: Node, data: dict) -> float:
        val = weight(u, v, data)
        if val is None:
            return 0.0
        if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
            return 0.0
        return nonneg(val)

    return w


def _edge_get_first(data: dict, keys: Sequence[str], default: Optional[float] = None) -> Optional[float]:
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return default


def make_noise_distance_weight(
    dist_keys: Sequence[str] = ("distance",),
    noise_keys: Sequence[str] = ("noise",),
) -> WeightFn:
    def w(_u: Node, _v: Node, data: dict) -> float:
        dist = _edge_get_first(data, dist_keys, 0.0)
        noise = _edge_get_first(data, noise_keys, 0.0)

        if noise is None or noise <= 0.0:
            return dist if dist is not None else 0.0

        return (dist if dist is not None else 0.0) / noise

    return safe_weight(w)


def compute_noise_stats(
    graph: nx.Graph,
    noise_keys_nodes: Sequence[str] = ("noise",)
) -> tuple[float, float]:
    vals: list[float] = []

    for _, attrs in graph.nodes(data=True):
        for k in noise_keys_nodes:
            v = attrs.get(k)
            if v is not None:
                vals.append(v)
                break


    if not vals:
        return 0.0, 1.0

    arr = np.asarray(vals, dtype=float)
    nmin = float(np.nanmin(arr))
    nmax = float(np.nanmax(arr))
    rng = nmax - nmin
    if not np.isfinite(rng) or rng <= 0.0:
        rng = 1.0
    return nmin, rng


def make_mixed_distance_noise_weight(
    graph: nx.Graph,
    alpha: float,
    dist_keys: Sequence[str] = ("distance",),
    noise_keys: Sequence[str] = ("noise",),
    higher_noise_is_better: bool = True,
) -> WeightFn:
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha must be in [0, 1]")

    nmin, nrng = compute_noise_stats(graph)

    def w(_u: Node, _v: Node, data: dict) -> float:
        edge_length = _edge_get_first(data, dist_keys, 0.0)
        noise = _edge_get_first(data, noise_keys, 0.0)

        dist_cost = edge_length / NAVIGATION_GRID_CELL_SIZE

        norm = clamp01((noise - nmin) / nrng)
        noise_cost = (1.0 - norm) if higher_noise_is_better else norm

        return (1.0 - alpha) * dist_cost + alpha * noise_cost

    return safe_weight(w)


def materialize_weight_attr(
    graph: nx.Graph,
    weight: WeightFn,
    attr: str = "weight",
) -> None:
    w = safe_weight(weight)
    for u, v, data in graph.edges(data=True):
        data[attr] = w(u, v, data)
