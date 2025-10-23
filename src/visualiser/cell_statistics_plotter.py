import re

import pandas as pd

from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH, CELL_AGE_PATH, CELL_ETHNICITY_PATH
from visualiser.barchart import plot_barchart_stats, plot_combined_bars
from visualiser.cell_statistics_calculator import (
    calculate_cells_exceeding_threshold,
    calculate_population_impacted_by_noise,
    get_cells_impacted_by_noise_with_population,
    calculate_age_impacted_by_noise,
    calculate_ethnicity_impacted_by_noise,
)
from visualiser.plot_utils import plot_standalone_heatmap
from visualiser.statistics import plot_dataset_stat_difference

CELL_POPULATION = load_dataframe_from_pickle(CELL_POPULATION_PATH)
CELL_AGE = load_dataframe_from_pickle(CELL_AGE_PATH)
CELL_ETHNICITY = load_dataframe_from_pickle(CELL_ETHNICITY_PATH)


def _slug(s) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(s)).strip("_").lower()


def plot_noise_exceedance_combined(main_df: pd.DataFrame, threshold: int = 55, decimals: int = 0, plot_stat_difference: bool = True):
    summary_df = calculate_cells_exceeding_threshold(main_df, threshold)
    if plot_stat_difference:
        plot_dataset_stat_difference(
            summary_df,
            value_col="cells_exceeding_threshold",
            ylabel="% of cells compared to Normal",
            title=f"Average Cells exceeding {threshold} dB",
        )
    return plot_combined_bars(
        summary_df,
        value_column="cells_exceeding_threshold",
        xlabel="Number of Drones",
        ylabel="Number of Cells",
        title=f"Cells exceeding {threshold} dB",
        decimal_places=decimals,
        filename="del_cel_imp",
    )


def plot_population_impact_combined(main_df: pd.DataFrame, threshold: int = 55, plot_stat_difference: bool = True):
    summary_df = calculate_population_impacted_by_noise(main_df, CELL_POPULATION, threshold)
    if plot_stat_difference:
        plot_dataset_stat_difference(
            summary_df,
            value_col="impacted_population",
            ylabel="% population exposure compared to Normal",
            title=f"Average population exposed over {threshold} dB vs Normal",
            filename="del_cel_imp_stat_diff",
        )
    return plot_combined_bars(
        summary_df,
        value_column="impacted_population",
        xlabel="Number of Drones",
        ylabel=f"Extra Population Exposed to Noise over {threshold} dB",
        filename="del_pop_imp_comp",
    )


def analyze_and_plot_age_impact_each_band(main_df: pd.DataFrame, threshold: int = 55, use_band_names: bool = True):
    df = calculate_age_impacted_by_noise(main_df, CELL_AGE, threshold=threshold, use_band_names=use_band_names)
    base = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    for col in [c for c in df.columns if c not in base]:
        plot_barchart_stats(
            df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population ({col}) over {threshold} dB",
            decimal_places=0,
            filename=f"del_age_imp_{_slug(col)}",
        )


def analyze_and_plot_ethnicity_impact_each_group(main_df: pd.DataFrame, threshold: int = 55, use_names: bool = False):
    df = calculate_ethnicity_impacted_by_noise(main_df, CELL_ETHNICITY, threshold=threshold, use_names=use_names)
    base = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    for col in [c for c in df.columns if c not in base]:
        plot_barchart_stats(
            df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population ({col}) over {threshold} dB",
            decimal_places=0,
            filename=f"del_eth_imp_{_slug(col)}",
        )


def plot_age_impact_each_band_combined(main_df: pd.DataFrame, threshold: int = 55, plot_stat_difference: bool = True, use_band_names: bool = True):
    df = calculate_age_impacted_by_noise(main_df, CELL_AGE, threshold=threshold, use_band_names=use_band_names)
    base = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    for col in [c for c in df.columns if c not in base]:
        if plot_stat_difference:
            plot_dataset_stat_difference(
                df,
                value_col=col,
                ylabel="% population exposure compared to Normal",
                title=f"{col}: exposed over {threshold} dB vs Normal",
                filename=f"del_age_imp_stat_diff_{_slug(col)}",
            )
        plot_combined_bars(
            df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population ({col}) over {threshold} dB",
            title=str(col),
            filename=f"del_age_imp_comp_{_slug(col)}",
        )


def plot_ethnicity_impact_each_group_combined(main_df: pd.DataFrame, threshold: int = 55, plot_stat_difference: bool = True, use_names: bool = False):
    df = calculate_ethnicity_impacted_by_noise(main_df, CELL_ETHNICITY, threshold=threshold, use_names=use_names)
    base = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    for col in [c for c in df.columns if c not in base]:
        if plot_stat_difference:
            plot_dataset_stat_difference(
                df,
                value_col=col,
                ylabel="% population exposure compared to Normal",
                title=f"{col}: exposed over {threshold} dB vs Normal",
                filename=f"del_eth_imp_stat_diff_{_slug(col)}",
            )
        plot_combined_bars(
            df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population ({col}) over {threshold} dB",
            title=str(col),
            filename=f"del_eth_imp_comp_{_slug(col)}",
        )


def analyze_and_plot_noise_increase(main_df: pd.DataFrame, threshold: int = 55):
    summary_df = calculate_cells_exceeding_threshold(main_df, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column="cells_exceeding_threshold",
        xlabel="Number of Drones",
        ylabel="Number of Cells",
        decimal_places=0,
        filename="del_cel_imp",
    )


def analyze_and_plot_population_impact(main_df: pd.DataFrame, threshold: int = 55):
    summary_df = calculate_population_impacted_by_noise(main_df, CELL_POPULATION, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column="impacted_population",
        xlabel="Number of Drones",
        ylabel=f"Extra Population Exposed to Noise over {threshold} dB",
        decimal_places=0,
        filename="del_pop_imp",
    )


def analyze_and_plot_age_impact(main_df: pd.DataFrame, threshold: int = 55, use_band_names: bool = True):
    summary_df = calculate_age_impacted_by_noise(main_df, CELL_AGE, threshold=threshold, use_band_names=use_band_names)
    base_cols = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    value_cols = [c for c in summary_df.columns if c not in base_cols]
    for col in value_cols:
        plot_barchart_stats(
            summary_df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population (age band) over {threshold} dB",
            decimal_places=0,
            filename=f"del_age_imp_{_slug(col)}",
        )


def analyze_and_plot_ethnicity_impact(main_df: pd.DataFrame, threshold: int = 55, use_names: bool = False):
    summary_df = calculate_ethnicity_impacted_by_noise(main_df, CELL_ETHNICITY, threshold=threshold, use_names=use_names)
    base_cols = {"dataset", "dataset_name", "num_drones", "navigation_type"}
    value_cols = [c for c in summary_df.columns if c not in base_cols]
    for col in value_cols:
        plot_barchart_stats(
            summary_df,
            value_column=col,
            xlabel="Number of Drones",
            ylabel=f"Extra Population (ethnicity) over {threshold} dB",
            decimal_places=0,
            filename=f"del_eth_imp_{_slug(col)}",
        )


def plot_cells_impacted_by_noise(main_df: pd.DataFrame, threshold: int = 55):
    df = get_cells_impacted_by_noise_with_population(main_df, CELL_POPULATION, threshold)
    metric = "impacted_population"
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
