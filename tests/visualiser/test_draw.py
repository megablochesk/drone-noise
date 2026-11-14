"""Smoke tests of the drawing functions: each returns a figure with the expected panels, series and labels."""
import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from matplotlib import pyplot as plt

from visualiser import draw, style
from visualiser.save import save_figure

FLEETS = [100, 500, 1250]


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def build_fleet_table(scale: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame(
        {"closest": [10.0, 50.0, 120.0], "random": [4.0, 20.0, 50.0], "furthest": [2.0, 10.0, 25.0]}, index=FLEETS
    ) * scale


def test_stocking_lines_draw_one_labelled_line_per_stocking():
    figure = draw.plot_stocking_lines(build_fleet_table(), "Number of Delivered Orders")
    axis = figure.axes[0]

    assert [line.get_label() for line in axis.get_lines()] == ["worst-case stocking", "best-case stocking", "random stocking"]
    assert axis.get_lines()[0].get_ydata().tolist() == [2.0, 10.0, 25.0]
    assert axis.get_xticks().tolist() == FLEETS
    assert (axis.get_xlabel(), axis.get_ylabel()) == ("Number of Drones", "Number of Delivered Orders")
    assert axis.get_legend().get_title().get_text() == "Warehouse Stock Conditions"


def test_navigation_panels_draw_one_panel_per_stocking_and_one_line_per_routing():
    tables = {navigation: build_fleet_table(1.0 - 0.1 * position) for position, navigation in enumerate(style.NAVIGATION_ORDER)}

    figure = draw.plot_navigation_panels(tables, "Delivered Orders")

    assert [axis.get_title() for axis in figure.axes] == ["Worst Stocking", "Random Stocking", "Best Stocking"]
    assert all(len(axis.get_lines()) == 5 for axis in figure.axes)
    assert [text.get_text() for text in figure.legends[0].get_texts()][:2] == ["Straight", "Mixed (α=0.25)"]
    assert figure.axes[0].get_ylabel() == "Delivered Orders"


def test_map_row_draws_one_map_with_its_colour_bar_per_image():
    images = [np.array([[1.0, np.nan], [3.0, 4.0]]), np.array([[2.0, 2.0], [np.nan, 5.0]])]

    figure = draw.plot_map_row(images, ["First", "Second"], [(1.0, 4.0), (2.0, 5.0)], ["Level (dB)", "Rise (dB)"])
    maps = [axis for axis in figure.axes if axis.get_title()]

    assert [axis.get_title() for axis in maps] == ["First", "Second"]
    assert len(figure.axes) == 4
    assert maps[1].images[0].get_clim() == (2.0, 5.0)


def test_single_map_has_axis_names_and_a_colour_bar():
    figure = draw.plot_single_map(np.array([[0.0, 10.0], [20.0, np.nan]]), (0.0, 20.0), "Population per grid cell")

    assert (figure.axes[0].get_xlabel(), figure.axes[0].get_ylabel()) == ("Grid Column", "Grid Row")
    assert figure.axes[1].get_ylabel() == "Population per grid cell"


def test_group_bars_write_each_value_at_the_end_of_its_bar():
    figure = draw.plot_group_bars([0.5, 0.25], ["A:IND", "W:BRIT"], as_percentage=True)
    axis = figure.axes[0]

    assert [label.get_text() for label in axis.get_yticklabels()] == ["A:IND", "W:BRIT"]
    assert [text.get_text() for text in axis.texts] == ["0.50%", "0.25%"]


def test_cell_count_bars_label_every_bin():
    figure = draw.plot_cell_count_bars(["0.0 - 0.5", "0.5 - 1.0"], [12, 3])
    axis = figure.axes[0]

    assert [label.get_text() for label in axis.get_xticklabels()] == ["0.0 - 0.5", "0.5 - 1.0"]
    assert (axis.get_xlabel(), axis.get_ylabel()) == ("Noise Difference, dBs", "Number of Cells")


def test_route_example_draws_every_route_with_its_ends():
    image = np.full((4, 6), 50.0)
    routes = {
        "STRAIGHT": (np.array([0.0, 5.0]), np.array([0.0, 3.0])),
        "NOISE_A100": (np.array([0.0, 5.0, 5.0]), np.array([0.0, 0.0, 3.0])),
    }

    figure = draw.plot_route_example(image, routes)
    labels = [text.get_text() for text in figure.axes[0].get_legend().get_texts()]

    assert labels == ["Distance", "Mixed (α=1.00)", "Start", "End"]


def test_a_saved_figure_is_written_in_every_format_and_closed(tmp_path):
    figure = draw.plot_stocking_lines(build_fleet_table(), "Number of Delivered Orders")

    paths = save_figure(figure, tmp_path / "figures", "deliveries", formats=("eps", "png"))

    assert [path.name for path in paths] == ["deliveries.eps", "deliveries.png"]
    assert all(path.stat().st_size > 0 for path in paths)
    assert not plt.fignum_exists(figure.number)
