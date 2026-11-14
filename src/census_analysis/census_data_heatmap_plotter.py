"""Maps of residents per cell: the whole population, or one map per census group."""
from pathlib import Path

import numpy as np
import pandas as pd

from visualiser import draw
from visualiser.figure_tables import build_grid_image
from visualiser.save import save_figure

POPULATION_LABEL = "Population per grid cell"


def read_image(cell_table: pd.DataFrame, column) -> np.ndarray:
    return build_grid_image(cell_table["row"].to_numpy(), cell_table["col"].to_numpy(), cell_table[column].to_numpy())


def draw_population_map(population: pd.DataFrame, figure_directory: Path):
    image = read_image(population, "population")
    save_figure(draw.plot_single_map(image, (0.0, float(np.nanmax(image))), POPULATION_LABEL), figure_directory, "population")


def draw_group_population_maps(
        group_table: pd.DataFrame, data_category: str, colour_range: tuple[float, float], figure_directory: Path,
        colour_bar_label: str,
):
    """One map per group code of the table, named `<category>_<code>_<lowest>_<highest>`."""
    for group_code in sorted(group_table.attrs[f"{data_category}_code_to_name"]):
        figure = draw.plot_single_map(read_image(group_table, group_code), colour_range, colour_bar_label)
        save_figure(figure, figure_directory, f"{data_category}_{group_code}_{colour_range[0]}_{colour_range[1]}")
