import json
import math
from functools import lru_cache

import networkx as nx
from pyproj import Transformer
from shapely.geometry import shape

from common.file_utils import load_graph, save_graph, path_exists
from common.model_configs import model_config
from common.path_configs import NAVIGATION_BASE_NOISE_PATH, NAVIGATION_GRAPH_PATH

NAVIGATION_GRID_CELL_SIZE = model_config.grid.nav_cell_m

_WGS84_TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)

NEIGHBOR_SHIFTS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]


@lru_cache(maxsize=1)
def load_or_build_graph(base_noise_path=NAVIGATION_BASE_NOISE_PATH, noise_graph_path=NAVIGATION_GRAPH_PATH):
    if path_exists(noise_graph_path, suffixes=(".pkl", ".graphml")):
        return load_graph(noise_graph_path)

    graph = _build_graph(base_noise_path)
    save_graph(graph, noise_graph_path)

    return graph


def _build_graph(base_noise_path: str) -> nx.Graph:
    records = _get_cells_noise_levels(base_noise_path)
    graph = nx.Graph()

    _add_nodes_from_records(graph, records)
    _connect_adjacent_cells(graph)

    return graph


def _get_cells_noise_levels(path: str):
    with open(path) as f:
        features = json.load(f).get("features", [])

    return [
        (
            feature["properties"].get("row", 0),
            feature["properties"].get("col", 0),
            feature["properties"].get("noise_level", 0.0),
            shape(feature["geometry"]).centroid.coords[0],
        )
        for feature in features
    ]


def _add_nodes_from_records(graph: nx.Graph, records):
    for row, column, noise, (longitude, latitude) in records:
        easting, northing = _WGS84_TO_BNG.transform(longitude, latitude)
        graph.add_node(
            (row, column),
            noise=noise,
            easting=easting,
            northing=northing
        )


def _connect_adjacent_cells(graph: nx.Graph):
    diagonal_factor = math.sqrt(2.0)

    for node_row, node_column in graph.nodes:
        node = (node_row, node_column)

        for row_shift, column_shift in NEIGHBOR_SHIFTS:
            neighbor_node = (node_row + row_shift, node_column + column_shift)
            if neighbor_node not in graph or graph.has_edge(node, neighbor_node):
                continue

            node_noise = graph.nodes[node]["noise"]
            neighbor_node_noise = graph.nodes[neighbor_node]["noise"]
            average_noise = (node_noise + neighbor_node_noise) / 2

            distance = NAVIGATION_GRID_CELL_SIZE * (diagonal_factor if is_diagonal_shift(column_shift, row_shift) else 1)

            graph.add_edge(
                node,
                neighbor_node,
                distance=distance,
                noise=average_noise
            )


def is_diagonal_shift(column_shift, row_shift):
    return row_shift != 0 and column_shift != 0
