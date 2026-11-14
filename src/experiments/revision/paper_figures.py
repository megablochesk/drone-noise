"""The paper's figures redrawn on the fine-grid design (Round 4 baseline, 100 m cells, 10 s step), as EPS.

Figure numbers follow the submitted paper. Figure 2 (a simulation snapshot on a street map) is not drawn: it
needs map tiles from the internet. All runs are of one seed.

Usage (from src/): python -m experiments.revision.paper_figures [--preview-directory DIRECTORY]
"""
import matplotlib

matplotlib.use("Agg")

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib import pyplot as plt
from matplotlib import ticker
from pyproj import Transformer

from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity, load_cell_population
from common.coordinate import Coordinate
from common.model_configs import model_config
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.fine_grid_design import FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M, PHASE_NAME
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.result_store import ResultStore, load_drone_levels
from experiments.revision.run_executor import HEADLINE_EXPOSURE_THRESHOLD_DB
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from metrics.cell_table import align_to_grid, load_cell_table
from metrics.exposure_metrics import combine_levels_db, find_newly_exposed_cells
from noise.navigator.grid_route_navigator import GridRouteNavigator
from noise.navigator.navigation_grid import NavigationGrid, calculate_mixed_edge_costs
from noise.navigator.navigation_grid_loader import load_navigation_grid
from noise.noise_grid import NoiseGrid, load_noise_grid, to_grid_image
from visualiser.single_sim_group_impact import _ETHNICITY_ABBREVIATIONS

RUN_TABLE_NAME = "paper_figure_runs.csv"
FIGURE_DIRECTORY_NAME = "paper_figures_100m_10s_round4"
FIGURE_FORMAT = "eps"
PREVIEW_FORMAT = "png"
PREVIEW_DPI = 110
MAP_DPI = 300
# The look of the submitted figures: serif text at 15 pt.
PAPER_STYLE = {"font.family": "serif", "font.size": 15, "axes.titlesize": 15, "legend.fontsize": 13}

STRAIGHT = "STRAIGHT"
NOISE_AWARE_NAVIGATIONS = ("NOISE_A025", "NOISE_A050", "NOISE_A075", "NOISE_A100")
MAPPED_FLEET = 1250
# The scenario the paper uses for its single-run figures: straight routes, random stocking, largest fleet.
EXAMPLE_STOCKING = "random"

STOCKING_LINE_ORDER = ("furthest", "closest", "random")
STOCKING_PANEL_ORDER = ("furthest", "random", "closest")
STOCKING_MAP_ORDER = ("closest", "random", "furthest")
STOCKING_LEGEND = {"furthest": "worst-case stocking", "closest": "best-case stocking", "random": "random stocking"}
STOCKING_TITLES = {"furthest": "Worst Stocking", "random": "Random Stocking", "closest": "Best Stocking"}
STOCKING_LINE_STYLES = {"furthest": "-", "closest": "--", "random": ":"}
STOCKING_MARKERS = {"furthest": "o", "closest": "s", "random": "^"}
NAVIGATION_LINE_STYLES = {STRAIGHT: "-", "NOISE_A025": "--", "NOISE_A050": ":", "NOISE_A075": "-.", "NOISE_A100": "-"}
NAVIGATION_MARKERS = {STRAIGHT: "o", "NOISE_A025": "s", "NOISE_A050": "^", "NOISE_A075": "D", "NOISE_A100": "x"}
ROUTE_STYLES = {
    STRAIGHT: dict(color="#FFFFFF", linewidth=2.2, linestyle="-", zorder=5),
    "NOISE_A025": dict(color="#FF00FF", linewidth=2.4, linestyle="--", zorder=2),
    "NOISE_A050": dict(color="#00E5FF", linewidth=2.4, linestyle="--", zorder=4),
    "NOISE_A075": dict(color="#FF7F0E", linewidth=2.6, linestyle="--", zorder=3),
    "NOISE_A100": dict(color="#FF0000", linewidth=2.6, linestyle="-", zorder=1),
}
ROUTE_OUTLINE_EXTRA_WIDTH = 0.8
ROUTE_START_LONGITUDE_LATITUDE = (-0.310795, 51.369156)
ROUTE_END_LONGITUDE_LATITUDE = (0.247855, 51.609507)

