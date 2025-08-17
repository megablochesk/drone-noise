import json
from pathlib import Path

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.spatial import cKDTree
from shapely.geometry import shape

matplotlib.use("TkAgg")


from common.path_configs import NAVIGATION_BASE_NOISE_PATH


def read_base_noise_data(path: str) -> pd.DataFrame:
    with open(path) as f:
        data = json.load(f)

    records = [
        (
            feat["properties"].get("row", 0),
            feat["properties"].get("col", 0),
            feat["properties"].get("noise_level", 0.0),
            shape(feat["geometry"]).centroid.coords[0],
        )
        for feat in data.get("features", [])
    ]
    return pd.DataFrame(records, columns=["row", "col", "noise", "centroid"])


def save_graphml(graph: nx.Graph, path: str) -> None:
    H = nx.Graph()
    for (r, c), data in graph.nodes(data=True):
        x, y = data["pos"]
        H.add_node(f"{r}_{c}", noise=data["noise"], pos_x=x, pos_y=y)

    for (r1, c1), (r2, c2), ed in graph.edges(data=True):
        H.add_edge(f"{r1}_{c1}", f"{r2}_{c2}", weight=ed["weight"])

    nx.write_graphml(H, path)


def load_graphml(path: str) -> nx.Graph:
    H = nx.read_graphml(path)
    G = nx.Graph()

    for node_id, data in H.nodes(data=True):
        r, c = map(int, node_id.split("_"))
        G.add_node(
            (r, c),
            noise=float(data["noise"]),
            pos=(float(data["pos_x"]), float(data["pos_y"])),
        )

    for u_id, v_id, data in H.edges(data=True):
        u = tuple(map(int, u_id.split("_")))
        v = tuple(map(int, v_id.split("_")))
        G.add_edge(u, v, weight=float(data["weight"]))

    return G


def build_noise_graph(df: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()

    node_ids = df[["row", "col"]].apply(tuple, axis=1).values
    centroids = np.vstack(df["centroid"].values)
    noises = df["noise"].values
    idx_map = {node: i for i, node in enumerate(node_ids)}
    grid = set(node_ids)

    for node, (x, y), n in zip(node_ids, centroids, noises):
        G.add_node(node, noise=n, pos=(x, y))

    shifts = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for node in node_ids:
        i, j = node
        for di, dj in shifts:
            nbr = (i + di, j + dj)
            if nbr in grid and not G.has_edge(node, nbr):
                ia, ib = idx_map[node], idx_map[nbr]
                x1, y1 = centroids[ia]
                x2, y2 = centroids[ib]
                dist = np.hypot(x1 - x2, y1 - y2)
                weight = dist / ((noises[ia] + noises[ib]) / 2)
                G.add_edge(node, nbr, weight=weight)

    return G


def build_kdtree(graph: nx.Graph):
    pts = np.array([graph.nodes[n]["pos"] for n in graph.nodes])
    return cKDTree(pts), list(graph.nodes)


def nearest_node(tree: cKDTree, nodes: list, point: tuple) -> tuple:
    _, idx = tree.query(point)
    return nodes[idx]


def shortest_path(
    graph: nx.Graph, tree: cKDTree, nodes: list, start_pt: tuple, end_pt: tuple
):
    start = nearest_node(tree, nodes, start_pt)
    end = nearest_node(tree, nodes, end_pt)
    return nx.shortest_path(graph, start, end, weight="weight")


def plot_noise_graph(G, path, figsize=(10, 10)):
    pos = nx.get_node_attributes(G, 'pos')
    plt.figure(figsize=figsize)
    nx.draw_networkx_edges(G, pos, edge_color='lightgray', width=1)
    noise = [G.nodes[n]['noise'] for n in G.nodes()]
    nodes = nx.draw_networkx_nodes(
        G, pos,
        node_size=50,
        cmap=plt.cm.viridis,
        node_color=noise
    )
    plt.colorbar(nodes, label='Noise level')
    path_edges = list(zip(path, path[1:]))
    nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='red', width=2)
    nx.draw_networkx_nodes(G, pos, nodelist=path, node_color='red', node_size=2)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def main():
    graphml_path = '../' + NAVIGATION_BASE_NOISE_PATH.replace(".geojson", ".graphml")

    if Path(graphml_path).exists():
        graph = load_graphml(graphml_path)
    else:
        df = read_base_noise_data(NAVIGATION_BASE_NOISE_PATH)
        graph = build_noise_graph(df)
        save_graphml(graph, graphml_path)

    tree, nodes = build_kdtree(graph)

    A = (0.160277, 51.200773)
    B = (-0.447186, 51.653594)

    path = shortest_path(graph, tree, nodes, A, B)

    plot_noise_graph(graph, path, (10, 10))

    print("Path length:", len(path))


if __name__ == "__main__":
    main()
