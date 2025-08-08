import pandas as pd

from visualiser.barchart import plot_barchart_stats
from visualiser.cell_population_calculator import (
    calculate_population_impacted_by_noise,
    CELL_POPULATION,
    get_cells_impacted_by_noise
)
from .plot_utils import plot_standalone_heatmap


def calculate_noise_increase_cells(main_df, threshold: int = 55) -> pd.DataFrame:
    """Return a dataframe of cells where combined noise exceeds a threshold."""
    rows = []
    for _, row in main_df.iterrows():
        noise_impact = row["noise_impact_df"]
        count = ((noise_impact["combined_noise"] > threshold) & (noise_impact["noise_level"] < threshold)).sum()
        rows.append(
            {
                "dataset_name": row["dataset_name"],
                "num_drones": row["num_drones"],
                "cells_exceeding_threshold": count,
            }
        )
    return pd.DataFrame(rows)


def analyze_and_plot_noise_increase(main_df, threshold: int = 55):
    """Plot number of cells where combined noise exceeds ``threshold``."""
    summary_df = calculate_noise_increase_cells(main_df, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column="cells_exceeding_threshold",
        xlabel="Number of Drones",
        ylabel="Number of Cells",
        decimal_places=0,
        filename="del_cel_imp",
    )


def analyze_and_plot_population_impact(main_df, threshold: int = 55):
    """Plot additional population impacted by noise over ``threshold``."""
    summary_df = calculate_population_impacted_by_noise(main_df, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column="impacted_population",
        xlabel="Number of Drones",
        ylabel=f"Extra Population Exposed to Noise over {threshold} dB",
        decimal_places=0,
        filename="del_pop_imp",
    )


def plot_cell_population():
    """Render heatmap of the static cell population grid."""
    population_df = CELL_POPULATION
    metric = "population"
    plot_standalone_heatmap(
        population_df,
        index="row",
        columns="col",
        values=metric,
        vmin=None,
        vmax=None,
        xlabel="Column",
        ylabel="Row",
        filename=metric,
    )


def plot_cells_impacted_by_noise(main_df, threshold: int = 55):
    """Render heatmaps of population cells impacted by noise."""
    df = get_cells_impacted_by_noise(main_df, threshold)
    metric = "population"
    for (dataset_name, num_drones), group_df in df.groupby(["dataset_name", "num_drones"]):
        plot_standalone_heatmap(
            group_df,
            index="row",
            columns="col",
            values=metric,
            vmin=None,
            vmax=None,
            xlabel="Column",
            ylabel="Row",
            filename=f"{metric}_{dataset_name}_{num_drones}",
        )