GRID_LINE_COLOUR = "#c8c8c8"
MINOR_GRID_LINE_COLOUR = "#e4e4e4"
COLOUR_MAP = "viridis"
OUTSIDE_STUDY_AREA_COLOUR = "white"
LEGEND_TITLE = "Warehouse Stock Conditions"
FLEET_LABEL = "Number of Drones"
DELIVERIES_LABEL = "Number of Delivered Orders"
NOISE_INCREASE_LABEL = "Average Noise Increase (dB)"
NEWLY_EXPOSED_LABEL = "Extra Population Exposed to Noise over 55 dB"
NOISE_LEVEL_LABEL = "Noise level (dB)"
INDIAN_GROUP_NAME = "Indian"
THOUSAND = 1000


def describe_navigation(navigation: str) -> str:
    alpha = re.search(r"_A(\d+)$", navigation)
    return f"Mixed (α={int(alpha.group(1)) / 100:.2f})" if alpha else "Straight"


def read_navigation(runs: pd.DataFrame) -> pd.Series:
    """Runs stored before the routing was recorded were all straight-line."""
    if "navigation" not in runs:
        return pd.Series(STRAIGHT, index=runs.index)
    return runs["navigation"].fillna(STRAIGHT)


def tabulate_metric_by_fleet(runs: pd.DataFrame, metric: str, terminal_phases: bool, navigation: str) -> pd.DataFrame:
    """Fleet sizes down, stockings across; every cell must come from exactly one run."""
    selected = runs[(runs["terminal_phases"] == terminal_phases) & (read_navigation(runs) == navigation)]
    runs_per_cell = selected.groupby(["number_of_drones", "stocking"]).size().unstack()
    if selected.empty or runs_per_cell.isna().any().any() or (runs_per_cell != 1).any().any():
        raise ValueError(f"Every fleet and stocking needs exactly one run of {navigation}, terminal phases {terminal_phases}")
    return selected.pivot(index="number_of_drones", columns="stocking", values=metric).sort_index()


def summarise_group_exposure(
        newly_exposed: np.ndarray, group_counts: dict[int, np.ndarray], group_names: dict[int, str]
) -> pd.DataFrame:
    """Per group: residents of the newly exposed cells, all residents, and the share of the group exposed."""
    summary = pd.DataFrame({
        "code": list(group_counts),
        "name": [group_names[code] for code in group_counts],
        "newly_exposed": [counts[newly_exposed].sum() for counts in group_counts.values()],
        "total": [counts.sum() for counts in group_counts.values()],
    })
    return summary.assign(share=summary["newly_exposed"] / summary["total"])


def find_shared_colour_range(maps: list[np.ndarray], lower_percentile: float, upper_percentile: float) -> tuple[float, float]:
    values = np.concatenate([image[np.isfinite(image)] for image in maps])
    return float(np.percentile(values, lower_percentile)), float(np.percentile(values, upper_percentile))


def select_run_key(runs: pd.DataFrame, stocking: str, navigation: str, terminal_phases: bool = True) -> str:
    selected = runs[
        (runs["number_of_drones"] == MAPPED_FLEET) & (runs["stocking"] == stocking)
        & (runs["terminal_phases"] == terminal_phases) & (read_navigation(runs) == navigation)
    ]
    if len(selected) != 1:
        raise ValueError(f"Expected one run of {stocking}, {navigation}, found {len(selected)}")
    return selected["run_key"].iloc[0]


def save_figure(figure, directory: Path, name: str, preview_directory: Path | None):
    figure.savefig(directory / f"{name}.{FIGURE_FORMAT}", format=FIGURE_FORMAT, dpi=MAP_DPI, bbox_inches="tight")
    if preview_directory is not None:
        figure.savefig(preview_directory / f"{name}.{PREVIEW_FORMAT}", dpi=PREVIEW_DPI, bbox_inches="tight")
    plt.close(figure)


def style_value_axis(axis):
    """Dotted horizontal guides; EPS has no transparency, so the guides are light greys."""
    axis.grid(axis="y", linestyle=":", linewidth=0.7, color=GRID_LINE_COLOUR)
    axis.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    axis.grid(axis="y", which="minor", linestyle=":", linewidth=0.4, color=MINOR_GRID_LINE_COLOUR)
    axis.set_axisbelow(True)


