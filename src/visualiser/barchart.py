from __future__ import annotations

from typing import Sequence, Mapping

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from visualiser.plot_utils import get_color_map

DATASET_TYPE_BAR_ORDER = ["furthest", "closest", "random"]

DATASET_TYPE_TO_LEGEND = {
    "furthest": "worst",
    "closest": "best",
    "random": "random",
}


def plot_barchart_stats(results_df, value_column, xlabel, ylabel, title=None, decimal_places=2, filename=None):
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df["dataset_name"].unique()]
    num_drones_list = sorted(results_df["num_drones"].unique())
    color_map = get_color_map(dataset_types)

    plot_multi_dataset_barchart(
        num_drones=num_drones_list,
        dataset_order=dataset_types,
        results=results_df,
        value_column=value_column,
        xlabel=xlabel,
        ylabel=ylabel,
        color_map=color_map,
        title=title,
        decimals=decimal_places,
        filename=filename,
    )


def plot_multi_dataset_barchart(
        *,
        num_drones: Sequence[int],
        dataset_order: Sequence[str],
        results: pd.DataFrame,
        value_column: str,
        color_map: Mapping[str, str],
        xlabel: str,
        ylabel: str,
        title: str | None = None,
        bar_width: float = 0.27,
        decimals: int = 2,
        filename: str | None = None,
) -> plt.Figure:
    x_positions = np.arange(len(num_drones))
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.filename = filename

    legend_added: set[str] = set()

    for idx, drones in enumerate(num_drones):
        values = _values_for_datasets(results, dataset_order, value_column)
        n_sets = len(values)

        for j, (ds, val) in enumerate(values):
            offset = x_positions[idx] - bar_width * (n_sets - 1) / 2 + j * bar_width
            legend_label = DATASET_TYPE_TO_LEGEND.get(ds, ds)
            label = legend_label if legend_label not in legend_added else ""
            legend_added.add(legend_label)

            bars = ax.bar(offset, val, bar_width, color=color_map[ds], label=label)
            _annotate_barchart_data_points(ax, bars, val, decimals)

    ax.set_xticks(x_positions)
    ax.set_xticklabels(num_drones)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or "")
    ax.legend(title="Dataset type")
    fig.tight_layout()
    return fig


def _values_for_datasets(df: pd.DataFrame, datasets: Sequence[str], value_col: str) -> list[tuple[str, float]]:
    results: list[tuple[str, float]] = []

    for ds in datasets:
        row = df.query("dataset_name == @ds and num_drones == @drones")
        value = 0 if row.empty else row.iloc[0][value_col]
        results.append((ds, value))

    return results


def _annotate_barchart_data_points(ax, bar, value, decimal_places=2, offset=2):
    ax.annotate(
        f'{value:.{decimal_places}f}' if isinstance(value, (float, int)) else f'{value}',
        xy=(bar[0].get_x() + bar[0].get_width() / 2, value),
        xytext=(0, offset),
        textcoords="offset points",
        ha='center',
        va='bottom',
        fontsize=14
    )
