"""Shared look of the revision figures: one colour per stocking, readable labels, one legend per figure."""
import math

from matplotlib.ticker import FuncFormatter, PercentFormatter

STOCKING_ORDER = ("closest", "random", "furthest")
STOCKING_LABELS = {"closest": "best", "random": "random", "furthest": "worst"}
STOCKING_COLOURS = {"closest": "tab:blue", "random": "tab:orange", "furthest": "tab:green"}
FLIGHT_PROFILE_LINE_STYLES = {False: "-", True: "--"}
FLIGHT_PROFILE_LABELS = {False: "cruise only", True: "terminal phases"}
METRIC_LABELS = {
    "delivered_orders": "deliveries completed in 10 h",
    "mean_noise_increase_db": "mean noise increase (dB)",
    "newly_exposed_population_55db": "newly exposed population at 55 dB",
    "population_inside_drone_contour_51db": "population inside the 51 dB drone-only contour",
}
THOUSANDS_FORMATTER = FuncFormatter(lambda value, _: f"{value:,.0f}")
MILLIONS_FORMATTER = FuncFormatter(lambda value, _: f"{value / 1e6:g}")
SIGNED_PERCENT_FORMATTER = PercentFormatter(xmax=1.0, decimals=None)
LEGEND_ROW_HEIGHT_FRACTION = 0.045


def describe_series(stocking: str, terminal_phases: bool) -> str:
    return f"{STOCKING_LABELS[stocking]} stocking, {FLIGHT_PROFILE_LABELS[terminal_phases]}"


def describe_variant(variant_name: str) -> str:
    return variant_name.replace("_", " ")


def add_figure_legend(figure, axis, title: str, number_of_columns: int | None = None):
    """One legend above all panels, taken from the series of one panel."""
    handles, labels = axis.get_legend_handles_labels()
    number_of_columns = number_of_columns or len(labels)
    number_of_rows = math.ceil(len(labels) / number_of_columns) + 1
    figure.legend(handles, labels, title=title, loc="upper center", ncol=number_of_columns, frameon=False, fontsize=9)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 1.0 - number_of_rows * LEGEND_ROW_HEIGHT_FRACTION))