def plot_stocking_lines(table: pd.DataFrame, value_label: str):
    """Figures 4-9: one line per stocking against the fleet size."""
    figure, axis = plt.subplots(figsize=(13, 6))
    colours = plt.get_cmap("tab10")
    for position, stocking in enumerate(STOCKING_LINE_ORDER):
        axis.plot(
            table.index, table[stocking], marker=STOCKING_MARKERS[stocking], linestyle=STOCKING_LINE_STYLES[stocking],
            color=colours(position), label=STOCKING_LEGEND[stocking], linewidth=2, markersize=6,
        )
    axis.set_xlabel(FLEET_LABEL)
    axis.set_ylabel(value_label)
    axis.set_xticks(table.index)
    axis.legend(title=LEGEND_TITLE, frameon=True, edgecolor="black", fancybox=False)
    style_value_axis(axis)
    figure.tight_layout()
    return figure


def format_compact_value(value: float, _position) -> str:
    if value >= THOUSAND:
        return f"{value / THOUSAND:g}k"
    return f"{value:g}"


def plot_navigation_panels(runs: pd.DataFrame, metric: str, value_label: str):
    """Figures 12-14: one panel per stocking, one line per routing, terminal phases on."""
    navigations = (STRAIGHT, *NOISE_AWARE_NAVIGATIONS)
    tables = {navigation: tabulate_metric_by_fleet(runs, metric, True, navigation) for navigation in navigations}
    figure, axes = plt.subplots(1, len(STOCKING_PANEL_ORDER), figsize=(15, 6), sharey=True)
    colours = plt.get_cmap("tab10")
    for axis, stocking in zip(axes, STOCKING_PANEL_ORDER):
        for position, navigation in enumerate(navigations):
            axis.plot(
                tables[navigation].index, tables[navigation][stocking], marker=NAVIGATION_MARKERS[navigation],
                linestyle=NAVIGATION_LINE_STYLES[navigation], color=colours(position), linewidth=2, markersize=6,
                label=describe_navigation(navigation),
            )
        axis.set_title(STOCKING_TITLES[stocking])
        axis.set_xlabel(FLEET_LABEL)
        axis.set_xticks(tables[STRAIGHT].index)
        axis.tick_params(axis="x", labelsize=8)
        axis.tick_params(axis="y", labelleft=True)
        axis.yaxis.set_major_locator(ticker.MaxNLocator(nbins=8))
        axis.yaxis.set_major_formatter(ticker.FuncFormatter(format_compact_value))
        style_value_axis(axis)
    axes[0].set_ylabel(value_label)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    return figure


def draw_map(axis, image: np.ndarray, title: str | None, colour_range: tuple[float, float], colour_bar_label: str):
    colour_map = plt.get_cmap(COLOUR_MAP).copy()
    colour_map.set_bad(OUTSIDE_STUDY_AREA_COLOUR)
    drawn = axis.imshow(
        np.ma.masked_invalid(image), origin="lower", cmap=colour_map, vmin=colour_range[0], vmax=colour_range[1],
        interpolation="nearest",
    )
    if title:
        axis.set_title(title)
    axis.set_xlabel("Grid Column")
    axis.set_ylabel("Grid Row")
    axis.figure.colorbar(drawn, ax=axis, fraction=0.04, pad=0.03, label=colour_bar_label)


def plot_map_row(images: list[np.ndarray], titles: list[str], colour_ranges: list[tuple[float, float]], labels: list[str]):
    figure, axes = plt.subplots(1, len(images), figsize=(6.5 * len(images), 5.2))
    for axis, image, title, colour_range, label in zip(np.atleast_1d(axes), images, titles, colour_ranges, labels):
        draw_map(axis, image, title, colour_range, label)
    figure.tight_layout()
    return figure


def plot_single_map(image: np.ndarray, colour_range: tuple[float, float], colour_bar_label: str):
    figure, axis = plt.subplots(figsize=(8, 6.2))
    draw_map(axis, image, None, colour_range, colour_bar_label)
    figure.tight_layout()
    return figure


def load_drone_maps(store: ResultStore, grid: NoiseGrid, runs: pd.DataFrame, navigation: str) -> list[np.ndarray]:
    """Drone-only level of the largest fleet as an image, one per stocking."""
    return [
        to_grid_image(grid, load_drone_levels(store, select_run_key(runs, stocking, navigation)))
        for stocking in STOCKING_MAP_ORDER
    ]


def plot_drone_maps(images: list[np.ndarray], colour_range: tuple[float, float]):
    """Figures 10, 15, 16: drone-only level per stocking, on the colour range shared by the three figures."""
    return plot_map_row(
        images, [STOCKING_TITLES[stocking] for stocking in STOCKING_MAP_ORDER], [colour_range] * len(images),
        [NOISE_LEVEL_LABEL] * len(images),
    )


