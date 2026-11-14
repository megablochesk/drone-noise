"""Draws one population map per ethnic group; the table is computed first if it is missing."""
from census_analysis.cell_datasets import load_cell_ethnicity
from census_analysis.census_data_heatmap_plotter import draw_group_population_maps
from visualiser import style

FIGURE_DIRECTORY = "figures/ethnicity_pop_maps"
COLOUR_RANGE = (0.0, 1000.0)


def compute_and_visualise_ethnicity_data():
    style.apply_paper_style()
    draw_group_population_maps(load_cell_ethnicity(), "ethnicity", COLOUR_RANGE, FIGURE_DIRECTORY, "Population per cell")
