"""The figures of each of the paper's experiments are written under their published file names."""
import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from matplotlib import pyplot as plt

from visualiser import paper_experiment_figures as figures

FLEETS = [100, 250]
STOCKINGS = ["closest", "random", "furthest"]
POPULATION = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], "population": [10.0, 20.0, 30.0]})
AGE_GROUPS = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], 0: [4.0, 8.0, 12.0], 1: [6.0, 12.0, 18.0]})
AGE_GROUPS.attrs["age_code_to_name"] = {0: "0–15", 1: "16–24"}
ETHNIC_GROUPS = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], 3: [1.0, 2.0, 3.0], 13: [9.0, 18.0, 27.0]})
ETHNIC_GROUPS.attrs["ethnicity_code_to_name"] = {
    3: "Asian, Asian British or Asian Welsh: Indian", 13: "White: English, Welsh, Scottish, Northern Irish or British",
}


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def build_cell_table(drone_level_db: float) -> pd.DataFrame:
    baseline = np.array([50.0, 54.0, 60.0])
    combined = 10.0 * np.log10(10.0 ** (baseline / 10.0) + 10.0 ** (drone_level_db / 10.0))
    return pd.DataFrame({
        "row": [0, 0, 1], "col": [0, 1, 0], "noise_level": baseline, "average_noise": drone_level_db,
        "combined_noise": combined, "noise_difference": combined - baseline,
    })


def build_results(navigations: list[str]) -> pd.DataFrame:
    rows = [
        {
            "dataset_name": stocking, "num_drones": fleet, "navigation_type": navigation,
            "avg_noise_diff": 0.001 * fleet, "delivered_orders_number": 10 * fleet, "execution_time_seconds": 0.1 * fleet,
            "noise_impact_df": build_cell_table(drone_level_db=53.0 + position),
        }
        for navigation in navigations for position, stocking in enumerate(STOCKINGS) for fleet in FLEETS
    ]
    return pd.DataFrame(rows)


def list_files(directory) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


def test_fleet_experiment_writes_its_five_line_figures(tmp_path):
    figures.draw_fleet_experiment_figures(build_results(["STRAIGHT"]), tmp_path, POPULATION, name_suffix="_landing")

    assert list_files(tmp_path) == [
        "del_cel_imp_landing.eps", "del_noise_landing.eps", "del_orders_landing.eps", "del_pop_imp_landing.eps",
        "exec_time_landing.eps",
    ]


def test_navigation_experiment_writes_its_three_panel_figures(tmp_path):
    results = build_results(["STRAIGHT", "NOISE_A025", "NOISE_A050", "NOISE_A075", "NOISE_A100"])

    figures.draw_navigation_experiment_figures(results, tmp_path, POPULATION)

    assert list_files(tmp_path) == [
        "line_avg_noise_facet_dataset.eps", "line_impacted_population_facet_dataset_t55.eps", "line_orders_facet_dataset.eps",
    ]


def test_stocking_maps_are_written_under_the_name_with_their_colour_range(tmp_path):
    results = build_results(["STRAIGHT"])

    figures.draw_stocking_noise_maps(results[results["num_drones"] == 250], tmp_path)

    assert list_files(tmp_path) == ["noise_maps_33_53.eps"]


def test_single_run_writes_maps_bars_and_the_code_tables(tmp_path):
    cell_table = build_cell_table(drone_level_db=54.0)

    figures.draw_single_run_figures(cell_table, tmp_path, AGE_GROUPS, ETHNIC_GROUPS)

    assert list_files(tmp_path) == [
        "age_impact_abs_55.eps", "age_impact_legend_55.tex", "age_impact_pct_55.eps", "eth_impact_abs_55.eps",
        "eth_impact_pct_55.eps", "ethnicity_impact_legend_55.tex", "noise_change_barchart.eps",
        "noise_level_comparison_40_80.eps",
    ]
    assert "A:IND & Asian: Indian" in (tmp_path / "ethnicity_impact_legend_55.tex").read_text(encoding="utf-8")