def plot_noise_comparison(grid: NoiseGrid, baseline_levels_db: np.ndarray, drone_levels_db: np.ndarray):
    """Figure 3: baseline, drone-only level and the rise of the combined level above the baseline."""
    increases_db = combine_levels_db(baseline_levels_db, drone_levels_db) - baseline_levels_db
    images = [to_grid_image(grid, values) for values in (baseline_levels_db, drone_levels_db, increases_db)]
    colour_ranges = [
        find_shared_colour_range([images[0]], 0.0, 99.9), find_shared_colour_range([images[1]], 1.0, 99.9),
        (0.0, find_shared_colour_range([images[2]], 0.0, 99.9)[1]),
    ]
    return plot_map_row(
        images, ["Base City Noise", "Drone Noise", "City Noise Increase"], colour_ranges,
        [NOISE_LEVEL_LABEL, NOISE_LEVEL_LABEL, "Noise increase (dB)"],
    )


def plot_group_bars(summary: pd.DataFrame, value_column: str, labels: list[str], as_percentage: bool):
    """Figures 17-20: one horizontal bar per group, with its value written at the end of the bar."""
    values = summary[value_column].to_numpy(dtype=float) * (100.0 if as_percentage else 1.0)
    positions = np.arange(len(summary))
    figure, axis = plt.subplots(figsize=(10.5, max(3.8, 0.28 * len(summary) + 1.2)))
    axis.barh(positions, values, height=0.75)
    axis.set_yticks(positions, labels)
    axis.invert_yaxis()
    axis.tick_params(axis="y", labelsize=11)
    value_format = "{x:,.2f}%" if as_percentage else "{x:,.0f}"
    axis.xaxis.set_major_formatter(ticker.StrMethodFormatter(value_format))
    axis.grid(axis="x", linestyle="--", color=GRID_LINE_COLOUR)
    axis.set_axisbelow(True)
    for position, value in zip(positions, values):
        axis.text(value + 0.01 * values.max(), position, value_format.format(x=value), va="center", ha="left", fontsize=11)
    axis.set_xlim(right=values.max() * 1.12)
    figure.tight_layout()
    return figure


def read_group_counts(grid: NoiseGrid, group_table: pd.DataFrame) -> dict[int, np.ndarray]:
    group_codes = [column for column in group_table.columns if isinstance(column, (int, np.integer))]
    return {int(code): align_to_grid(grid, group_table, code) for code in group_codes}


def shorten_ethnicity_names(code_to_name: dict[int, str]) -> dict[int, str]:
    """'Asian, Asian British or Asian Welsh: Indian' -> 'Indian', the name the paper's codes are keyed by."""
    return {int(code): name.split(": ", 1)[-1].strip() for code, name in code_to_name.items()}


def convert_to_coordinate(longitude_latitude: tuple[float, float]) -> Coordinate:
    easting, northing = Transformer.from_crs(4326, 27700, always_xy=True).transform(*longitude_latitude)
    return Coordinate(northing=northing, easting=easting)


