import networkx as nx
from scipy.spatial import cKDTree

from noise.noise_graph_builder import load_or_build_graph
from common.coordinate import Coordinate


class NoiseGraphNavigator:
    def __init__(self):
        self.graph = load_or_build_graph()

        self.tree = self.build_kdtree()
        self.nodes = list(self.graph.nodes)

    def build_kdtree(self):
        return cKDTree(
            [(self.graph.nodes[node]["easting"], self.graph.nodes[node]["northing"]) for node in self.graph]
        )

    def find_nearest_node(self, point: Coordinate) -> tuple:
        _, index = self.tree.query((point.easting, point.northing))
        return self.nodes[index]

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
