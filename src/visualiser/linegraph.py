"""Utility functions for rendering line graphs for multiple datasets."""

from matplotlib import pyplot as plt

from .chart_config import DATASET_TYPE_BAR_ORDER
from .plot_utils import get_color_map, plot_multiple_datasets_linegraph


def prepare_linegraph_data(results_df):
    """Return dataset ordering and colour map for a line graph."""
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df["dataset_name"].unique()]
    color_map = get_color_map(dataset_types)
    return dataset_types, color_map


def plot_linegraph(results_df, value_column, xlabel, ylabel, title=""):
    """Plot line graph for a given results dataframe."""
    dataset_types, color_map = prepare_linegraph_data(results_df)
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_multiple_datasets_linegraph(ax, results_df, dataset_types, color_map, value_column)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title="Dataset Type")
    fig.tight_layout()
    return fig