def find_example_routes(navigation_grid: NavigationGrid, start: Coordinate, end: Coordinate) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Eastings and northings of the straight line and of the route of every alpha between the two places."""
    routes = {STRAIGHT: (np.array([start.easting, end.easting]), np.array([start.northing, end.northing]))}
    for navigation in NOISE_AWARE_NAVIGATIONS:
        alpha = int(navigation[-3:]) / 100
        navigator = GridRouteNavigator(navigation_grid, calculate_mixed_edge_costs(navigation_grid, alpha), [])
        routes[navigation] = navigator.get_optimal_route_coordinates(start, end)
    return routes


def measure_route_lengths(routes: dict[str, tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
    lengths_m = {name: np.hypot(np.diff(eastings), np.diff(northings)).sum() for name, (eastings, northings) in routes.items()}
    return pd.DataFrame({
        "navigation": list(lengths_m), "route_length_km": [length / THOUSAND for length in lengths_m.values()],
        "increase_over_straight": [length / lengths_m[STRAIGHT] - 1.0 for length in lengths_m.values()],
    })


def plot_route_example(navigation_grid: NavigationGrid, routes: dict[str, tuple[np.ndarray, np.ndarray]]):
    """Figure 11: the routes of every routing between two places, over the baseline map of the navigation grid."""
    boundaries, cell_size_m = model_config.map_boundaries, navigation_grid.cell_size_m
    image = np.full((navigation_grid.rows.max() + 1, navigation_grid.columns.max() + 1), np.nan)
    image[navigation_grid.rows, navigation_grid.columns] = navigation_grid.noise_levels_db

    figure, axis = plt.subplots(figsize=(10 * image.shape[1] / image.shape[0], 10))
    drawn = axis.imshow(image, origin="lower", cmap=COLOUR_MAP, interpolation="nearest")
    axis.axis("off")
    for navigation, (eastings, northings) in routes.items():
        style = ROUTE_STYLES[navigation]
        label = "Distance" if navigation == STRAIGHT else describe_navigation(navigation)
        columns = (eastings - boundaries.left) / cell_size_m - 0.5
        rows = (northings - boundaries.bottom) / cell_size_m - 0.5
        line = axis.plot(columns, rows, label=label, **style)[0]
        line.set_path_effects([
            patheffects.Stroke(linewidth=style["linewidth"] + ROUTE_OUTLINE_EXTRA_WIDTH, foreground="black"),
            patheffects.Normal(),
        ])
    straight_columns = (routes[STRAIGHT][0] - boundaries.left) / cell_size_m - 0.5
    straight_rows = (routes[STRAIGHT][1] - boundaries.bottom) / cell_size_m - 0.5
    axis.scatter(straight_columns[:1], straight_rows[:1], marker="o", s=70, color="white", edgecolor="black", zorder=6, label="Start")
    axis.scatter(straight_columns[1:], straight_rows[1:], marker="X", s=90, color="white", edgecolor="black", zorder=6, label="End")
    axis.legend(loc="upper left", frameon=True, facecolor="white", framealpha=1.0)
    figure.colorbar(drawn, ax=axis, fraction=0.035, pad=0.01, label=NOISE_LEVEL_LABEL)
    figure.tight_layout()
    return figure


def draw_fleet_figures(runs: pd.DataFrame, save):
    for first_figure_number, metric, label in [
        (4, "delivered_orders", DELIVERIES_LABEL), (6, "mean_noise_increase_db", NOISE_INCREASE_LABEL),
        (8, "newly_exposed_population_55db", NEWLY_EXPOSED_LABEL),
    ]:
        for offset, terminal_phases in enumerate([False, True]):
            profile = "terminal_phases" if terminal_phases else "cruise_only"
            table = tabulate_metric_by_fleet(runs, metric, terminal_phases, STRAIGHT)
            save(plot_stocking_lines(table, label), f"fig{first_figure_number + offset:02d}_{metric}_{profile}")
    save(plot_navigation_panels(runs, "delivered_orders", "Delivered Orders"), "fig12_delivered_orders_by_navigation")
    save(plot_navigation_panels(runs, "mean_noise_increase_db", NOISE_INCREASE_LABEL), "fig13_mean_noise_increase_by_navigation")
    save(plot_navigation_panels(runs, "newly_exposed_population_55db", "Newly Exposed Population"), "fig14_newly_exposed_by_navigation")


def draw_map_figures(store: ResultStore, grid: NoiseGrid, runs: pd.DataFrame, baseline_levels_db: np.ndarray, save):
    example_levels_db = load_drone_levels(store, select_run_key(runs, EXAMPLE_STOCKING, STRAIGHT))
    save(plot_noise_comparison(grid, baseline_levels_db, example_levels_db), "fig03_noise_maps")
    figure_names = {
        STRAIGHT: "fig10_drone_noise_straight", "NOISE_A050": "fig15_drone_noise_alpha_050",
        "NOISE_A100": "fig16_drone_noise_alpha_100",
    }
    images = {navigation: load_drone_maps(store, grid, runs, navigation) for navigation in figure_names}
    all_images = [image for navigation_images in images.values() for image in navigation_images]
    colour_range = find_shared_colour_range(all_images, lower_percentile=1.0, upper_percentile=99.9)
    for navigation, figure_name in figure_names.items():
        save(plot_drone_maps(images[navigation], colour_range), figure_name)


def draw_population_figures(grid: NoiseGrid, population: np.ndarray, ethnicity_counts: dict, ethnicity_names: dict, save):
    population_image = to_grid_image(grid, population)
    save(plot_single_map(population_image, (0.0, np.nanmax(population_image)), "Population per grid cell"), "fig01_population")
    indian_code = next(code for code, name in ethnicity_names.items() if name == INDIAN_GROUP_NAME)
    indian_image = to_grid_image(grid, ethnicity_counts[indian_code])
    indian_range = (0.0, find_shared_colour_range([indian_image], 0.0, 99.9)[1])
    save(plot_single_map(indian_image, indian_range, "Population per cell"), "fig21_indian_population")


def draw_group_figures(newly_exposed: np.ndarray, grid: NoiseGrid, ethnicity_counts: dict, ethnicity_names: dict, save) -> pd.DataFrame:
    age_table = load_cell_age(FINE_CELL_SIZE_M)
    age_names = age_table.attrs["age_code_to_name"]
    ethnicity = summarise_group_exposure(newly_exposed, ethnicity_counts, ethnicity_names)
    ethnicity = ethnicity.assign(label=[_ETHNICITY_ABBREVIATIONS[name] for name in ethnicity["name"]])
    age = summarise_group_exposure(newly_exposed, read_group_counts(grid, age_table), age_names)
    age = age.assign(label=age["name"])

    by_share = ethnicity.sort_values("share", ascending=False, kind="mergesort")
    by_label = ethnicity.sort_values("label", kind="mergesort")
    age_by_share = age.sort_values("share", ascending=False, kind="mergesort")
    save(plot_group_bars(by_share, "share", by_share["label"].tolist(), as_percentage=True), "fig17_ethnic_groups_share")
    save(plot_group_bars(by_label, "newly_exposed", by_label["label"].tolist(), as_percentage=False), "fig18_ethnic_groups_count")
    save(plot_group_bars(age_by_share, "share", age_by_share["label"].tolist(), as_percentage=True), "fig19_age_groups_share")
    save(plot_group_bars(age, "newly_exposed", age["label"].tolist(), as_percentage=False), "fig20_age_groups_count")
    return pd.concat([ethnicity.assign(grouping="ethnicity"), age.assign(grouping="age")], ignore_index=True)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-directory", type=Path, default=None, help="also write PNG copies here, for checking")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    plt.rcParams.update(PAPER_STYLE)
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    tables_directory, store = phase_directory(PHASE_NAME), default_result_store()
    figure_directory = tables_directory.parent / FIGURE_DIRECTORY_NAME
    figure_directory.mkdir(parents=True, exist_ok=True)
    if arguments.preview_directory is not None:
        arguments.preview_directory.mkdir(parents=True, exist_ok=True)

    def save(figure, name: str):
        save_figure(figure, figure_directory, name, arguments.preview_directory)

    runs = pd.read_csv(tables_directory / RUN_TABLE_NAME)
    grid = load_noise_grid(FINE_CELL_SIZE_M)
    cell_table = load_cell_table(FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M)
    ethnicity_table = load_cell_ethnicity(FINE_CELL_SIZE_M)
    ethnicity_names = shorten_ethnicity_names(ethnicity_table.attrs["ethnicity_code_to_name"])
    ethnicity_counts = read_group_counts(grid, ethnicity_table)
    example_levels_db = load_drone_levels(store, select_run_key(runs, EXAMPLE_STOCKING, STRAIGHT))
    newly_exposed = find_newly_exposed_cells(example_levels_db, cell_table.baseline_levels_db, HEADLINE_EXPOSURE_THRESHOLD_DB)

    draw_fleet_figures(runs, save)
    draw_map_figures(store, grid, runs, cell_table.baseline_levels_db, save)
    draw_population_figures(grid, align_to_grid(grid, load_cell_population(FINE_CELL_SIZE_M), "population"), ethnicity_counts, ethnicity_names, save)
    group_exposure = draw_group_figures(newly_exposed, grid, ethnicity_counts, ethnicity_names, save)

    navigation_grid = load_navigation_grid(FINE_BASELINE_NOISE_MAP)
    routes = find_example_routes(
        navigation_grid, convert_to_coordinate(ROUTE_START_LONGITUDE_LATITUDE), convert_to_coordinate(ROUTE_END_LONGITUDE_LATITUDE)
    )
    save(plot_route_example(navigation_grid, routes), "fig11_example_routes")

    write_phase_table(group_exposure.assign(git_hash=git_hash), tables_directory, "paper_figure_group_exposure.csv")
    write_phase_table(measure_route_lengths(routes).assign(git_hash=git_hash), tables_directory, "paper_figure_route_lengths.csv")


if __name__ == "__main__":
    main()
