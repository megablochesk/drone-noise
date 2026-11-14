"""The result tables of the paper's experiments (one row per run with a per-cell table inside) read as the
run table and arrays that the figure tables and drawing functions take."""
import numpy as np
import pandas as pd
import pytest

from visualiser.legacy_results import (
    align_group_counts,
    convert_legacy_results,
    find_newly_exposed_cells_of_run,
    format_code_table_as_latex,
    read_cell_image,
)

THRESHOLD_DB = 55.0
POPULATION = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], "population": [10.0, 20.0, 30.0]})


def build_cell_table(combined_levels_db: list[float]) -> pd.DataFrame:
    """Three cells with baselines of 50, 54 and 60 dB; the last one is already above 55 dB."""
    return pd.DataFrame({
        "row": [0, 0, 1], "col": [0, 1, 0], "noise_level": [50.0, 54.0, 60.0], "average_noise": [45.0, 46.0, 47.0],
        "combined_noise": combined_levels_db,
    })


def build_legacy_results() -> pd.DataFrame:
    return pd.DataFrame({
        "dataset_name": ["closest", "furthest"], "num_drones": [100, 100], "navigation_type": ["STRAIGHT", "NOISE_A050"],
        "avg_noise_diff": [0.4, 0.3], "delivered_orders_number": [900, 150], "execution_time_seconds": [12.0, 9.0],
        "noise_impact_df": [build_cell_table([56.0, 54.5, 61.0]), build_cell_table([55.5, 55.5, 61.0])],
    })


def test_runs_get_the_column_names_of_the_revision_run_table():
    runs = convert_legacy_results(build_legacy_results(), terminal_phases=True, population=POPULATION, threshold_db=THRESHOLD_DB)

    assert runs["stocking"].tolist() == ["closest", "furthest"]
    assert runs["number_of_drones"].tolist() == [100, 100]
    assert runs["navigation"].tolist() == ["STRAIGHT", "NOISE_A050"]
    assert runs["terminal_phases"].tolist() == [True, True]
    assert runs["delivered_orders"].tolist() == [900, 150]
    assert runs["mean_noise_increase_db"].tolist() == [0.4, 0.3]
    assert runs["execution_time_s"].tolist() == [12.0, 9.0]


def test_newly_exposed_cells_and_residents_are_counted_per_run():
    """Run 1: only the 50 dB cell rises above 55 dB (10 residents). Run 2: the 50 and 54 dB cells (30).
    The 60 dB cell was above the threshold before the drones and never counts."""
    runs = convert_legacy_results(build_legacy_results(), terminal_phases=True, population=POPULATION, threshold_db=THRESHOLD_DB)

    assert runs["newly_exposed_cells"].tolist() == [1, 2]
    assert runs["newly_exposed_population"].tolist() == [10.0, 30.0]


def test_newly_exposed_cells_need_a_baseline_below_and_a_combined_level_above_the_threshold():
    """Both inequalities are strict, as in the published code."""
    cells = build_cell_table([55.0, 55.01, 61.0])

    assert find_newly_exposed_cells_of_run(cells, THRESHOLD_DB).tolist() == [False, True, False]


def test_a_column_of_the_cell_table_becomes_an_image():
    image = read_cell_image(build_cell_table([56.0, 54.5, 61.0]), "average_noise")

    assert image[0, 0] == 45.0 and image[0, 1] == 46.0 and image[1, 0] == 47.0 and np.isnan(image[1, 1])


def test_group_counts_follow_the_cell_order_of_the_run():
    """The group table lists the cells in another order and has a cell the run does not."""
    groups = pd.DataFrame({"row": [1, 0, 0, 5], "col": [0, 1, 0, 5], 3: [7.0, 8.0, 9.0, 1.0], 4: [0.0, 2.0, 4.0, 1.0]})

    counts = align_group_counts(build_cell_table([56.0, 54.5, 61.0]), groups)

    assert counts[3].tolist() == [9.0, 8.0, 7.0] and counts[4].tolist() == [4.0, 2.0, 0.0]


def test_a_cell_without_group_counts_is_refused():
    groups = pd.DataFrame({"row": [0], "col": [0], 3: [7.0]})

    with pytest.raises(ValueError, match="group table"):
        align_group_counts(build_cell_table([56.0, 54.5, 61.0]), groups)


def test_code_table_is_sorted_by_code_and_escaped_for_latex():
    table = format_code_table_as_latex(["W:BRIT", "A:IND"], ["White: British & Irish", "Asian: Indian"])

    assert table == (
        "\\begin{tabular}{ll}\n\\hline\nCode & Group \\\\\n\\hline\n"
        "A:IND & Asian: Indian \\\\\nW:BRIT & White: British \\& Irish \\\\\n"
        "\\hline\n\\end{tabular}\n"
    )
