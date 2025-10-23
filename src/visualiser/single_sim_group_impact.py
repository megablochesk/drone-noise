from __future__ import annotations

import re
from textwrap import fill

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import ticker as mtick

from census_analysis.age_data_processor.age_cell_matrix_calculator import AGE_BAND_DEFS
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH

CELL_AGE = load_dataframe_from_pickle(CELL_AGE_PATH)
CELL_ETHNICITY = load_dataframe_from_pickle(CELL_ETHNICITY_PATH)


def _slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(s)).strip("_").lower()


def _wrap(names, width=16):
    return [fill(str(n), width=width) for n in names]


def _value_cols(df: pd.DataFrame) -> list[int]:
    return [c for c in df.columns if isinstance(c, (int, np.integer))]


def _impacted_cells(impact_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    m = (impact_df["combined_noise"] > threshold) & (impact_df["noise_level"] < threshold)
    return impact_df.loc[m, ["row", "col"]].drop_duplicates(ignore_index=True)


def _summarise_groups(
    cells: pd.DataFrame,
    cell_values_df: pd.DataFrame,
    value_cols: list[int],
    name_map: dict[int, str],
) -> pd.DataFrame:
    if cells.empty:
        impacted = pd.Series({c: 0.0 for c in value_cols}, dtype=float)
    else:
        joined = cells.merge(cell_values_df[["row", "col", *value_cols]], on=["row", "col"], how="left")
        impacted = joined[value_cols].sum(numeric_only=True)

    totals = cell_values_df[value_cols].sum(numeric_only=True)
    impacted = impacted.reindex(value_cols).astype(float).fillna(0.0)
    totals = totals.reindex(value_cols).astype(float).fillna(0.0)
    pct = np.divide(
        impacted.to_numpy(),
        totals.to_numpy(),
        out=np.zeros_like(impacted.to_numpy(), dtype=float),
        where=totals.to_numpy() > 0,
    ) * 100.0

    return pd.DataFrame(
        {
            "code": value_cols,
            "name": [name_map.get(int(c), str(c)) for c in value_cols],
            "impacted": impacted.to_list(),
            "total": totals.to_list(),
            "pct": pct.tolist(),
        }
    ).reset_index(drop=True)


def _plot_bars(
    df: pd.DataFrame,
    *,
    value_col: str,           # 'impacted' | 'pct'
    title: str,
    filename: str,
    sort: str | None = None,  # 'desc' | 'asc' | None
    wrap: int = 16,
    annotate: bool = False,
):
    if sort == "desc":
        df = df.sort_values(value_col, ascending=False, kind="mergesort")
    elif sort == "asc":
        df = df.sort_values(value_col, ascending=True, kind="mergesort")

    y = np.arange(len(df))
    vals = df[value_col].to_numpy(dtype=float)

    height = max(4.0, 0.38 * len(df))
    fig, ax = plt.subplots(figsize=(12, height), constrained_layout=True)
    fig.filename = filename

    ax.barh(y, vals, height=0.9)
    ax.set_yticks(y, _wrap(df["name"].tolist(), width=wrap))
    ax.invert_yaxis()

    if value_col == "pct":
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.1f}%"))
        ax.set_xlabel("% of group impacted")
    else:
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
        ax.set_xlabel("People impacted")

    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    if annotate:
        for yi, v in zip(y, vals):
            if v > 0:
                label = f"{v:,.1f}%" if value_col == "pct" else f"{v:,.0f}"
                ax.text(v, yi, label, va="center", ha="left", fontsize=9)


def _age_names(value_cols: list[int]) -> dict[int, str]:
    return {k: AGE_BAND_DEFS[k][2] for k in value_cols if k in AGE_BAND_DEFS}


def _ethnicity_names(value_cols: list[int]) -> dict[int, str]:
    raw = CELL_ETHNICITY.attrs.get("ethnicity_code_to_name", {int(c): str(c) for c in value_cols})
    return {
        int(k): (re.split(r":| - ", v, maxsplit=1)[-1].strip() if isinstance(v, str) else str(v))
        for k, v in raw.items()
        if int(k) in value_cols
    }


