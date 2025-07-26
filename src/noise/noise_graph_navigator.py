import json

import networkx as nx
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape

from common.configuration import NAVIGATION_GRID_CELL_SIZE, NAVIGATION_BASE_NOISE_PATH, NAVIGATION_GRAPH_PATH
from common.coordinate import Coordinate

from common.file_utils import load_graph, save_graph, path_exists

_WGS84_TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)


class NoiseGraphNavigator:
    def __init__(self, base_noise_path=NAVIGATION_BASE_NOISE_PATH, graph_path=NAVIGATION_GRAPH_PATH):
        self.base_noise_path = base_noise_path
        self.graph_path = graph_path

        self.graph = self._load_or_build_graph()

        self.tree = cKDTree([self.graph.nodes[node]["pos"] for node in self.graph])
        self.nodes = list(self.graph.nodes)

    @staticmethod
    def _get_cells_noise_levels(path):
        features = json.load(open(path)).get("features", [])
        return [
            (
                feature["properties"].get("row", 0),
                feature["properties"].get("col", 0),
                feature["properties"].get("noise_level", 0.0),
                shape(feature["geometry"]).centroid.coords[0],
            )
            for feature in features
        ]

    def _build_graph(self, path=None):
        records = self._get_cells_noise_levels(path or self.base_noise_path)
        graph = nx.Graph()
        self._add_nodes_from_records(graph, records)
        self._connect_adjacent_cells(graph)
        return graph

    @staticmethod
    def _add_nodes_from_records(graph: nx.Graph, records):
        for row, column, noise, (longitude, latitude) in records:
            easting, northing = _WGS84_TO_BNG.transform(longitude, latitude)
            graph.add_node((row, column), noise=noise, pos=(easting, northing))

    @staticmethod
    def _connect_adjacent_cells(graph: nx.Graph):
        neighbor_shifts = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for node_row, node_column in list(graph.nodes):
            node = (node_row, node_column)
            for delta_row, delta_column in neighbor_shifts:
                neighbor_node = (node_row + delta_row, node_column + delta_column)
                if neighbor_node in graph and not graph.has_edge(node, neighbor_node):
                    noise_1 = graph.nodes[node]["noise"]
                    noise_2 = graph.nodes[neighbor_node]["noise"]
                    average_noise_between_cells = (noise_1 + noise_2) / 2
                    weight = NAVIGATION_GRID_CELL_SIZE / average_noise_between_cells
                    graph.add_edge(node, neighbor_node, weight=weight)

    def _load_or_build_graph(self):
        if path_exists(self.graph_path):
            return load_graph(self.graph_path)

        graph = self._build_graph()
        save_graph(graph, self.graph_path)

        return graph

    def find_nearest_node(self, point: Coordinate) -> tuple:
        _, index = self.tree.query((point.easting, point.northing))
        return self.nodes[index]

    def get_optimal_route(self, start: Coordinate, end: Coordinate):
        start_node = self.find_nearest_node(start)
        end_node = self.find_nearest_node(end)

        return nx.shortest_path(self.graph, start_node, end_node, weight="weight")

    def nodes_to_coordinates(self, nodes):
        return [
            Coordinate(
                northing=self.graph.nodes[node]["pos"][1],
                easting=self.graph.nodes[node]["pos"][0],
            )
            for node in nodes
        ]
