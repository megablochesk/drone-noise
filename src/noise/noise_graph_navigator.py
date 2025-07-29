import networkx as nx
from scipy.spatial import cKDTree

from noise.noise_graph_builder import load_or_build_graph
from common.coordinate import Coordinate
from common.configuration import LONDON_WAREHOUSES


class NoiseGraphNavigator:
    def __init__(self):
        self.graph = load_or_build_graph()
        self.nodes = list(self.graph.nodes)
        self.tree = self.build_kdtree()

        self._warehouse_node_cache = {
            coord: self._query_kdtree(coord)
            for _, coord in LONDON_WAREHOUSES
        }

    def build_kdtree(self):
        return cKDTree([
            (self.graph.nodes[node]["easting"], self.graph.nodes[node]["northing"])
            for node in self.graph
        ])

    def _query_kdtree(self, point: Coordinate) -> tuple:
        _, index = self.tree.query((point.easting, point.northing))
        return self.nodes[index]

    def find_nearest_node(self, point: Coordinate) -> tuple:
        cached = self._warehouse_node_cache.get(point)
        if cached:
            return cached
        return self._query_kdtree(point)

    def get_optimal_route(self, start: Coordinate, end: Coordinate):
        start_node = self.find_nearest_node(start)
        end_node = self.find_nearest_node(end)

        return nx.shortest_path(
            self.graph,
            start_node,
            end_node,
            weight="weight"
        )

    def nodes_to_coordinates(self, nodes):
        return [
            Coordinate(
                northing=self.graph.nodes[node]["northing"],
                easting=self.graph.nodes[node]["easting"],
            )
            for node in nodes
        ]
