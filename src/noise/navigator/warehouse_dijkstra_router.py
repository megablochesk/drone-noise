from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Hashable, Iterable, List, Optional

import networkx as nx
import numpy as np

from common.file_utils import load_data_from_pickle, path_exists
from noise.navigator.cost_function_generator import WeightSpec, safe_weight

Node = Hashable


def _tagged_cache_path(base_path: Optional[str], tag: Optional[str]) -> Optional[str]:
    if base_path is None or tag is None or tag == "":
        return base_path

    p = Path(base_path)
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in tag)
    return str(p.with_name(f"{p.stem}__{safe}{p.suffix}"))


def _save_pickle_atomic(obj, path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, str(p))


def _dijkstra_predecessor_and_distance(graph: nx.Graph, source: Node, weight: WeightSpec):
    fn = getattr(nx, "single_source_dijkstra_predecessor_and_distance", None)
    if fn is not None:
        return fn(graph, source, weight=weight)

    fn = getattr(nx, "dijkstra_predecessor_and_distance", None)
    if fn is not None:
        return fn(graph, source, weight=weight)

    from networkx.algorithms.shortest_paths import weighted as w

    if hasattr(w, "single_source_dijkstra_predecessor_and_distance"):
        return w.single_source_dijkstra_predecessor_and_distance(graph, source, weight=weight)

    if hasattr(w, "dijkstra_predecessor_and_distance"):
        return w.dijkstra_predecessor_and_distance(graph, source, weight=weight)

    raise AttributeError("No compatible NetworkX Dijkstra predecessor function found.")


@dataclass(frozen=True)
class _SPT:
    pred_idx: np.ndarray  # int32
    dist: np.ndarray      # float32


