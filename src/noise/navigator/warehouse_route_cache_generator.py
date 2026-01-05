from __future__ import annotations

from typing import Callable, Optional

from scipy.spatial import cKDTree

from common.coordinate import Coordinate
from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS
from noise.navigator.cost_function_generator import WeightSpec, make_noise_distance_weight, materialize_weight_attr
from noise.navigator.navigator_base import BaseNavigator
from noise.navigator.warehouse_dijkstra_router import WarehouseDijkstraRouter

LONDON_WAREHOUSES = list(model_config.warehouses.bng_coordinates.items())
WeightBuilder = Callable[[object], WeightSpec]


class WarehouseRouteCacheGenerator(BaseNavigator):
    def __init__(
        self,
        weight: WeightSpec | None = None,
        weight_id: str | None = "noise_dist",
        cache_path: Optional[str] = None,
        max_workers: int | None = None,
        ensure_weight_attr: bool = True,
        weight_builder: WeightBuilder | None = None,
    ):
        super().__init__()

        if cache_path is None:
            cache_path = PATH_CONFIGS.warehouse_paths_cache()

        if weight_builder is not None:
            weight = weight_builder(self.graph)

        if weight is None:
            if ensure_weight_attr and not self._graph_has_edge_attr("weight"):
                materialize_weight_attr(self.graph, make_noise_distance_weight(), attr="weight")
            weight = "weight"

        if callable(weight) and not weight_id:
            cache_path = None

        self.nodes = list(self.graph.nodes)
        self.tree = self._build_kdtree()

        self._warehouse_node_cache = {
            warehouse_location: self._query_kdtree(warehouse_location)
            for _, warehouse_location in LONDON_WAREHOUSES
        }

        self._router = WarehouseDijkstraRouter(
            graph=self.graph,
            warehouse_nodes=self._warehouse_node_cache.values(),
            weight=weight,
            cache_path=cache_path,
            cache_tag=weight_id,
            max_workers=max_workers,
        )

    def find_nearest_node(self, point: Coordinate) -> tuple:
        cached = self._warehouse_node_cache.get(point)
        if cached is not None:
            return cached
        return self._query_kdtree(point)

    def get_optimal_route(self, start: Coordinate, end: Coordinate):
        start_node = self.find_nearest_node(start)
        end_node = self.find_nearest_node(end)
        return self._router.get_route(start_node, end_node)

    def _build_kdtree(self):
        return cKDTree([
            (self.graph.nodes[node]["easting"], self.graph.nodes[node]["northing"])
            for node in self.graph
        ])

    def _query_kdtree(self, point: Coordinate) -> tuple:
        _, index = self.tree.query((point.easting, point.northing))
        return self.nodes[index]

    def _graph_has_edge_attr(self, attr: str) -> bool:
        for _, _, data in self.graph.edges(data=True):
            if attr in data and data[attr] is not None:
                return True
        return False