def plot_single_sim_group_impact(
    *,
    noise_impact_df: pd.DataFrame,
    cell_values_df: pd.DataFrame,
    label: str,
    name_map_func,
    threshold: float = 55.0,
    mode: str = "count",        # 'count' | 'pct'
    filename_prefix: str | None = None,
    sort: str | None = None,    # 'desc' | 'asc' | None
    wrap: int = 16,
    annotate: bool | None = None,
) -> pd.DataFrame:
    cells = _impacted_cells(noise_impact_df, threshold)
    value_cols = _value_cols(cell_values_df)
    names = name_map_func(value_cols)
    summary = _summarise_groups(cells, cell_values_df, value_cols, names)

    if mode == "pct":
        annotate = True if annotate is None else annotate
        sort = "desc" if sort is None else sort
        prefix = filename_prefix or f"{_slug(label)}_impact_pct"
        _plot_bars(
            summary,
            value_col="pct",
            title=f"{label}: % of group newly exposed over {threshold} dB",
            filename=f"{prefix}_{int(threshold)}",
            sort=sort,
            wrap=wrap,
            annotate=annotate,
        )
    else:
        annotate = False if annotate is None else annotate
        prefix = filename_prefix or f"{_slug(label)}_impact_abs"
        _plot_bars(
            summary,
            value_col="impacted",
            title=f"{label}: people newly exposed over {threshold} dB",
            filename=f"{prefix}_{int(threshold)}",
            sort=sort,
            wrap=wrap,
            annotate=annotate,
        )
    return summary


def plot_single_sim_age_impact(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    mode: str = "count",
    filename_prefix: str | None = None,
    *,
    sort: str | None = None,
    wrap: int = 10,
    annotate: bool | None = None,
) -> pd.DataFrame:
    return plot_single_sim_group_impact(
        noise_impact_df=noise_impact_df,
        cell_values_df=CELL_AGE,
        label="Age",
        name_map_func=_age_names,
        threshold=threshold,
        mode=mode,
        filename_prefix=filename_prefix,
        sort=sort,
        wrap=wrap,
        annotate=annotate,
    )


def plot_single_sim_ethnicity_impact(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    mode: str = "count",
    filename_prefix: str | None = None,
    *,
    sort: str | None = None,
    wrap: int = 14,
    annotate: bool | None = None,
) -> pd.DataFrame:
    return plot_single_sim_group_impact(
        noise_impact_df=noise_impact_df,
        cell_values_df=CELL_ETHNICITY,
        label="Ethnicity",
        name_map_func=_ethnicity_names,
        threshold=threshold,
        mode=mode,
        filename_prefix=filename_prefix,
        sort=sort,
        wrap=wrap,
        annotate=annotate,
    )


def plot_single_sim_age_impact_counts(noise_impact_df: pd.DataFrame, threshold: float = 55.0, filename_prefix: str = "age_impact_abs"):
    return plot_single_sim_age_impact(noise_impact_df, threshold=threshold, mode="count", filename_prefix=filename_prefix)


def plot_single_sim_age_impact_percentages(noise_impact_df: pd.DataFrame, threshold: float = 55.0, filename_prefix: str = "age_impact_pct"):
    return plot_single_sim_age_impact(noise_impact_df, threshold=threshold, mode="pct", filename_prefix=filename_prefix)


def plot_single_sim_ethnicity_impact_counts(noise_impact_df: pd.DataFrame, threshold: float = 55.0, filename_prefix: str = "eth_impact_abs"):
    return plot_single_sim_ethnicity_impact(noise_impact_df, threshold=threshold, mode="count", filename_prefix=filename_prefix)


def plot_single_sim_ethnicity_impact_percentages(noise_impact_df: pd.DataFrame, threshold: float = 55.0, filename_prefix: str = "eth_impact_pct"):
    return plot_single_sim_ethnicity_impact(noise_impact_df, threshold=threshold, mode="pct", filename_prefix=filename_prefix)
