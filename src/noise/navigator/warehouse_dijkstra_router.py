from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Hashable, Iterable, List, Optional, Tuple

import networkx as nx

from common.file_utils import load_data_from_pickle, path_exists, save_data_as_pickle
from noise.navigator.cost_function_generator import WeightSpec, safe_weight

Node = Hashable


def _tagged_cache_path(base_path: Optional[str], tag: Optional[str]) -> Optional[str]:
    if base_path is None or tag is None or tag == "":
        return base_path

    p = Path(base_path)
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in tag)
    return str(p.with_name(f"{p.stem}__{safe}{p.suffix}"))


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

        self._cache_path = _tagged_cache_path(cache_path, cache_tag)
        self._max_workers = max_workers

        self._route_cache: Dict[Tuple[Node, Node], List[Node]] = {}
        self._warehouse_paths: Dict[Node, Dict[Node, List[Node]]] = self._load_or_compute_warehouse_paths()


    def get_route(self, start_node: Node, end_node: Node) -> List[Node]:
        key = (start_node, end_node)
        rev_key = (end_node, start_node)

        cached = self._route_cache.get(key)
        if cached is not None:
            return cached

        rev_cached = self._route_cache.get(rev_key)
        if rev_cached is not None:
            path = list(reversed(rev_cached))
            self._route_cache[key] = path
            return path

        path = self._warehouse_paths.get(start_node, {}).get(end_node)
        if path is not None:
            self._route_cache[key] = path
            return path

        path = self._warehouse_paths.get(end_node, {}).get(start_node)
        if path is not None:
            path = list(reversed(path))
            self._route_cache[key] = path
            return path

        path = nx.shortest_path(self._graph, start_node, end_node, weight=self._weight)
        self._route_cache[key] = path
        return path


    def _load_or_compute_warehouse_paths(self) -> Dict[Node, Dict[Node, List[Node]]]:
        cached = self._load_cached_paths()
        if cached is not None:
            return cached

        computed = self._compute_warehouse_paths()
        self._save_paths_to_cache(computed)
        return computed


    def _load_cached_paths(self) -> Optional[Dict[Node, Dict[Node, List[Node]]]]:
        if self._cache_path is None:
            return None
        if path_exists(self._cache_path):
            print(f"Loading precomputed warehouse paths from: {self._cache_path}")
            return load_data_from_pickle(self._cache_path)
        return None


    def _save_paths_to_cache(self, paths: Dict[Node, Dict[Node, List[Node]]]) -> None:
        if self._cache_path is None:
            return
        print(f"Saving computed warehouse paths to: {self._cache_path}")
        save_data_as_pickle(paths, self._cache_path)


    def _compute_warehouse_paths(self) -> Dict[Node, Dict[Node, List[Node]]]:
        print("Computing Dijkstra paths from all warehouse nodes (parallel)...")
        warehouse_paths: Dict[Node, Dict[Node, List[Node]]] = {}

        def compute_paths(node: Node):
            return node, nx.single_source_dijkstra_path(self._graph, node, weight=self._weight)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [executor.submit(compute_paths, node) for node in self._warehouse_nodes]
            for i, fut in enumerate(as_completed(futures), 1):
                node, paths = fut.result()
                warehouse_paths[node] = paths
                print(f"  [{i}/{len(self._warehouse_nodes)}] Done: {node}")

        return warehouse_paths
