"""The paper's figures redrawn on the fine-grid design (Round 4 baseline, 100 m cells, 10 s step), as EPS.

Figure numbers follow the submitted paper. Figure 2 (a simulation snapshot on a street map) is not drawn: it
needs map tiles from the internet. Every line, bar and map is the mean over the seeds of the run table (maps
as sound energy). This script only loads and saves; the tables are
in visualiser/figure_tables.py and the drawing in visualiser/draw.py.

Usage (from src/): python -m experiments.revision.paper_figures [--preview-directory DIRECTORY]
"""
import matplotlib

matplotlib.use("Agg")

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity, load_cell_population
from census_analysis.ethnic_group_codes import abbreviate_ethnic_groups
from common.coordinate import Coordinate
from common.model_configs import model_config
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.fine_grid_design import (
    FINE_BASELINE_NOISE_MAP,
    FINE_BOUNDARY_DATUM,
    FINE_CELL_SIZE_M,
    PHASE_NAME,
)
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.result_store import ResultStore, ensure_runs_are_on_grid, load_drone_levels
from experiments.revision.run_executor import HEADLINE_EXPOSURE_THRESHOLD_DB
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from metrics.cell_table import align_to_grid, load_cell_table
from metrics.exposure_metrics import combine_levels_db, find_newly_exposed_cells
from noise.navigator.grid_route_navigator import GridRouteNavigator
from noise.navigator.navigation_grid import NavigationGrid, calculate_mixed_edge_costs
from noise.navigator.navigation_grid_loader import load_navigation_grid
from noise.noise_grid import NoiseGrid, load_noise_grid, to_grid_image
from visualiser import draw, style
from visualiser.figure_tables import (
    average_group_exposure,
    average_levels_db,
    build_grid_image,
    count_seeds,
    find_shared_colour_range,
    measure_route_lengths,
    read_navigation,
    summarise_group_exposure,
    tabulate_metric_by_fleet,
)
from visualiser.save import save_figure

RUN_TABLE_NAME = "paper_figure_runs.csv"
FIGURE_DIRECTORY_NAME = "paper_figures_100m_10s_round4"
FIGURE_FORMATS = ("eps",)
PREVIEW_FORMATS = ("png",)
PREVIEW_DPI = 90

MAPPED_FLEET = 1250
# The scenario the paper uses for its single-run figures: straight routes, random stocking, largest fleet.
EXAMPLE_STOCKING = "random"
MAPPED_NAVIGATIONS = {
    style.STRAIGHT: "fig10_drone_noise_straight", "NOISE_A050": "fig15_drone_noise_alpha_050",
    "NOISE_A100": "fig16_drone_noise_alpha_100",
}
FLEET_FIGURES = (
    (4, "delivered_orders", style.DELIVERIES_LABEL), (6, "mean_noise_increase_db", style.NOISE_INCREASE_LABEL),
    (8, "newly_exposed_population_55db", style.NEWLY_EXPOSED_LABEL),
)
NAVIGATION_FIGURES = (
    ("fig12_delivered_orders_by_navigation", "delivered_orders", "Delivered Orders"),
    ("fig13_mean_noise_increase_by_navigation", "mean_noise_increase_db", style.NOISE_INCREASE_LABEL),
    ("fig14_newly_exposed_by_navigation", "newly_exposed_population_55db", "Newly Exposed Population"),
)
# Figure 11's delivery: from depot DBR1 (Barking) across central London to a customer in Hillingdon, west London,
# 40 km away, where the straight line and the route of every alpha are told apart along most of their length.
ROUTE_START_DEPOT = "DBR1"
ROUTE_END_LONGITUDE_LATITUDE = (-0.415156, 51.536100)
INDIAN_GROUP_NAME = "Indian"
PERCENT = 100.0
HALF_CELL = 0.5


def select_run_keys(runs: pd.DataFrame, stocking: str, navigation: str, terminal_phases: bool = True) -> list[str]:
    """The runs of the largest fleet in one configuration, one per seed, in seed order."""
    selected = runs[
        (runs["number_of_drones"] == MAPPED_FLEET) & (runs["stocking"] == stocking)
        & (runs["terminal_phases"] == terminal_phases) & (read_navigation(runs) == navigation)
    ].sort_values("seed")
    if selected.empty or selected["seed"].duplicated().any():
        raise ValueError(f"Expected one run per seed of {stocking}, {navigation}, found {len(selected)} runs")
    return selected["run_key"].tolist()


def load_levels_of_every_seed(store: ResultStore, runs: pd.DataFrame, stocking: str, navigation: str) -> list[np.ndarray]:
    return [load_drone_levels(store, run_key) for run_key in select_run_keys(runs, stocking, navigation)]


