"""Drawing functions: each takes prepared tables or images and returns a figure. Nothing is loaded, computed
from runs, or saved here; see figure_tables.py for the tables and save.py for writing files."""
import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib import pyplot as plt
from matplotlib import ticker

from visualiser import style

THOUSAND = 1000
LINE_FIGURE_SIZE = (13, 6)
PANEL_FIGURE_SIZE = (15, 6)
MAP_PANEL_SIZE = (6.5, 5.2)
SINGLE_MAP_SIZE = (8, 6.2)
BAR_FIGURE_WIDTH = 10.5
CELL_COUNT_FIGURE_SIZE = (10, 6)
ROUTE_FIGURE_HEIGHT = 10


def style_value_axis(axis):
    """Dotted horizontal guides behind the data."""
    axis.grid(axis="y", linestyle=":", linewidth=0.7, color=style.GRID_LINE_COLOUR)
    axis.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    axis.grid(axis="y", which="minor", linestyle=":", linewidth=0.4, color=style.MINOR_GRID_LINE_COLOUR)
    axis.set_axisbelow(True)


def format_compact_value(value: float, _position) -> str:
    """1,500 -> 1.5k; values below a thousand as they are."""
    return f"{value / THOUSAND:g}k" if value >= THOUSAND else f"{value:g}"


def plot_stocking_lines(table: pd.DataFrame, value_label: str):
    """One line per stocking against the fleet size; the table has fleets down and stockings across."""
    figure, axis = plt.subplots(figsize=LINE_FIGURE_SIZE)
    for stocking in style.STOCKING_LINE_ORDER:
        axis.plot(
            table.index, table[stocking], marker=style.STOCKING_MARKERS[stocking],
            linestyle=style.STOCKING_LINE_STYLES[stocking], color=style.STOCKING_COLOURS[stocking],
            label=style.STOCKING_LEGEND[stocking], linewidth=2, markersize=6,
        )
    axis.set_xlabel(style.FLEET_LABEL)
    axis.set_ylabel(value_label)
    axis.set_xticks(table.index)
    axis.legend(title=style.LEGEND_TITLE, frameon=True, edgecolor="black", fancybox=False)
    style_value_axis(axis)
    figure.tight_layout()
    return figure


def plot_navigation_panels(tables: dict[str, pd.DataFrame], value_label: str):
    """One panel per stocking and one line per routing; `tables` maps a routing to its fleet x stocking table."""
    figure, axes = plt.subplots(1, len(style.STOCKING_PANEL_ORDER), figsize=PANEL_FIGURE_SIZE, sharey=True)
    for axis, stocking in zip(axes, style.STOCKING_PANEL_ORDER):
        for navigation, table in tables.items():
            axis.plot(
                table.index, table[stocking], marker=style.NAVIGATION_MARKERS[navigation],
                linestyle=style.NAVIGATION_LINE_STYLES[navigation], color=style.NAVIGATION_COLOURS[navigation],
                linewidth=2, markersize=6, label=style.describe_navigation(navigation),
            )
        axis.set_title(style.STOCKING_TITLES[stocking])
        axis.set_xlabel(style.FLEET_LABEL)
        axis.set_xticks(next(iter(tables.values())).index)
        axis.tick_params(axis="x", labelsize=9)
        axis.tick_params(axis="y", labelleft=True)
        axis.yaxis.set_major_locator(ticker.MaxNLocator(nbins=8))
        axis.yaxis.set_major_formatter(ticker.FuncFormatter(format_compact_value))
        style_value_axis(axis)
    axes[0].set_ylabel(value_label)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, fontsize=11)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    return figure


def draw_map(axis, image: np.ndarray, colour_range: tuple[float, float], colour_bar_label: str):
    """A [row, column] image with square cells, row 0 at the bottom; cells without a value stay blank."""
    colour_map = plt.get_cmap(style.COLOUR_MAP).copy()
    colour_map.set_bad(style.OUTSIDE_STUDY_AREA_COLOUR)
    drawn = axis.imshow(
        np.ma.masked_invalid(image), origin="lower", cmap=colour_map, vmin=colour_range[0], vmax=colour_range[1],
        interpolation="nearest",
    )
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.figure.colorbar(drawn, ax=axis, fraction=0.04, pad=0.03, label=colour_bar_label)


