from __future__ import annotations

import re
from typing import Iterable

import matplotlib
import pandas as pd
from matplotlib import pyplot as plt

from common.file_utils import load_dataframe_from_pickle
from common.path_configs import PATH_CONFIGS, CELL_POPULATION_PATH
from visualiser.cell_statistics_calculator import calculate_population_impacted_by_noise

matplotlib.use(PATH_CONFIGS.matplotlib_backend)


_DATASET_LABEL = {
    "furthest": "Worst Stocking",
    "closest": "Best Stocking",
    "random": "Random Stocking"
}

_DATASET_STYLE = {
    "furthest": ("-", None),
    "random": ("--", None),
    "closest": (":", None),
}


def plot_impacted_population_lines(
    results_df: pd.DataFrame,
    *,
    threshold: int = 55,
    aggregation_method: str = "mean",
    filename_prefix: str = "line_impacted_population",
):
    population_df = load_dataframe_from_pickle(CELL_POPULATION_PATH)
    summary_df = calculate_population_impacted_by_noise(results_df, population_df, threshold=threshold)

    series_df = _aggregate_metric(summary_df, value_col="impacted_population", aggregation_method=aggregation_method)

    plot_metric_lines_facet_by_dataset(
        series_df,
        "impacted_population",
        ylabel=f"Extra population exposed over {threshold} dB",
        #title=f"Impacted population vs drones — faceted by dataset (>{threshold} dB)",
        filename=f"{filename_prefix}_facet_dataset_t{threshold}",
    )


def plot_average_noise_lines_facet(df: pd.DataFrame):
    plot_metric_lines_facet_by_dataset(
        df,
        "avg_noise_diff",
        ylabel="Average Noise Increase (dB)",
        #title="Average noise vs drones — navigation types (faceted by dataset)",
        filename="line_avg_noise_facet_dataset",
    )


def plot_delivered_orders_lines_facet(df: pd.DataFrame):
    plot_metric_lines_facet_by_dataset(
        df,
        "delivered_orders_number",
        ylabel="Delivered orders",
        #title="Delivered orders vs drones — navigation types (faceted by dataset)",
        filename="line_orders_facet_dataset",
    )


def _aggregate_metric(df: pd.DataFrame, *, value_col: str, aggregation_method: str) -> pd.DataFrame:
    keys = ["dataset_name", "dataset", "navigation_type", "num_drones"]
    x = df.copy()

    if aggregation_method == "median":
        out = x.groupby(keys, as_index=False)[value_col].median()
    else:
        out = x.groupby(keys, as_index=False)[value_col].mean()

    return out


def plot_metric_lines_facet_by_dataset(
    df: pd.DataFrame,
    value_col: str,
    *,
    dataset_col: str = "dataset_name",
    nav_col: str = "navigation_type",
    x_col: str = "num_drones",
    title: str | None = None,
    ylabel: str | None = None,
    xlabel: str = "Number of Drones",
    filename: str | None = None,
):
    ds_order = _dataset_order(df[dataset_col].unique())
    nav_order = _nav_order(df[nav_col].unique())
    nav_colors = _nav_color_map(nav_order)

    fig, axes = plt.subplots(1, len(ds_order), figsize=(5 * len(ds_order), 4), sharey=True)
    if len(ds_order) == 1:
        axes = [axes]

    fig.filename = filename or f"lines_{value_col}_facet_dataset"

    for ax, ds in zip(axes, ds_order):
        sub = df[df[dataset_col] == ds]
        _plot_lines_for_nav(ax, sub, value_col, x_col, nav_col, nav_order, nav_colors, label_on=True)
        _format_axis(ax, x=sub[x_col], xlabel=xlabel, ylabel=ylabel, title=_dataset_label(ds))

    _add_figure_legend(fig, axes[0])

    if title:
        fig.suptitle(title, y=1.04)

    top = 0.86 if title else 0.88
    fig.tight_layout(rect=[0, 0, 1, top])

    return fig, axes


def _plot_lines_for_nav(ax, sub, value_col, x_col, nav_col, nav_order, nav_colors, label_on: bool):
    for nav in nav_order:
        s = sub[sub[nav_col] == nav].sort_values(x_col)
        if s.empty:
            continue
        ax.plot(
            s[x_col],
            s[value_col],
            marker="o",
            linewidth=2,
            color=nav_colors[nav],
            label=_nav_label(nav) if label_on else None,
        )


def _format_axis(ax, *, x, xlabel, ylabel, title):
    xs = sorted(pd.Series(x).dropna().unique().tolist())
    ax.set_xticks(xs)
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)


def _add_figure_legend(
    fig,
    ax,
    *,
    fontsize: int = 13,
    title: str | None = None,
    title_fontsize: int = 14,
    ncol: int | None = None,
):
    handles, labels = ax.get_legend_handles_labels()
    labels = [l for l in labels if l]
    if not labels:
        return None

    if ncol is None:
        ncol = min(len(labels), 5)

    legend = fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=ncol,
        frameon=False,
        fontsize=fontsize,
        title=title,
        title_fontsize=title_fontsize,
    )
    return legend


def _dataset_order(values: Iterable[str]) -> list[str]:
    v = list(map(str, values))
    preferred = ["furthest", "random", "closest"]
    return _ordered(v, preferred)


def _nav_order(values: Iterable[str]) -> list[str]:
    v = list(map(str, values))

    def key(name: str):
        if name == "STRAIGHT":
            return (0, 0.0, name)
        a = _alpha(name)
        if a is not None:
            return (1, a, name)
        return (2, 999.0, name)

    return sorted(v, key=key)


def _nav_color_map(nav_order: list[str]) -> dict[str, object]:
    cmap = plt.get_cmap("tab10")
    return {nav: cmap(i % 10) for i, nav in enumerate(nav_order)}


def _dataset_label(ds: str) -> str:
    return _DATASET_LABEL.get(ds, ds)


def _nav_label(name: str) -> str:
    if name == "STRAIGHT":
        return "Straight"
    a = _alpha(name)
    if a is None:
        return name.replace("_", " ").title()
    base = name.split("_A", 1)[0].replace("_", " ").title()
    return f"{base} α={a:.2f}"


def _alpha(name: str) -> float | None:
    m = re.search(r"_A(\d+)$", str(name))
    if not m:
        return None
    return int(m.group(1)) / 100.0


def _ordered(values: list[str], preferred: list[str]) -> list[str]:
    out = [x for x in preferred if x in values]
    tail = sorted([x for x in values if x not in out])
    return out + tail
