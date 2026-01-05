import os
from pathlib import Path

import matplotlib
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pyproj import Transformer
from scipy.spatial import cKDTree

from common.coordinate import Coordinate
from noise.navigator.cost_function_generator import make_mixed_distance_noise_weight
from noise.noise_graph_builder import load_or_build_graph
from route_planner.straight_line_planner import StraightLinePlanner
from visualiser.plot_utils import add_font_style

matplotlib.use("Agg")

os.chdir(Path(__file__).resolve().parents[3])

WGS84_TO_OSGB36 = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)

_BASE_STYLES: dict[str, dict] = {
    "Distance": dict(color="#FFFFFF", linewidth=2.4, linestyle="-"),
}

_MIXED_STYLES_BY_ALPHA: dict[str, dict] = {
    "0.25": dict(color="#FF7F0E", linewidth=2.4, linestyle=":"),    # orange
    "0.50": dict(color="#00E5FF", linewidth=2.4, linestyle=":"),    # cyan
    "0.75": dict(color="#FF00FF", linewidth=2.6, linestyle=":"),    # magenta
    "1.00": dict(color="#FF0000", linewidth=2.6, linestyle=":"),    # red
}

_DEFAULT_STYLE = dict(color="#FFFFFF", linewidth=2.2, linestyle="-")


def coord_from_lonlat(lonlat: tuple[float, float]) -> Coordinate:
    lon, lat = lonlat
    easting, northing = WGS84_TO_OSGB36.transform(lon, lat)
    return Coordinate(northing=northing, easting=easting)


def build_kdtree(graph: nx.Graph) -> tuple[cKDTree, list[tuple[int, int]]]:
    nodes = list(graph.nodes)
    pts = np.asarray([(graph.nodes[n]["easting"], graph.nodes[n]["northing"]) for n in nodes], dtype=float)
    return cKDTree(pts), nodes


def nearest_node(tree: cKDTree, nodes: list[tuple[int, int]], point: Coordinate) -> tuple[int, int]:
    _, idx = tree.query((point.easting, point.northing))
    return nodes[int(idx)]


def _graph_to_noise_grid(graph: nx.Graph):
    nodes = list(graph.nodes)
    rows = np.fromiter((n[0] for n in nodes), dtype=int)
    cols = np.fromiter((n[1] for n in nodes), dtype=int)

    r0, c0 = int(rows.min()), int(cols.min())
    H = int(rows.max() - r0 + 1)
    W = int(cols.max() - c0 + 1)

    grid = np.full((H, W), np.nan, dtype=float)
    for (r, c) in nodes:
        grid[r - r0, c - c0] = graph.nodes[(r, c)].get("noise", np.nan)

    return grid, r0, c0


def _pad_to_square(grid: np.ndarray):
    H, W = grid.shape
    S = int(max(H, W))
    out = np.full((S, S), np.nan, dtype=float)

    top = (S - H) // 2
    left = (S - W) // 2
    out[top:top + H, left:left + W] = grid
    return out, top, left


def _parse_alpha_key(name: str) -> str | None:
    if not name.startswith("Mixed"):
        return None
    i = name.find("α=")
    if i < 0:
        return None
    j = name.find(")", i)
    if j < 0:
        return None
    return name[i + 2: j]


def _route_style(name: str) -> dict:
    if name in _BASE_STYLES:
        return _BASE_STYLES[name]
    akey = _parse_alpha_key(name)
    if akey is None:
        return _DEFAULT_STYLE
    return _MIXED_STYLES_BY_ALPHA.get(akey, _DEFAULT_STYLE)


