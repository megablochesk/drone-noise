"""The one set of styles for every figure: colours, marks, names and text sizes of the submitted paper."""
import re

from matplotlib import pyplot as plt

STRAIGHT = "STRAIGHT"
NAVIGATION_ORDER = (STRAIGHT, "NOISE_A025", "NOISE_A050", "NOISE_A075", "NOISE_A100")

# Order of the lines in a legend, of the panels of a figure by routing, and of the maps of a figure.
STOCKING_LINE_ORDER = ("furthest", "closest", "random")
STOCKING_PANEL_ORDER = ("furthest", "random", "closest")
STOCKING_MAP_ORDER = ("closest", "random", "furthest")
STOCKING_LEGEND = {"furthest": "worst-case stocking", "closest": "best-case stocking", "random": "random stocking"}
STOCKING_TITLES = {"furthest": "Worst Stocking", "random": "Random Stocking", "closest": "Best Stocking"}
STOCKING_COLOURS = {stocking: plt.get_cmap("tab10")(position) for position, stocking in enumerate(STOCKING_LINE_ORDER)}
STOCKING_LINE_STYLES = {"furthest": "-", "closest": "--", "random": ":"}
STOCKING_MARKERS = {"furthest": "o", "closest": "s", "random": "^"}

NAVIGATION_COLOURS = {navigation: plt.get_cmap("tab10")(position) for position, navigation in enumerate(NAVIGATION_ORDER)}
NAVIGATION_LINE_STYLES = {STRAIGHT: "-", "NOISE_A025": "--", "NOISE_A050": ":", "NOISE_A075": "-.", "NOISE_A100": "-"}
NAVIGATION_MARKERS = {STRAIGHT: "o", "NOISE_A025": "s", "NOISE_A050": "^", "NOISE_A075": "D", "NOISE_A100": "x"}
# Dashes of equal length and gap, the second set shifted by one dash: where two routes are the same cells
# (alpha 0.25 and 0.50 often are) the line alternates between their colours instead of hiding one.
ROUTE_DASH_LENGTH = 4
ROUTE_DASHES = (ROUTE_DASH_LENGTH, ROUTE_DASH_LENGTH)
ROUTE_STYLES = {
    STRAIGHT: dict(color="#FFFFFF", linewidth=2.2, linestyle="-", zorder=5),
    "NOISE_A025": dict(color="#FF00FF", linewidth=2.4, linestyle=(0, ROUTE_DASHES), zorder=2),
    "NOISE_A050": dict(color="#00E5FF", linewidth=2.4, linestyle=(ROUTE_DASH_LENGTH, ROUTE_DASHES), zorder=4),
    "NOISE_A075": dict(color="#FF7F0E", linewidth=2.6, linestyle="--", zorder=3),
    "NOISE_A100": dict(color="#FF0000", linewidth=2.6, linestyle="-", zorder=1),
}
ROUTE_OUTLINE_EXTRA_WIDTH = 0.8
STRAIGHT_ROUTE_LABEL = "Distance"

# EPS has no transparency, so guide lines are light greys instead of translucent black.
GRID_LINE_COLOUR = "#c8c8c8"
MINOR_GRID_LINE_COLOUR = "#e4e4e4"
COLOUR_MAP = "viridis"
OUTSIDE_STUDY_AREA_COLOUR = "white"
BAR_COLOUR = "skyblue"

LEGEND_TITLE = "Warehouse Stock Conditions"
FLEET_LABEL = "Number of Drones"
DELIVERIES_LABEL = "Number of Delivered Orders"
NOISE_INCREASE_LABEL = "Average Noise Increase (dB)"
NEWLY_EXPOSED_LABEL = "Extra Population Exposed to Noise over 55 dB"
NOISE_LEVEL_LABEL = "Noise level (dB)"
NOISE_RISE_LABEL = "Noise increase (dB)"

PAPER_STYLE = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 15,
    "axes.titlesize": 15,
    "axes.labelsize": 15,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 15,
    "legend.title_fontsize": 15,
    "figure.titlesize": 15,
}


def apply_paper_style():
    """Text of the submitted figures; called by the scripts that draw, never at import."""
    plt.rcParams.update(PAPER_STYLE)


def describe_navigation(navigation: str) -> str:
    alpha = re.search(r"_A(\d+)$", navigation)
    return f"Mixed (α={int(alpha.group(1)) / 100:.2f})" if alpha else "Straight"


def read_alpha(navigation: str) -> float:
    """0.25 for NOISE_A025."""
    return int(re.search(r"_A(\d+)$", navigation).group(1)) / 100
