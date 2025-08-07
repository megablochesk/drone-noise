"""Utility functions for rendering bar charts for multiple datasets."""

from typing import List, Tuple

import numpy as np
from matplotlib import pyplot as plt

from .chart_config import DATASET_TYPE_BAR_ORDER, DATASET_TYPE_TO_LEGEND
from .plot_utils import get_color_map, annotate_barchart_data_points


def prepare_barchart_data(results_df) -> Tuple[List[str], List[int], dict]:
    """Return dataset ordering, x axis values and colour map for a bar chart."""
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df["dataset_name"].unique()]
    num_drones_list = sorted(results_df["num_drones"].unique())
    color_map = get_color_map(dataset_types)
    return dataset_types, num_drones_list, color_map


def extract_sorted_values(results_df, dataset_types, num_drones, value_column):
    """Fetch values for a particular number of drones across datasets."""
    ds_values = []
    for ds in DATASET_TYPE_BAR_ORDER:
        if ds in dataset_types:
            row = results_df[(results_df["dataset_name"] == ds) & (results_df["num_drones"] == num_drones)]
            value = row.iloc[0][value_column] if not row.empty else 0
            ds_values.append((ds, value))
    return ds_values


def plot_multiple_datasets_barchart(x, num_drones_list, dataset_types, results_df, value_column, xlabel, ylabel,
                                    color_map, title=None, decimal_places=2, filename=None):
    """Render bar chart for multiple datasets on the same axes."""
    width = 0.27
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.filename = filename
    added_labels = set()

    for i, num_drones in enumerate(num_drones_list):
        ds_values = extract_sorted_values(results_df, dataset_types, num_drones, value_column)
        num_datasets = len(ds_values)

        for j, (ds, value) in enumerate(ds_values):
            bar_position = x[i] - width * (num_datasets - 1) / 2 + j * width
            legend_label = DATASET_TYPE_TO_LEGEND.get(ds, ds)
            label = legend_label if legend_label not in added_labels else ""
            if legend_label not in added_labels:
                added_labels.add(legend_label)

            bar = ax.bar(bar_position, value, width, color=color_map[ds], label=label)
            annotate_barchart_data_points(ax, bar, value, decimal_places)

    ax.set_xticks(x)
    ax.set_xticklabels(num_drones_list)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


def plot_barchart_stats(results_df, value_column, xlabel, ylabel, title=None, decimal_places=2, filename=None):
    """Convenience wrapper to plot dataset statistics on a bar chart."""
    dataset_types, num_drones_list, color_map = prepare_barchart_data(results_df)
    x = np.arange(len(num_drones_list))
    plot_multiple_datasets_barchart(
        x,
        num_drones_list,
        dataset_types,
        results_df,
        value_column,
        xlabel,
        ylabel,
        color_map,
        title,
        decimal_places,
        filename,
    )
