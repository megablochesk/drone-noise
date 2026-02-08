from __future__ import annotations

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

from common.coordinate import Coordinate, calculate_distance
from noise.navigator.cost_function_generator import make_mixed_distance_noise_weight
from noise.noise_graph_builder import load_or_build_graph
from visualiser.plot_utils import add_font_style

matplotlib.use("Agg")

os.chdir(Path(__file__).resolve().parents[3])

WGS84_TO_OSGB36 = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)

try:
    from common.model_configs import model_config

    MODEL_TIME_STEP = float(model_config.time.step_s)
    DRONE_SPEED = float(model_config.drone.speed_mps)
except Exception:
    MODEL_TIME_STEP = 1.0
    DRONE_SPEED = 10.0


_BASE_STYLES: dict[str, dict] = {
    "Distance": dict(color="#FFFFFF", linewidth=2.4, linestyle="-"),
}

_MIXED_STYLES_BY_ALPHA: dict[str, dict] = {
    "0.25": dict(color="#FF7F0E", linewidth=2.4, linestyle=":"),  # orange
    "0.50": dict(color="#00E5FF", linewidth=2.4, linestyle=":"),  # cyan
    "0.75": dict(color="#FF00FF", linewidth=2.6, linestyle=":"),  # magenta
    "1.00": dict(color="#FF0000", linewidth=2.6, linestyle=":"),  # red
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
    out[top : top + H, left : left + W] = grid
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
    return name[i + 2 : j]


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


def route_length_m(graph: nx.Graph, route: list[tuple[int, int]], distance_key: str = "distance") -> float:
    total = 0.0
    for u, v in zip(route, route[1:]):
        data = graph[u][v]
        d = data.get(distance_key, None)
        if d is None:
            a = graph.nodes[u]
            b = graph.nodes[v]
            dx = float(b["easting"]) - float(a["easting"])
            dy = float(b["northing"]) - float(a["northing"])
            d = (dx * dx + dy * dy) ** 0.5
        total += float(d)
    return total


def polyline_length_m(coords: list[Coordinate]) -> float:
    total = 0.0
    for a, b in zip(coords, coords[1:]):
        total += float(calculate_distance(a, b))
    return total


def resample_polyline_by_time(coords: list[Coordinate], speed: float, dt: float) -> list[Coordinate]:
    if len(coords) <= 1:
        return coords

    step_dist = speed * dt
    if step_dist <= 0:
        return coords

    cum = _cumulative_distances(coords)
    total = float(cum[-1])
    if total <= 0:
        return [coords[0], coords[-1]]

    targets = _targets(total, step_dist)
    return _resample_by_targets(coords, cum, targets)


def _cumulative_distances(coords: list[Coordinate]) -> np.ndarray:
    cum = np.zeros(len(coords), dtype=float)
    for i in range(1, len(coords)):
        cum[i] = cum[i - 1] + calculate_distance(coords[i - 1], coords[i])
    return cum


def _targets(total: float, step_dist: float) -> np.ndarray:
    if step_dist >= total:
        return np.array([0.0, total], dtype=float)
    t = np.arange(0.0, total, step_dist, dtype=float)
    if t.size == 0 or t[-1] != total:
        t = np.append(t, total)
    return t


def _resample_by_targets(coords: list[Coordinate], cum: np.ndarray, targets: np.ndarray) -> list[Coordinate]:
    out: list[Coordinate] = []
    j = 0
    n = len(coords)

    for d in targets:
        while j < n - 2 and cum[j + 1] < d:
            j += 1

        d0 = float(cum[j])
        d1 = float(cum[j + 1])
        seg = d1 - d0
        if seg <= 0.0:
            out.append(coords[j])
            continue

        t = (float(d) - d0) / seg
        a = coords[j]
        b = coords[j + 1]
        e = a.easting + (b.easting - a.easting) * t
        n_ = a.northing + (b.northing - a.northing) * t
        out.append(Coordinate(northing=n_, easting=e))

    return out


def _node_to_coord(graph: nx.Graph, node: tuple[int, int]) -> Coordinate:
    nd = graph.nodes[node]
    return Coordinate(northing=float(nd["northing"]), easting=float(nd["easting"]))


def _route_nodes_to_coords(graph: nx.Graph, route: list[tuple[int, int]]) -> list[Coordinate]:
    return [_node_to_coord(graph, n) for n in route]


def resample_route_nodes_by_time(
    graph: nx.Graph,
    route: list[tuple[int, int]],
    tree: cKDTree,
    nodes: list[tuple[int, int]],
    start: Coordinate,
    end: Coordinate,
    speed: float,
    dt: float,
) -> list[tuple[int, int]]:
    if not route:
        return []

    coords = _route_nodes_to_coords(graph, route)
    sampled = resample_polyline_by_time(coords, speed=speed, dt=dt)

    sampled[0] = start
    sampled[-1] = end

    snapped = [nearest_node(tree, nodes, p) for p in sampled]
    return _dedupe_consecutive(snapped)


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
        ln.set_path_effects(
            [
                pe.Stroke(linewidth=style.get("linewidth", 1.5) + 0.8, foreground="black"),
                pe.Normal(),
            ]
        )

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
    speed: float = DRONE_SPEED,
    dt: float = MODEL_TIME_STEP,
    distance_key: str = "distance",
):
    start = coord_from_lonlat(A_lonlat)
    end = coord_from_lonlat(B_lonlat)

    graph = load_or_build_graph()
    tree, nodes = build_kdtree(graph)

    start_node = nearest_node(tree, nodes, start)
    end_node = nearest_node(tree, nodes, end)

    raw_routes: dict[str, list[tuple[int, int]]] = {}
    plot_routes: dict[str, list[tuple[int, int]]] = {}

    straight_coords = resample_polyline_by_time([start, end], speed=speed, dt=dt)
    straight_nodes = [nearest_node(tree, nodes, p) for p in straight_coords]
    plot_routes["Distance"] = _dedupe_consecutive(straight_nodes)

    for alpha in alphas:
        mixed_weight = make_mixed_distance_noise_weight(
            graph=graph,
            alpha=alpha,
            dist_keys=(distance_key,),
            noise_keys=("noise",),
            higher_noise_is_better=True,
        )

        name = f"Mixed (α={alpha:.2f})"
        raw = nx.shortest_path(graph, start_node, end_node, weight=mixed_weight)
        raw_routes[name] = raw

        plot_routes[name] = resample_route_nodes_by_time(
            graph=graph,
            route=raw,
            tree=tree,
            nodes=nodes,
            start=start,
            end=end,
            speed=speed,
            dt=dt,
        )

    plot_routes_on_noise_grid(
        graph=graph,
        routes=plot_routes,
        start_node=start_node,
        end_node=end_node,
        save_figure_path=figure_save_path,
        square=True,
        dpi=300,
        also_save_png=True,
    )

    straight_length = polyline_length_m([start, end])
    print("Distance nodes:", len(plot_routes["Distance"]))
    print("Distance length (m):", int(straight_length))

    for alpha in alphas:
        name = f"Mixed (α={alpha:.2f})"

        raw = raw_routes[name]
        sampled = plot_routes[name]

        raw_len = route_length_m(graph, raw, distance_key=distance_key)
        sampled_len = polyline_length_m(_route_nodes_to_coords(graph, sampled))
        noise_sum = sum_route_noise(graph, raw)

        print(f"{name} nodes:", int(len(sampled)))
        print(f"{name} length raw (m):", int(raw_len))
        print(f"{name} length sampled (m):", int(sampled_len))
        print(f"{name} noise sum:", int(noise_sum))


if __name__ == "__main__":
    A = (-0.310795, 51.369156)
    B = (0.247855, 51.609507)

    alphas = [0.25, 0.50, 0.75, 1.00]
    figure_save_path = "figures/navigation_routes_distance_noise_mixed.eps"

    get_noise_route_navigation(A, B, alphas, figure_save_path)
