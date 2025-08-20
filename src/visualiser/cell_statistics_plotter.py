import pandas as pd

from visualiser.barchart import plot_barchart_stats, plot_combined_bars
from visualiser.cell_statistics_calculator import (
    calculate_population_impacted_by_noise,
    CELL_POPULATION,
    get_cells_impacted_by_noise, calculate_noise_increase_cells
)
from visualiser.plot_utils import plot_standalone_heatmap
from visualiser.statistics import plot_dataset_stat_difference


def plot_noise_exceedance_combined(main_df: pd.DataFrame, threshold = 55, decimals: int = 0, plot_stat_difference=True):
    summary_df = calculate_noise_increase_cells(main_df, threshold)

    if plot_stat_difference:
        plot_dataset_stat_difference(
            summary_df,
            value_col="cells_exceeding_threshold",
            ylabel="% of cells compared to Normal",
            title="Average Cells exceeding {threshold} dB",

        )

    return plot_combined_bars(
        summary_df,
        value_column="cells_exceeding_threshold",
        xlabel="Number of Drones",
        ylabel="Number of Cells",
        title=f"Cells exceeding {threshold} dB",
        decimal_places=decimals,
        filename="del_cel_imp"
    )


def plot_population_impact_combined(main_df, threshold: int = 55, plot_stat_difference=True):
    summary_df = calculate_population_impacted_by_noise(main_df, threshold)

    if plot_stat_difference:
        plot_dataset_stat_difference(
            summary_df,
            value_col="impacted_population",
            ylabel="% population exposure compared to Normal",
            title="Average Noise Difference to Normal",
            filename = "del_cel_imp_stat_diff",
        )

    return plot_combined_bars(
        summary_df,
        value_column="impacted_population",
        xlabel="Number of Drones",
        ylabel=f"Extra Population Exposed to Noise over {threshold} dB",
        filename="del_pop_imp_comp"
    )


def analyze_and_plot_noise_increase(main_df, threshold: int = 55):
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
