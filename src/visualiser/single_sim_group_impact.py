from __future__ import annotations

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from census_analysis.age_data_processor.age_cell_matrix_calculator import AGE_BAND_DEFS
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH

CELL_AGE = load_dataframe_from_pickle(CELL_AGE_PATH)
CELL_ETHNICITY = load_dataframe_from_pickle(CELL_ETHNICITY_PATH)


def _slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(s)).strip("_").lower()


def _impacted_cells(impact_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    m = (impact_df["combined_noise"] > threshold) & (impact_df["noise_level"] < threshold)
    return impact_df.loc[m, ["row", "col"]].drop_duplicates(ignore_index=True)


def _summarise_group_counts(cells: pd.DataFrame, cell_values_df: pd.DataFrame, value_cols: list[int], name_map: dict[int, str]) -> pd.DataFrame:
    if cells.empty:
        impacted = pd.Series({c: 0.0 for c in value_cols}, dtype=float)
    else:
        joined = cells.merge(cell_values_df[["row", "col", *value_cols]], on=["row", "col"], how="left")
        impacted = joined[value_cols].sum(numeric_only=True)

    df = pd.DataFrame({
        "code": value_cols,
        "name": [name_map.get(int(c), str(c)) for c in value_cols],
        "impacted": [float(impacted.get(c, 0.0)) for c in value_cols],
    })

    return df.reset_index(drop=True)


from matplotlib import ticker as mtick
from textwrap import fill

def _wrap(names, width=16):
    return [fill(str(n), width=width) for n in names]

def _plot_count_bars(
    df: pd.DataFrame,
    title: str,
    filename: str,
    *,
    sort: str | None = None,     # 'desc' | 'asc' | None
    top_n: int | None = None,
    wrap: int = 16,
    annotate: bool = False,
):
    if sort == "desc":
        df = df.sort_values("impacted", ascending=False, kind="mergesort")
    elif sort == "asc":
        df = df.sort_values("impacted", ascending=True, kind="mergesort")

    if top_n is not None:
        df = df.head(top_n)

    y = np.arange(len(df))
    vals = df["impacted"].to_numpy(dtype=float)

    height = max(4.0, 0.38 * len(df))
    fig, ax = plt.subplots(figsize=(12, height), constrained_layout=True)
    fig.filename = filename

    ax.barh(y, vals, height=0.9)
    ax.set_yticks(y, _wrap(df["name"].tolist(), width=wrap))
    ax.invert_yaxis()  # highest first if sorted desc
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlabel("People impacted")
    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    if annotate:
        for yi, v in zip(y, vals):
            if v > 0:
                ax.text(v, yi, f"{v:,.0f}", va="center", ha="left", fontsize=9)


def plot_single_sim_age_impact_counts(noise_impact_df: pd.DataFrame, threshold: float = 55.0, filename_prefix: str = "age_impact_abs"):
    cells = _impacted_cells(noise_impact_df, threshold)
    value_cols = [c for c in CELL_AGE.columns if isinstance(c, (int, np.integer))]

    # Use AGE_BAND_DEFS to map band codes to string labels
    names = {k: AGE_BAND_DEFS[k][2] for k in value_cols if k in AGE_BAND_DEFS}

    summary = _summarise_group_counts(cells, CELL_AGE, value_cols, names)

    _plot_count_bars(summary,
                     f"Age: people newly exposed over {threshold} dB",
                     f"{filename_prefix}_{int(threshold)}",
                     top_n=None,
                     wrap=10)

    return summary



def plot_single_sim_ethnicity_impact_counts(noise_impact_df: pd.DataFrame, threshold: float = 55.0,
                                            filename_prefix: str = "eth_impact_abs"):
    cells = _impacted_cells(noise_impact_df, threshold)
    value_cols = [c for c in CELL_ETHNICITY.columns if isinstance(c, (int, np.integer))]

    raw_names = CELL_ETHNICITY.attrs.get("ethnicity_code_to_name", {int(c): str(c) for c in value_cols})

    # Truncate names after ":" or " - " if present
    names = {
        k: re.split(r":| - ", v, maxsplit=1)[-1].strip() if isinstance(v, str) else str(v)
        for k, v in raw_names.items()
    }

    summary = _summarise_group_counts(cells, CELL_ETHNICITY, value_cols, names)

    _plot_count_bars(summary,
                     f"Ethnicity: people newly exposed over {threshold} dB",
                     f"eth_impact_abs_{int(threshold)}",
                     top_n=None,
                     wrap=14,
                     annotate=False)

    return summary