def load_drone_maps(store: ResultStore, grid: NoiseGrid, runs: pd.DataFrame, navigation: str) -> list[np.ndarray]:
    """Drone-only level of the largest fleet as an image, one per stocking."""
    return [
        to_grid_image(grid, average_levels_db(load_levels_of_every_seed(store, runs, stocking, navigation)))
        for stocking in style.STOCKING_MAP_ORDER
    ]


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
    routes = {style.STRAIGHT: (np.array([start.easting, end.easting]), np.array([start.northing, end.northing]))}
    for navigation in style.NAVIGATION_ORDER[1:]:
        edge_costs = calculate_mixed_edge_costs(navigation_grid, style.read_alpha(navigation))
        routes[navigation] = GridRouteNavigator(navigation_grid, edge_costs, []).get_optimal_route_coordinates(start, end)
    return routes


def convert_to_image_coordinates(routes: dict, cell_size_m: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Eastings and northings as fractional columns and rows of the navigation grid's image."""
    boundaries = model_config.map_boundaries
    return {
        navigation: ((eastings - boundaries.left) / cell_size_m - HALF_CELL, (northings - boundaries.bottom) / cell_size_m - HALF_CELL)
        for navigation, (eastings, northings) in routes.items()
    }


def draw_fleet_figures(runs: pd.DataFrame, save):
    """Figures 4-9 and 12-14."""
    for first_figure_number, metric, label in FLEET_FIGURES:
        for offset, terminal_phases in enumerate([False, True]):
            profile = "terminal_phases" if terminal_phases else "cruise_only"
            table = tabulate_metric_by_fleet(runs, metric, terminal_phases, style.STRAIGHT)
            save(draw.plot_stocking_lines(table, label), f"fig{first_figure_number + offset:02d}_{metric}_{profile}")
    for figure_name, metric, label in NAVIGATION_FIGURES:
        tables = {navigation: tabulate_metric_by_fleet(runs, metric, True, navigation) for navigation in style.NAVIGATION_ORDER}
        save(draw.plot_navigation_panels(tables, label), figure_name)


def draw_map_figures(
        store: ResultStore, grid: NoiseGrid, runs: pd.DataFrame, baseline_levels_db: np.ndarray, drone_levels_db: np.ndarray, save,
):
    """Figure 3, and figures 10, 15 and 16 on one colour range so that they can be compared."""
    increases_db = combine_levels_db(baseline_levels_db, drone_levels_db) - baseline_levels_db
    images = [to_grid_image(grid, values) for values in (baseline_levels_db, drone_levels_db, increases_db)]
    colour_ranges = [
        find_shared_colour_range([images[0]], 0.0, 99.9), find_shared_colour_range([images[1]], 1.0, 99.9),
        (0.0, find_shared_colour_range([images[2]], 0.0, 99.9)[1]),
    ]
    labels = [style.NOISE_LEVEL_LABEL, style.NOISE_LEVEL_LABEL, style.NOISE_RISE_LABEL]
    save(draw.plot_map_row(images, ["Base City Noise", "Drone Noise", "City Noise Increase"], colour_ranges, labels), "fig03_noise_maps")

    drone_maps = {navigation: load_drone_maps(store, grid, runs, navigation) for navigation in MAPPED_NAVIGATIONS}
    all_maps = [image for maps in drone_maps.values() for image in maps]
    shared_range = find_shared_colour_range(all_maps, lower_percentile=1.0, upper_percentile=99.9)
    titles = [style.STOCKING_TITLES[stocking] for stocking in style.STOCKING_MAP_ORDER]
    for navigation, figure_name in MAPPED_NAVIGATIONS.items():
        figure = draw.plot_map_row(drone_maps[navigation], titles, [shared_range] * len(titles), [style.NOISE_LEVEL_LABEL] * len(titles))
        save(figure, figure_name)


def draw_population_figures(grid: NoiseGrid, population: np.ndarray, ethnicity_counts: dict, ethnicity_names: dict, save):
    """Figures 1 and 21."""
    population_image = to_grid_image(grid, population)
    save(draw.plot_single_map(population_image, (0.0, np.nanmax(population_image)), "Population per grid cell"), "fig01_population")
    indian_code = next(code for code, name in ethnicity_names.items() if name == INDIAN_GROUP_NAME)
    indian_image = to_grid_image(grid, ethnicity_counts[indian_code])
    indian_range = (0.0, find_shared_colour_range([indian_image], 0.0, 99.9)[1])
    save(draw.plot_single_map(indian_image, indian_range, "Population per cell"), "fig21_indian_population")


def draw_group_figures(
        newly_exposed_by_seed: list[np.ndarray], grid: NoiseGrid, ethnicity_counts: dict, ethnicity_names: dict, save,
) -> pd.DataFrame:
    """Figures 17-20; returns the numbers behind them."""
    age_table = load_cell_age(FINE_CELL_SIZE_M, FINE_BOUNDARY_DATUM)
    age_counts, age_names = read_group_counts(grid, age_table), age_table.attrs["age_code_to_name"]
    ethnicity = average_group_exposure([
        summarise_group_exposure(newly_exposed, ethnicity_counts, ethnicity_names) for newly_exposed in newly_exposed_by_seed
    ])
    ethnicity = ethnicity.assign(label=abbreviate_ethnic_groups(ethnicity["name"].tolist()))
    age = average_group_exposure([
        summarise_group_exposure(newly_exposed, age_counts, age_names) for newly_exposed in newly_exposed_by_seed
    ])
    age = age.assign(label=age["name"])

    by_share = ethnicity.sort_values("share", ascending=False, kind="mergesort")
    by_label = ethnicity.sort_values("label", kind="mergesort")
    age_by_share = age.sort_values("share", ascending=False, kind="mergesort")
    save(draw.plot_group_bars(by_share["share"] * PERCENT, by_share["label"].tolist(), as_percentage=True), "fig17_ethnic_groups_share")
    save(draw.plot_group_bars(by_label["newly_exposed"], by_label["label"].tolist(), as_percentage=False), "fig18_ethnic_groups_count")
    save(draw.plot_group_bars(age_by_share["share"] * PERCENT, age_by_share["label"].tolist(), as_percentage=True), "fig19_age_groups_share")
    save(draw.plot_group_bars(age["newly_exposed"], age["label"].tolist(), as_percentage=False), "fig20_age_groups_count")
    return pd.concat([ethnicity.assign(grouping="ethnicity"), age.assign(grouping="age")], ignore_index=True)


def draw_route_figure(save) -> pd.DataFrame:
    """Figure 11; returns the route lengths."""
    navigation_grid = load_navigation_grid(FINE_BASELINE_NOISE_MAP)
    routes = find_example_routes(
        navigation_grid, model_config.warehouses.bng_coordinates[ROUTE_START_DEPOT], convert_to_coordinate(ROUTE_END_LONGITUDE_LATITUDE)
    )
    image = build_grid_image(navigation_grid.rows, navigation_grid.columns, navigation_grid.noise_levels_db)
    save(draw.plot_route_example(image, convert_to_image_coordinates(routes, navigation_grid.cell_size_m)), "fig11_example_routes")
    return measure_route_lengths(routes)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-directory", type=Path, default=None, help="also write PNG copies here, for checking")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    style.apply_paper_style()
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    tables_directory, store = phase_directory(PHASE_NAME), default_result_store()
    figure_directory = tables_directory.parent / FIGURE_DIRECTORY_NAME

    def save(figure, name: str):
        if arguments.preview_directory is not None:
            figure.savefig(arguments.preview_directory / f"{name}.{PREVIEW_FORMATS[0]}", dpi=PREVIEW_DPI, bbox_inches="tight")
        save_figure(figure, figure_directory, name, FIGURE_FORMATS)

    if arguments.preview_directory is not None:
        arguments.preview_directory.mkdir(parents=True, exist_ok=True)
    runs = pd.read_csv(tables_directory / RUN_TABLE_NAME)
    grid = load_noise_grid(FINE_CELL_SIZE_M, FINE_BOUNDARY_DATUM)
    ensure_runs_are_on_grid(runs, grid)
    cell_table = load_cell_table(FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M, FINE_BOUNDARY_DATUM)
    ethnicity_table = load_cell_ethnicity(FINE_CELL_SIZE_M, FINE_BOUNDARY_DATUM)
    ethnicity_names = shorten_ethnicity_names(ethnicity_table.attrs["ethnicity_code_to_name"])
    ethnicity_counts = read_group_counts(grid, ethnicity_table)
    example_levels_by_seed = load_levels_of_every_seed(store, runs, EXAMPLE_STOCKING, style.STRAIGHT)
    newly_exposed_by_seed = [
        find_newly_exposed_cells(levels_db, cell_table.baseline_levels_db, HEADLINE_EXPOSURE_THRESHOLD_DB)
        for levels_db in example_levels_by_seed
    ]
    population = align_to_grid(grid, load_cell_population(FINE_CELL_SIZE_M, FINE_BOUNDARY_DATUM), "population")

    draw_fleet_figures(runs, save)
    draw_map_figures(store, grid, runs, cell_table.baseline_levels_db, average_levels_db(example_levels_by_seed), save)
    draw_population_figures(grid, population, ethnicity_counts, ethnicity_names, save)
    group_exposure = draw_group_figures(newly_exposed_by_seed, grid, ethnicity_counts, ethnicity_names, save)
    route_lengths = draw_route_figure(save)

    number_of_seeds = count_seeds(runs)
    write_phase_table(
        group_exposure.assign(number_of_seeds=number_of_seeds, git_hash=git_hash), tables_directory, "paper_figure_group_exposure.csv"
    )
    write_phase_table(route_lengths.assign(git_hash=git_hash), tables_directory, "paper_figure_route_lengths.csv")


if __name__ == "__main__":
    main()
