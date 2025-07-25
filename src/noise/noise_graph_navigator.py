import json

import networkx as nx
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape

from common.configuration import NAVIGATION_GRID_CELL_SIZE, NAVIGATION_BASE_NOISE_PATH, NAVIGATION_GRAPH_PATH
from common.coordinate import Coordinate
from common.file_utils import load_graph, save_graph, path_exists

_WGS84_TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)

def get_df_from_noise_matrix_geojson(path):
    feats = json.load(open(path)).get("features", [])
    rows = [
        (
            f["properties"].get("row", 0),
            f["properties"].get("col", 0),
            f["properties"].get("noise_level", 0.0),
            shape(f["geometry"]).centroid.coords[0],
        )
        for f in feats
    ]
    return rows

def build_graph(path=NAVIGATION_BASE_NOISE_PATH):
    records = get_df_from_noise_matrix_geojson(path)
    graph = nx.Graph()

    for r, c, noise, (lon, lat) in records:
        easting, northing = _WGS84_TO_BNG.transform(lon, lat)
        graph.add_node((r, c), noise=noise, pos=(easting, northing))

    shifts = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for node in graph:
        r, c = node
        for dr, dc in shifts:
            nbr = (r + dr, c + dc)
            if nbr in graph and not graph.has_edge(node, nbr):
                n1, n2 = graph.nodes[node]["noise"], graph.nodes[nbr]["noise"]

                avg_noise_between_cells = (n1 + n2) / 2
                weight = NAVIGATION_GRID_CELL_SIZE / avg_noise_between_cells
                graph.add_edge(node, nbr, weight=weight)

    return graph


def get_navigation_graph():
    if path_exists(NAVIGATION_GRAPH_PATH):
        return load_graph(NAVIGATION_GRAPH_PATH)

    graph = build_graph()
    save_graph(graph, NAVIGATION_GRAPH_PATH)

    return graph

def generate_tree_from_graph(graph):
    return cKDTree([graph.nodes[n]["pos"] for n in graph])

def get_list_of_nodes_in_graph(graph):
    return list(graph.nodes)

def get_optimal_noise_based_route(graph, tree, nodes, start, end):
    start_node = find_nearest_node(tree, nodes, start)
    end_node = find_nearest_node(tree, nodes, end)

    return nx.shortest_path(graph, start_node, end_node, weight="weight")

def find_nearest_node(tree: cKDTree, nodes: list, point: Coordinate) -> tuple:
    _, idx = tree.query((point.easting, point.northing))

    return nodes[idx]
