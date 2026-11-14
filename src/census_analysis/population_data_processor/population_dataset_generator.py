"""Draws the population map (Figure 1 of the paper); the table is computed first if it is missing."""
from census_analysis.cell_datasets import load_cell_population
from census_analysis.census_data_heatmap_plotter import draw_population_map
from visualiser import style

FIGURE_DIRECTORY = "figures"


def compute_and_visualise_population_data():
    style.apply_paper_style()
    draw_population_map(load_cell_population(), FIGURE_DIRECTORY)