def _dedupe_consecutive(nodes_route: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not nodes_route:
        return nodes_route
    out = [nodes_route[0]]
    for n in nodes_route[1:]:
        if n != out[-1]:
            out.append(n)
    return out


def sum_route_noise(graph: nx.Graph, route: list[tuple[int, int]]) -> float:
    total = 0.0
    for u, v in zip(route, route[1:]):
        data = graph[u][v]
        noise_u = graph.nodes[u].get("noise", 0.0)
        noise_v = graph.nodes[v].get("noise", 0.0)
        edge_noise = data.get("noise", (noise_u + noise_v) / 2.0)
        total += float(edge_noise)
    return total


def plot_routes_on_noise_grid(
    graph: nx.Graph,
    routes: dict[str, list[tuple[int, int]]],
    start_node: tuple[int, int],
    end_node: tuple[int, int],
    save_figure_path: str,
    square: bool = True,
    dpi: int = 600,
    also_save_png: bool = True,
):
    grid, r0, c0 = _graph_to_noise_grid(graph)

    top = left = 0
    if square:
        grid, top, left = _pad_to_square(grid)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.axis("off")

    vmin = np.nanmin(grid)
    grid_plot = np.where(np.isnan(grid), vmin, grid)

    im = ax.imshow(
        grid_plot,
        origin="lower",
        cmap=plt.cm.viridis,
        interpolation="nearest",
    )
    im.set_rasterized(True)
    ax.set_aspect("equal")

    for name, route in routes.items():
        pr = np.fromiter((n[0] for n in route), dtype=int) - r0 + top
        pc = np.fromiter((n[1] for n in route), dtype=int) - c0 + left

        style = _route_style(name)
        ln = ax.plot(pc, pr, label=name, **style)[0]
        ln.set_path_effects([
            pe.Stroke(linewidth=style.get("linewidth", 1.5) + 0.8, foreground="black"),
            pe.Normal(),
        ])

    sr = start_node[0] - r0 + top
    sc = start_node[1] - c0 + left
    er = end_node[0] - r0 + top
    ec = end_node[1] - c0 + left

    start_scatter = ax.scatter(
        [sc],
        [sr],
        s=70,
        marker="o",
        color="#FFFFFF",
        edgecolors="black",
        linewidths=1.0,
        zorder=10,
        label="Start",
    )
    end_scatter = ax.scatter(
        [ec],
        [er],
        s=80,
        marker="X",
        color="#FFFFFF",
        edgecolors="black",
        linewidths=1.0,
        zorder=10,
        label="End",
    )
    start_scatter.set_path_effects([pe.Stroke(linewidth=2.0, foreground="black"), pe.Normal()])
    end_scatter.set_path_effects([pe.Stroke(linewidth=2.0, foreground="black"), pe.Normal()])

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2.2%", pad=0.08)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("Noise level")

    ax.legend(loc="lower left", frameon=True, fontsize=10)
    add_font_style()

    pos = cax.get_position(fig)
    shrink = 0.8
    new_height = pos.height * shrink
    cax.set_position([pos.x0, pos.y0 + (pos.height - new_height) / 2, pos.width, new_height])

    fig.savefig(save_figure_path, dpi=dpi, bbox_inches="tight", pad_inches=0.02)
    if also_save_png:
        fig.savefig(str(Path(save_figure_path).with_suffix(".png")), dpi=dpi, bbox_inches="tight", pad_inches=0.02)

    plt.close(fig)


def get_noise_route_navigation(
    A_lonlat: tuple[float, float],
    B_lonlat: tuple[float, float],
    alphas: list[float],
    figure_save_path: str,
):
    start = coord_from_lonlat(A_lonlat)
    end = coord_from_lonlat(B_lonlat)

    graph = load_or_build_graph()
    tree, nodes = build_kdtree(graph)

    start_node = nearest_node(tree, nodes, start)
    end_node = nearest_node(tree, nodes, end)

    routes: dict[str, list[tuple[int, int]]] = {}

    planner = StraightLinePlanner()
    straight_coords = planner.plan_route(start, end)
    straight_nodes = [nearest_node(tree, nodes, p) for p in straight_coords]
    routes["Distance"] = _dedupe_consecutive(straight_nodes)

    for alpha in alphas:
        mixed_weight = make_mixed_distance_noise_weight(
            graph=graph,
            alpha=alpha,
            dist_keys=("distance",),
            noise_keys=("noise",),
            higher_noise_is_better=True,
        )
        routes[f"Mixed (α={alpha:.2f})"] = nx.shortest_path(graph, start_node, end_node, weight=mixed_weight)

    plot_routes_on_noise_grid(
        graph=graph,
        routes=routes,
        start_node=start_node,
        end_node=end_node,
        save_figure_path=figure_save_path,
        square=True,
        dpi=300,
        also_save_png=True,
    )

    print("Distance nodes:", len(routes["Distance"]))

    for alpha in alphas:
        name = f"Mixed (α={alpha:.2f})"
        print(f"{name} nodes:", len(routes[name]))
        print(f"{name} noise sum:", sum_route_noise(graph, routes[name]))


if __name__ == "__main__":
    A = (-0.310795, 51.369156)
    B = (0.247855, 51.609507)

    alphas = [0.25, 0.50, 0.75, 1.00]

    figure_save_path = "figures/navigation_routes_distance_noise_mixed.eps"

    get_noise_route_navigation(A, B, alphas, figure_save_path)
