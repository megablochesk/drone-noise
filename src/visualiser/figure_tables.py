"""Tables behind the figures: pure functions from run tables and arrays, without any drawing."""
import numpy as np
import pandas as pd

from visualiser.style import STRAIGHT

METRES_PER_KILOMETRE = 1000.0


def read_navigation(runs: pd.DataFrame) -> pd.Series:
    """The routing of every run; a run without a recorded routing is a straight-line run."""
    if "navigation" not in runs:
        return pd.Series(STRAIGHT, index=runs.index)
    return runs["navigation"].fillna(STRAIGHT)


def tabulate_metric_by_fleet(runs: pd.DataFrame, metric: str, terminal_phases: bool, navigation: str) -> pd.DataFrame:
    """Fleet sizes down, stockings across; every cell must come from exactly one run."""
    selected = runs[(runs["terminal_phases"] == terminal_phases) & (read_navigation(runs) == navigation)]
    runs_per_cell = selected.groupby(["number_of_drones", "stocking"]).size().unstack()
    if selected.empty or runs_per_cell.isna().any().any() or (runs_per_cell != 1).any().any():
        raise ValueError(f"Every fleet and stocking needs exactly one run of {navigation}, terminal phases {terminal_phases}")
    return selected.pivot(index="number_of_drones", columns="stocking", values=metric).sort_index()


def summarise_group_exposure(
        newly_exposed: np.ndarray, group_counts: dict[int, np.ndarray], group_names: dict[int, str]
) -> pd.DataFrame:
    """Per group: residents of the newly exposed cells, all residents, and the share of the group exposed."""
    summary = pd.DataFrame({
        "code": list(group_counts),
        "name": [group_names[code] for code in group_counts],
        "newly_exposed": [counts[newly_exposed].sum() for counts in group_counts.values()],
        "total": [counts.sum() for counts in group_counts.values()],
    })
    return summary.assign(share=summary["newly_exposed"] / summary["total"])


def find_shared_colour_range(maps: list[np.ndarray], lower_percentile: float, upper_percentile: float) -> tuple[float, float]:
    values = np.concatenate([image[np.isfinite(image)] for image in maps])
    return float(np.percentile(values, lower_percentile)), float(np.percentile(values, upper_percentile))


def build_grid_image(rows: np.ndarray, columns: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Cell values as a [row, column] image; cells that are not listed are NaN."""
    image = np.full((rows.max() + 1, columns.max() + 1), np.nan)
    image[rows, columns] = values
    return image


def count_cells_by_noise_increase(increases_db: np.ndarray, bin_width_db: float) -> tuple[list[str], list[int]]:
    """Number of cells per bin of the noise increase, from floor(min) to ceil(max), with the bins' labels."""
    bin_edges = np.arange(int(np.floor(increases_db.min())), int(np.ceil(increases_db.max())), bin_width_db)
    counts = pd.Series(increases_db).value_counts(bins=bin_edges, sort=False).sort_index()
    labels = [f"{interval.left:.1f} - {interval.right:.1f}" for interval in counts.index]
    return labels, counts.tolist()


def measure_route_lengths(routes: dict[str, tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
    """Length of each route given as eastings and northings in metres, and its excess over the straight route."""
    lengths_m = {name: np.hypot(np.diff(eastings), np.diff(northings)).sum() for name, (eastings, northings) in routes.items()}
    return pd.DataFrame({
        "navigation": list(lengths_m),
        "route_length_km": [length_m / METRES_PER_KILOMETRE for length_m in lengths_m.values()],
        "increase_over_straight": [length_m / lengths_m[STRAIGHT] - 1.0 for length_m in lengths_m.values()],
    })
