"""The figures of the paper's experiments, drawn from their stored result tables under the published names.

Each function converts a result table with legacy_results.py, builds tables with figure_tables.py, draws with
draw.py and saves with save.py; nothing here computes a metric or styles a figure itself.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from census_analysis.ethnic_group_codes import abbreviate_ethnic_groups, describe_ethnic_group
from visualiser import draw, style
from visualiser.figure_tables import count_cells_by_noise_increase, summarise_group_exposure, tabulate_metric_by_fleet
from visualiser.legacy_results import (
    CELL_TABLE_COLUMN,
    align_group_counts,
    convert_legacy_results,
    find_newly_exposed_cells_of_run,
    format_code_table_as_latex,
    read_cell_image,
)
from visualiser.save import save_figure

EXPOSURE_THRESHOLD_DB = 55.0
PERCENT = 100.0
NOISE_INCREASE_BIN_WIDTH_DB = 0.5
# Colour ranges of the published maps, part of their file names.
SINGLE_RUN_MAP_RANGES = [(40.0, 80.0), (25.0, 55.0), (0.0, 9.0)]
STOCKING_MAP_RANGE = (33.0, 53.0)
MIXED_STOCKING_MAP_RANGE = (25.0, 50.0)
# The published 500 m maps label every fifth row and every sixth column.
PUBLISHED_MAP_TICK_STEPS = (5, 6)
FLEET_FIGURES = (
    ("exec_time", "execution_time_s", "Execution Time, seconds"),
    ("del_noise", "mean_noise_increase_db", style.NOISE_INCREASE_LABEL),
    ("del_orders", "delivered_orders", style.DELIVERIES_LABEL),
    ("del_cel_imp", "newly_exposed_cells", "Number of Cells"),
    ("del_pop_imp", "newly_exposed_population", style.NEWLY_EXPOSED_LABEL),
)
NAVIGATION_FIGURES = (
    ("line_orders_facet_dataset", "delivered_orders", "Delivered Orders"),
    ("line_avg_noise_facet_dataset", "mean_noise_increase_db", style.NOISE_INCREASE_LABEL),
    ("line_impacted_population_facet_dataset_t55", "newly_exposed_population", "Newly Exposed Population"),
)


def save(figure, figure_directory: Path, name: str):
    save_figure(figure, figure_directory, name)


def draw_fleet_experiment_figures(results: pd.DataFrame, figure_directory: Path, population: pd.DataFrame, name_suffix: str = ""):
    """Fleet size against run time, noise increase, deliveries, newly exposed cells and newly exposed residents."""
    runs = convert_legacy_results(results, terminal_phases=True, population=population, threshold_db=EXPOSURE_THRESHOLD_DB)
    for figure_name, metric, label in FLEET_FIGURES:
        table = tabulate_metric_by_fleet(runs, metric, terminal_phases=True, navigation=style.STRAIGHT)
        save(draw.plot_stocking_lines(table, label), figure_directory, f"{figure_name}{name_suffix}")


def draw_navigation_experiment_figures(results: pd.DataFrame, figure_directory: Path, population: pd.DataFrame):
    """Deliveries, noise increase and newly exposed residents per routing, one panel per stocking."""
    runs = convert_legacy_results(results, terminal_phases=True, population=population, threshold_db=EXPOSURE_THRESHOLD_DB)
    navigations = [navigation for navigation in style.NAVIGATION_ORDER if navigation in set(runs["navigation"])]
    for figure_name, metric, label in NAVIGATION_FIGURES:
        tables = {navigation: tabulate_metric_by_fleet(runs, metric, True, navigation) for navigation in navigations}
        save(draw.plot_navigation_panels(tables, label), figure_directory, figure_name)


def name_with_range(figure_name: str, colour_range: tuple[float, float]) -> str:
    return f"{figure_name}_{colour_range[0]:.0f}_{colour_range[1]:.0f}"


def draw_stocking_noise_maps(results: pd.DataFrame, figure_directory: Path):
    """Drone-only level of one fleet under best, random and worst stocking."""
    cell_tables = results.set_index("dataset_name")[CELL_TABLE_COLUMN]
    images = [read_cell_image(cell_tables[stocking], "average_noise") for stocking in style.STOCKING_MAP_ORDER]
    titles = [style.STOCKING_TITLES[stocking] for stocking in style.STOCKING_MAP_ORDER]
    figure = draw.plot_map_row(images, titles, [STOCKING_MAP_RANGE] * len(images), [style.NOISE_LEVEL_LABEL] * len(images), PUBLISHED_MAP_TICK_STEPS)
    save(figure, figure_directory, name_with_range("noise_maps", STOCKING_MAP_RANGE))


def draw_mixed_stocking_noise_maps(results: pd.DataFrame, figure_directory: Path):
    """Drone-only level of every mix of random and best stocking, in the order of the result table."""
    images = [read_cell_image(cell_table, "average_noise") for cell_table in results[CELL_TABLE_COLUMN]]
    figure = draw.plot_map_row(
        images, results["dataset_name"].tolist(), [MIXED_STOCKING_MAP_RANGE] * len(images), [style.NOISE_LEVEL_LABEL] * len(images),
        PUBLISHED_MAP_TICK_STEPS,
    )
    save(figure, figure_directory, name_with_range("mixed_datasets_noise_maps", MIXED_STOCKING_MAP_RANGE))


def draw_noise_maps_of_run(cell_table: pd.DataFrame, figure_directory: Path):
    images = [read_cell_image(cell_table, column) for column in ("noise_level", "average_noise", "noise_difference")]
    labels = [style.NOISE_LEVEL_LABEL, style.NOISE_LEVEL_LABEL, style.NOISE_RISE_LABEL]
    figure = draw.plot_map_row(images, ["Base City Noise", "Drone Noise", "City Noise Increase"], SINGLE_RUN_MAP_RANGES, labels, PUBLISHED_MAP_TICK_STEPS)
    save(figure, figure_directory, name_with_range("noise_level_comparison", SINGLE_RUN_MAP_RANGES[0]))


def draw_group_bars_of_run(
        newly_exposed: np.ndarray, group_counts: dict, group_names: dict, group_codes: dict, figure_directory: Path,
        name_prefix: str, legend_name: str,
):
    """Residents and share of every group in the newly exposed cells, and the legend table of the codes."""
    summary = summarise_group_exposure(newly_exposed, group_counts, group_names)
    summary = summary.assign(label=[group_codes[name] for name in summary["name"]])
    by_share = summary.sort_values("share", ascending=False, kind="mergesort")
    threshold = f"{EXPOSURE_THRESHOLD_DB:.0f}"
    save(draw.plot_group_bars(summary["newly_exposed"], summary["label"].tolist(), False), figure_directory, f"{name_prefix}_abs_{threshold}")
    save(draw.plot_group_bars(by_share["share"] * PERCENT, by_share["label"].tolist(), True), figure_directory, f"{name_prefix}_pct_{threshold}")
    legend_path = Path(figure_directory) / f"{legend_name}_{threshold}.tex"
    legend_path.write_text(format_code_table_as_latex(summary["label"].tolist(), summary["name"].tolist()), encoding="utf-8")


def shorten_census_name(census_name: str) -> str:
    """'Asian, Asian British or Asian Welsh: Indian' -> 'Indian'."""
    return census_name.split(": ", 1)[-1].strip()


def draw_single_run_figures(cell_table: pd.DataFrame, figure_directory: Path, age_groups: pd.DataFrame, ethnic_groups: pd.DataFrame):
    """One run: cells by noise increase, the three noise maps, and exposure by age band and ethnic group."""
    labels, counts = count_cells_by_noise_increase(cell_table["noise_difference"].to_numpy(), NOISE_INCREASE_BIN_WIDTH_DB)
    save(draw.plot_cell_count_bars(labels, counts), figure_directory, "noise_change_barchart")
    draw_noise_maps_of_run(cell_table, figure_directory)

    newly_exposed = find_newly_exposed_cells_of_run(cell_table, EXPOSURE_THRESHOLD_DB)
    age_names = age_groups.attrs["age_code_to_name"]
    draw_group_bars_of_run(
        newly_exposed, align_group_counts(cell_table, age_groups), age_names, {name: name for name in age_names.values()},
        figure_directory, "age_impact", "age_impact_legend",
    )
    short_names = [shorten_census_name(name) for name in ethnic_groups.attrs["ethnicity_code_to_name"].values()]
    ethnic_names = {
        code: describe_ethnic_group(short_name)
        for code, short_name in zip(ethnic_groups.attrs["ethnicity_code_to_name"], short_names)
    }
    ethnic_codes = dict(zip(ethnic_names.values(), abbreviate_ethnic_groups(short_names)))
    draw_group_bars_of_run(
        newly_exposed, align_group_counts(cell_table, ethnic_groups), ethnic_names, ethnic_codes,
        figure_directory, "eth_impact", "ethnicity_impact_legend",
    )
