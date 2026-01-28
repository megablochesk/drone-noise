from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Dict, Hashable, Iterable, List, Optional

import networkx as nx

from common.file_utils import load_data_from_pickle, path_exists
from noise.navigator.cost_function_generator import WeightSpec, safe_weight

Node = Hashable


def _tagged_cache_path(base_path: Optional[str], tag: Optional[str]) -> Optional[str]:
    if base_path is None or tag is None or tag == "":
        return base_path

    p = Path(base_path)
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in tag)
    return str(p.with_name(f"{p.stem}__{safe}{p.suffix}"))


def _safe_node_id(node: Node) -> str:
    s = str(node)
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)


def _save_pickle_atomic(obj, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, str(p))


class WarehouseDijkstraRouter:
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

        if callable(weight):
            self._weight: WeightSpec = safe_weight(weight)
        else:
            self._weight = weight

        self._cache_base_path = _tagged_cache_path(cache_path, cache_tag)
        self._max_workers = max_workers

        self._loaded_source: Node | None = None
        self._loaded_paths: Dict[Node, List[Node]] | None = None

        self._ensure_sources_cached()

    def get_route(self, start_node: Node, end_node: Node) -> List[Node]:
        if start_node in self._warehouse_nodes:
            paths = self._get_source_paths(start_node)
            path = paths.get(end_node)
            if path is not None:
                return path

        if end_node in self._warehouse_nodes:
            paths = self._get_source_paths(end_node)
            path = paths.get(start_node)
            if path is not None:
                return list(reversed(path))

        return nx.shortest_path(self._graph, start_node, end_node, weight=self._weight)

    def _ensure_sources_cached(self) -> None:
        if self._cache_base_path is None:
            return

        base = Path(self._cache_base_path)
        base.parent.mkdir(parents=True, exist_ok=True)

        missing = [n for n in self._warehouse_nodes if not path_exists(self._source_cache_path(n))]
        if not missing:
            return

        if self._max_workers is not None and self._max_workers != 1:
            print("Note: forcing sequential cache build to avoid high RAM usage.")
        print(f"Computing Dijkstra cache for {len(missing)} warehouse nodes (saving per-node)...")

        for i, src in enumerate(missing, 1):
            paths = nx.single_source_dijkstra_path(self._graph, src, weight=self._weight)
            out_path = self._source_cache_path(src)
            _save_pickle_atomic(paths, out_path)
            print(f"  [{i}/{len(missing)}] Saved: {out_path}")

    def _source_cache_path(self, source: Node) -> str:
        if self._cache_base_path is None:
            raise RuntimeError("Cache path is disabled.")
        base = Path(self._cache_base_path)
        sid = _safe_node_id(source)
        return str(base.with_name(f"{base.stem}__src_{sid}{base.suffix}"))

    def _get_source_paths(self, source: Node) -> Dict[Node, List[Node]]:
        if self._loaded_source == source and self._loaded_paths is not None:
            return self._loaded_paths

        if self._cache_base_path is None:
            paths = nx.single_source_dijkstra_path(self._graph, source, weight=self._weight)
            self._loaded_source = source
            self._loaded_paths = paths
            return paths

        p = self._source_cache_path(source)
        if path_exists(p):
            paths = load_data_from_pickle(p)
            self._loaded_source = source
            self._loaded_paths = paths
            return paths

        paths = nx.single_source_dijkstra_path(self._graph, source, weight=self._weight)
        _save_pickle_atomic(paths, p)
        self._loaded_source = source
        self._loaded_paths = paths
        return paths