def plot_map_row(images: list[np.ndarray], titles: list[str], colour_ranges: list[tuple[float, float]], labels: list[str]):
    """Maps side by side, each with its title, colour range and colour bar."""
    figure, axes = plt.subplots(1, len(images), figsize=(MAP_PANEL_SIZE[0] * len(images), MAP_PANEL_SIZE[1]))
    for axis, image, title, colour_range, label in zip(np.atleast_1d(axes), images, titles, colour_ranges, labels):
        draw_map(axis, image, colour_range, label)
        axis.set_title(title)
    figure.tight_layout()
    return figure


def plot_single_map(image: np.ndarray, colour_range: tuple[float, float], colour_bar_label: str):
    figure, axis = plt.subplots(figsize=SINGLE_MAP_SIZE)
    draw_map(axis, image, colour_range, colour_bar_label)
    axis.set_xlabel("Grid Column")
    axis.set_ylabel("Grid Row")
    figure.tight_layout()
    return figure


def plot_group_bars(values: list[float], labels: list[str], as_percentage: bool):
    """One horizontal bar per group, top to bottom in the order given, with its value written at its end."""
    values = np.asarray(values, dtype=float)
    positions = np.arange(len(values))
    figure, axis = plt.subplots(figsize=(BAR_FIGURE_WIDTH, max(3.8, 0.28 * len(values) + 1.2)))
    axis.barh(positions, values, height=0.75)
    axis.set_yticks(positions, labels)
    axis.invert_yaxis()
    axis.tick_params(axis="y", labelsize=11)
    value_format = "{x:,.2f}%" if as_percentage else "{x:,.0f}"
    axis.xaxis.set_major_formatter(ticker.StrMethodFormatter(value_format))
    axis.grid(axis="x", linestyle="--", color=style.GRID_LINE_COLOUR)
    axis.set_axisbelow(True)
    largest_value = values.max() if len(values) else 0.0
    for position, value in zip(positions, values):
        if value > 0:
            axis.text(value + 0.01 * largest_value, position, value_format.format(x=value), va="center", ha="left", fontsize=11)
    if largest_value > 0:
        axis.set_xlim(right=largest_value * 1.12)
    figure.tight_layout()
    return figure


def plot_cell_count_bars(bin_labels: list[str], cell_counts: list[int]):
    """Number of cells per bin of the noise increase."""
    figure, axis = plt.subplots(figsize=CELL_COUNT_FIGURE_SIZE)
    bars = axis.bar(bin_labels, cell_counts, color=style.BAR_COLOUR, edgecolor="black")
    axis.bar_label(bars, fmt="{:,.0f}")
    axis.set_title("Number of Cells by Noise Level Difference")
    axis.set_xlabel("Noise Difference, dBs")
    axis.set_ylabel("Number of Cells")
    axis.grid(axis="y", linestyle="--", color=style.GRID_LINE_COLOUR)
    axis.set_axisbelow(True)
    axis.set_xticks(range(len(bin_labels)), bin_labels, rotation=45, ha="right")
    figure.tight_layout()
    return figure


def plot_route_example(image: np.ndarray, routes: dict[str, tuple[np.ndarray, np.ndarray]]):
    """Routes over a noise map. Each route is (columns, rows) in image coordinates; the straight route's two
    points mark the start and the end."""
    figure, axis = plt.subplots(figsize=(ROUTE_FIGURE_HEIGHT * image.shape[1] / image.shape[0], ROUTE_FIGURE_HEIGHT))
    drawn = axis.imshow(image, origin="lower", cmap=style.COLOUR_MAP, interpolation="nearest")
    axis.axis("off")
    for navigation, (columns, rows) in routes.items():
        route_style = style.ROUTE_STYLES[navigation]
        label = style.STRAIGHT_ROUTE_LABEL if navigation == style.STRAIGHT else style.describe_navigation(navigation)
        line = axis.plot(columns, rows, label=label, **route_style)[0]
        line.set_path_effects([
            patheffects.Stroke(linewidth=route_style["linewidth"] + style.ROUTE_OUTLINE_EXTRA_WIDTH, foreground="black"),
            patheffects.Normal(),
        ])
    start_and_end_columns, start_and_end_rows = routes[style.STRAIGHT]
    axis.scatter(start_and_end_columns[:1], start_and_end_rows[:1], marker="o", s=70, color="white", edgecolor="black", zorder=6, label="Start")
    axis.scatter(start_and_end_columns[1:], start_and_end_rows[1:], marker="X", s=90, color="white", edgecolor="black", zorder=6, label="End")
    axis.legend(loc="upper left", frameon=True, facecolor="white", framealpha=1.0)
    figure.colorbar(drawn, ax=axis, fraction=0.035, pad=0.01, label=style.NOISE_LEVEL_LABEL)
    figure.tight_layout()
    return figure