class WarehouseDijkstraRouter:
    """
    Warehouse-optimised router with compact caching.

    Cache format (single file for all warehouses, per weight_id tag):
      {
        "version": 1,
        "nodes": [node0, node1, ...],                 # graph node order used for indexing
        "spt": { warehouse_node: {"pred_idx": ..., "dist": ...}, ... }
      }

    We only store "from warehouse" SPT. "to warehouse" is obtained by reversing the path.
    """

    _CACHE_VERSION = 1

    def __init__(
        self,
        graph: nx.Graph,
        warehouse_nodes: Iterable[Node],
        weight: WeightSpec,
        cache_path: Optional[str] = None,
        cache_tag: Optional[str] = None,
        max_workers: Optional[int] = None,
    ):
        self._graph = graph
        self._warehouse_nodes = list(warehouse_nodes)
        self._warehouse_set = set(self._warehouse_nodes)

        if callable(weight):
            self._weight: WeightSpec = safe_weight(weight)
        else:
            self._weight = weight

        self._cache_path = _tagged_cache_path(cache_path, cache_tag)
        self._max_workers = max_workers

        self._nodes = self._stable_node_order()
        self._node_to_idx: Dict[Node, int] = {n: i for i, n in enumerate(self._nodes)}

        self._cache_spt: Dict[Node, _SPT] = {}

        self._loaded_source: Node | None = None
        self._loaded_spt: _SPT | None = None

        self._load_or_build_cache()

    def get_route(self, start_node: Node, end_node: Node) -> List[Node]:
        if start_node in self._warehouse_set:
            spt = self._get_spt(start_node)
            path = self._reconstruct_path(start_node, end_node, spt)
            if path is not None:
                return path

        if end_node in self._warehouse_set:
            spt = self._get_spt(end_node)
            path = self._reconstruct_path(end_node, start_node, spt)
            if path is not None:
                return list(reversed(path))

        return nx.shortest_path(self._graph, start_node, end_node, weight=self._weight)

    def _stable_node_order(self) -> List[Node]:
        nodes = list(self._graph.nodes)
        try:
            return sorted(nodes)  # grid tuples sort fine
        except TypeError:
            return nodes

    def _load_or_build_cache(self):
        if self._cache_path is None:
            self._cache_spt = {}
            return

        p = self._cache_path
        if path_exists(p):
            obj = load_data_from_pickle(p)
            loaded = self._try_deserialize_cache(obj)
            if loaded is not None:
                self._cache_spt = loaded
            else:
                self._cache_spt = {}

        missing = [w for w in self._warehouse_nodes if w not in self._cache_spt]
        if not missing:
            return

        if self._max_workers is not None and self._max_workers != 1:
            print("Note: forcing sequential cache build to avoid high RAM usage.")

        print(f"Computing Dijkstra SPT cache for {len(missing)} warehouse nodes (saving combined file)...")

        for i, src in enumerate(missing, 1):
            self._cache_spt[src] = self._build_spt(src)
            if i % 1 == 0 or i == len(missing):
                print(f"  [{i}/{len(missing)}]")

        _save_pickle_atomic(self._serialize_cache(self._cache_spt), p)
        print(f"Saved combined warehouse cache: {p}")

    def _try_deserialize_cache(self, obj) -> Optional[Dict[Node, _SPT]]:
        if not isinstance(obj, dict):
            return None

        if obj.get("version") != self._CACHE_VERSION:
            return None

        nodes = obj.get("nodes")
        if nodes != self._nodes:
            return None

        spt_raw = obj.get("spt")
        if not isinstance(spt_raw, dict):
            return None

        out: Dict[Node, _SPT] = {}
        for src, payload in spt_raw.items():
            if not isinstance(payload, dict):
                continue

            pred_idx = payload.get("pred_idx")
            dist = payload.get("dist")

            if pred_idx is None or dist is None:
                continue

            if not isinstance(pred_idx, np.ndarray):
                pred_idx = np.asarray(pred_idx, dtype=np.int32)
            else:
                pred_idx = pred_idx.astype(np.int32, copy=False)

            if not isinstance(dist, np.ndarray):
                dist = np.asarray(dist, dtype=np.float32)
            else:
                dist = dist.astype(np.float32, copy=False)

            if pred_idx.shape[0] != len(self._nodes):
                continue
            if dist.shape[0] != len(self._nodes):
                continue

            out[src] = _SPT(pred_idx=pred_idx, dist=dist)

        return out

    def _serialize_cache(self, spt: Dict[Node, _SPT]) -> dict:
        return {
            "version": self._CACHE_VERSION,
            "nodes": self._nodes,
            "spt": {
                src: {"pred_idx": v.pred_idx, "dist": v.dist}
                for src, v in spt.items()
            },
            "n_nodes": int(len(self._nodes)),
            "n_edges": int(self._graph.number_of_edges()),
        }

    def _get_spt(self, source: Node) -> _SPT:
        if self._loaded_source == source and self._loaded_spt is not None:
            return self._loaded_spt

        spt = self._cache_spt.get(source)
        if spt is None:
            spt = self._build_spt(source)
            self._cache_spt[source] = spt
            if self._cache_path is not None:
                _save_pickle_atomic(self._serialize_cache(self._cache_spt), self._cache_path)

        self._loaded_source = source
        self._loaded_spt = spt
        return spt

    def _build_spt(self, source: Node) -> _SPT:
        if source not in self._node_to_idx:
            raise KeyError(f"Unknown source node: {source}")

        pred, dist = _dijkstra_predecessor_and_distance(self._graph, source, self._weight)

        n = len(self._nodes)
        pred_idx = np.full(n, -1, dtype=np.int32)
        dist_arr = np.full(n, np.inf, dtype=np.float32)

        src_i = self._node_to_idx[source]
        pred_idx[src_i] = int(src_i)
        dist_arr[src_i] = 0.0

        for node, d in dist.items():
            i = self._node_to_idx.get(node)
            if i is None:
                continue

            dist_arr[i] = float(d)

            if node == source:
                continue

            preds = pred.get(node)
            if not preds:
                continue

            parent = self._pick_parent(preds)
            pi = self._node_to_idx.get(parent)
            if pi is None:
                continue

            pred_idx[i] = int(pi)

        return _SPT(pred_idx=pred_idx, dist=dist_arr)

    def _pick_parent(self, preds: List[Node]) -> Node:
        # deterministic choice to keep cache stable across runs
        return min(preds, key=lambda x: self._node_to_idx.get(x, 1_000_000_000))

    def _reconstruct_path(self, source: Node, target: Node, spt: _SPT) -> Optional[List[Node]]:
        tgt_i = self._node_to_idx.get(target)
        if tgt_i is None:
            return None

        src_i = self._node_to_idx.get(source)
        if src_i is None:
            return None

        pred = spt.pred_idx

        if int(pred[tgt_i]) == -1:
            return None

        idx_path: List[int] = []
        cur = int(tgt_i)
        n = int(pred.shape[0])

        for _ in range(n + 1):
            idx_path.append(cur)
            if cur == src_i:
                break
            nxt = int(pred[cur])
            if nxt < 0:
                return None
            cur = nxt
        else:
            return None

        idx_path.reverse()
        return [self._nodes[i] for i in idx_path]
