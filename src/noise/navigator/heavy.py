from concurrent.futures import ThreadPoolExecutor, as_completed

import networkx as nx
from scipy.spatial import cKDTree

from common.coordinate import Coordinate
from common.file_utils import save_data_as_pickle, load_data_from_pickle, path_exists
from common.model_configs import model_config
from noise.navigator.base import BaseNavigator

LONDON_WAREHOUSES = list(model_config.warehouses.bng_coordinates.items())
WAREHOUSE_PATHS_CACHE = model_config.paths.warehouse_paths_cache()


class HeavyNavigator(BaseNavigator):
    def __init__(self):
        super().__init__()

        self.nodes = list(self.graph.nodes)
        self.tree = self._build_kdtree()

        self._warehouse_node_cache = {
            coord: self._query_kdtree(coord)
            for _, coord in LONDON_WAREHOUSES
        }

        self._route_cache = {}
        self._warehouse_paths = self._load_or_compute_warehouse_paths()

    def find_nearest_node(self, point: Coordinate) -> tuple:
        cached = self._warehouse_node_cache.get(point)
        if cached:
            return cached
        return self._query_kdtree(point)


    def get_optimal_route(self, start: Coordinate, end: Coordinate):
        start_node = self.find_nearest_node(start)
        end_node = self.find_nearest_node(end)

        return self._get_or_compute_route(start_node, end_node)

    def _build_kdtree(self):
        return cKDTree([
            (self.graph.nodes[node]["easting"], self.graph.nodes[node]["northing"])
            for node in self.graph
        ])

    def _query_kdtree(self, point: Coordinate) -> tuple:
        _, index = self.tree.query((point.easting, point.northing))
        return self.nodes[index]

    @staticmethod
    def _load_cached_paths():
        if path_exists(WAREHOUSE_PATHS_CACHE):
            print(f"Loading precomputed warehouse paths from: {WAREHOUSE_PATHS_CACHE}")
            return load_data_from_pickle(WAREHOUSE_PATHS_CACHE)
        return None

    def _compute_warehouse_paths(self):
        print("Computing Dijkstra paths from all warehouse nodes (parallel)...")
        nodes = list(self._warehouse_node_cache.values())
        warehouse_paths = {}

        def compute_paths(node):
            return node, nx.single_source_dijkstra_path(self.graph, node, weight="weight")

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(compute_paths, node): node for node in nodes}
            for i, future in enumerate(as_completed(futures), 1):
                node, paths = future.result()
                warehouse_paths[node] = paths
                print(f"  [{i}/{len(nodes)}] Done: {node}")

        return warehouse_paths

    @staticmethod
    def _save_paths_to_cache(paths):
        print(f"Saving computed warehouse paths to: {WAREHOUSE_PATHS_CACHE}")
        save_data_as_pickle(paths, WAREHOUSE_PATHS_CACHE)

    def _load_or_compute_warehouse_paths(self):
        cached = self._load_cached_paths()
        if cached is not None:
            return cached

        computed = self._compute_warehouse_paths()
        self._save_paths_to_cache(computed)

        print("Warehouse paths loaded!")

        return computed

    def _get_or_compute_route(self, start_node, end_node):
        key = (start_node, end_node)
        rev_key = (end_node, start_node)

        if key in self._route_cache:
            return self._route_cache[key]
        if rev_key in self._route_cache:
            return self._cache_and_return(key, list(reversed(self._route_cache[rev_key])))

        path = self._get_from_precomputed_paths(start_node, end_node)
        if path:
            return self._cache_and_return(key, path)

        path = self._get_from_precomputed_paths(end_node, start_node)
        if path:
            return self._cache_and_return(key, list(reversed(path)))

        return self._compute_and_cache_path(start_node, end_node)

    def _get_from_precomputed_paths(self, source_node, target_node):
        return self._warehouse_paths.get(source_node, {}).get(target_node)

    def _compute_and_cache_path(self, start_node, end_node):
        path = nx.shortest_path(self.graph, start_node, end_node, weight="weight")
        return self._cache_and_return((start_node, end_node), path)

    def _cache_and_return(self, key, path):
        self._route_cache[key] = path
        return path
