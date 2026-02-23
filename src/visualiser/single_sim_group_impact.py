from __future__ import annotations

import re
from pathlib import Path

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


def _reorder_by_codes(df: pd.DataFrame, codes: list[int]) -> pd.DataFrame:
    order = pd.Categorical(df["code"], categories=codes, ordered=True)
    return df.assign(_ord=order).sort_values("_ord").drop(columns=["_ord"])


def _latex_escape(s: str) -> str:
    return (
        str(s)
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


def _save_mapping(mapping: pd.DataFrame, base_path: str) -> None:
    Path(base_path).parent.mkdir(parents=True, exist_ok=True)

    rows = "\n".join(
        f"{_latex_escape(r.code)} & {_latex_escape(r.name)} \\\\"
        for r in mapping.itertuples(index=False)
    )
    tex = (
        "\\begin{tabular}{ll}\n"
        "\\hline\n"
        "Code & Group \\\\\n"
        "\\hline\n"
        f"{rows}\n"
        "\\hline\n"
        "\\end{tabular}\n"
    )
    with open(f"figures/{base_path}.tex", "w", encoding="utf-8") as f:
        f.write(tex)


def _plot_bars(
    df: pd.DataFrame,
    *,
    value_col: str,                 # 'impacted' | 'pct'
    title: str,
    filename: str,                  # base name (without extension)
    sort: str | None = None,        # 'desc' | 'asc' | None
    annotate: bool = True,
    max_items: int | None = None,
    legend_prefix: str | None = None,  # base path (without extension) for legend table
    codes_override: list[str] | None = None,  # use fixed codes for shared legend across plots
) -> pd.DataFrame:
    if sort == "desc":
        df = df.sort_values(value_col, ascending=False, kind="mergesort")
    elif sort == "asc":
        df = df.sort_values(value_col, ascending=True, kind="mergesort")

    if max_items is not None:
        df = df.head(max_items).copy()

    df = df.reset_index(drop=True)

    codes = codes_override if codes_override is not None else [f"E{idx + 1:02d}" for idx in range(len(df))]

    y = np.arange(len(df))
    vals = df[value_col].to_numpy(dtype=float)

    fig_h = max(3.8, 0.28 * len(df) + 1.2)
    fig, ax = plt.subplots(figsize=(10.5, fig_h), constrained_layout=True)
    fig.filename = filename

    ax.barh(y, vals, height=0.75)
    ax.set_yticks(y, codes)
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=9)

    if value_col == "pct":
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.1f}%"))
        ax.set_xlabel("% of group impacted")
    else:
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
        ax.set_xlabel("People impacted")

    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    if annotate:
        xmax = float(np.nanmax(vals)) if vals.size else 0.0
        pad = 0.01 * xmax if xmax > 0 else 0.0
        for yi, v in zip(y, vals):
            if v > 0:
                label = f"{v:,.1f}%" if value_col == "pct" else f"{v:,.0f}"
                ax.text(v + pad, yi, label, va="center", ha="left", fontsize=9)

    fig.savefig(f"figures/{filename}.eps")
    plt.close(fig)

    mapping = pd.DataFrame({"code": codes, "name": df["name"].tolist()})

    if legend_prefix is not None:
        _save_mapping(mapping, legend_prefix)

    return mapping


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
    mode: str = "count",              # 'count' | 'pct'
    filename_prefix: str | None = None,
    sort: str | None = None,          # 'desc' | 'asc' | None
    annotate: bool | None = None,
    max_items: int | None = None,
    legend_prefix: str | None = None,  # when set, legend table is saved here
    shared_codes_order: list[int] | None = None,  # enforce same order across plots (by original group codes)
    shared_display_codes: list[str] | None = None,  # enforce same displayed codes (E01..)
    make_legend: bool = True,
) -> tuple[pd.DataFrame, list[int], list[str]]:
    cells = _impacted_cells(noise_impact_df, threshold)
    value_cols = _value_cols(cell_values_df)
    names = name_map_func(value_cols)
    summary = _summarise_groups(cells, cell_values_df, value_cols, names)

    if shared_codes_order is not None:
        summary = _reorder_by_codes(summary, shared_codes_order)
        sort = None

    thr = int(threshold)
    prefix = filename_prefix or f"{_slug(label)}_impact_{'pct' if mode == 'pct' else 'abs'}"
    legend_out = legend_prefix or f"{_slug(label)}_impact_legend_{thr}"

    if mode == "pct":
        annotate = True if annotate is None else annotate
        sort = "desc" if sort is None else sort

        mapping = _plot_bars(
            summary,
            value_col="pct",
            title=f"{label}: % of group newly exposed over {threshold} dB",
            filename=f"{prefix}_{thr}",
            sort=sort,
            annotate=annotate,
            max_items=max_items,
            legend_prefix=legend_out if make_legend else None,
            codes_override=shared_display_codes,
        )

        # Order and display codes to reuse later
        ordered_codes = summary.sort_values("pct", ascending=False, kind="mergesort")["code"].tolist() if shared_codes_order is None else shared_codes_order
        display_codes = mapping["code"].tolist() if shared_display_codes is None else shared_display_codes
        return summary, ordered_codes, display_codes

    annotate = False if annotate is None else annotate

    mapping = _plot_bars(
        summary,
        value_col="impacted",
        title=f"{label}: people newly exposed over {threshold} dB",
        filename=f"{prefix}_{thr}",
        sort=sort,
        annotate=annotate,
        max_items=max_items,
        legend_prefix=legend_out if make_legend else None,
        codes_override=shared_display_codes,
    )

    ordered_codes = summary["code"].tolist() if shared_codes_order is not None else summary["code"].tolist()
    display_codes = mapping["code"].tolist() if shared_display_codes is None else shared_display_codes
    return summary, ordered_codes, display_codes


def plot_single_sim_age_impact(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    mode: str = "count",
    filename_prefix: str | None = None,
    *,
    sort: str | None = None,
    annotate: bool | None = None,
    max_items: int | None = None,
    legend_prefix: str | None = None,
    shared_codes_order: list[int] | None = None,
    shared_display_codes: list[str] | None = None,
    make_legend: bool = True,
) -> tuple[pd.DataFrame, list[int], list[str]]:
    return plot_single_sim_group_impact(
        noise_impact_df=noise_impact_df,
        cell_values_df=CELL_AGE,
        label="Age",
        name_map_func=_age_names,
        threshold=threshold,
        mode=mode,
        filename_prefix=filename_prefix,
        sort=sort,
        annotate=annotate,
        max_items=max_items,
        legend_prefix=legend_prefix,
        shared_codes_order=shared_codes_order,
        shared_display_codes=shared_display_codes,
        make_legend=make_legend,
    )


def plot_single_sim_ethnicity_impact(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    mode: str = "count",
    filename_prefix: str | None = None,
    *,
    sort: str | None = None,
    annotate: bool | None = None,
    max_items: int | None = None,
    legend_prefix: str | None = None,
    shared_codes_order: list[int] | None = None,
    shared_display_codes: list[str] | None = None,
    make_legend: bool = True,
) -> tuple[pd.DataFrame, list[int], list[str]]:
    return plot_single_sim_group_impact(
        noise_impact_df=noise_impact_df,
        cell_values_df=CELL_ETHNICITY,
        label="Ethnicity",
        name_map_func=_ethnicity_names,
        threshold=threshold,
        mode=mode,
        filename_prefix=filename_prefix,
        sort=sort,
        annotate=annotate,
        max_items=max_items,
        legend_prefix=legend_prefix,
        shared_codes_order=shared_codes_order,
        shared_display_codes=shared_display_codes,
        make_legend=make_legend,
    )


def plot_single_sim_age_impact_counts(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    filename_prefix: str = "age_impact_abs",
) -> pd.DataFrame:
    summary, _, _ = plot_single_sim_age_impact(
        noise_impact_df,
        threshold=threshold,
        mode="count",
        filename_prefix=filename_prefix,
    )
    return summary


def plot_single_sim_age_impact_percentages(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    filename_prefix: str = "age_impact_pct",
) -> pd.DataFrame:
    summary, _, _ = plot_single_sim_age_impact(
        noise_impact_df,
        threshold=threshold,
        mode="pct",
        filename_prefix=filename_prefix,
        sort="desc",
        annotate=True,
    )
    return summary


def plot_single_sim_ethnicity_impact_counts(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    filename_prefix: str = "eth_impact_abs",
) -> pd.DataFrame:
    summary, _, _ = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="count",
        filename_prefix=filename_prefix,
    )
    return summary


def plot_single_sim_ethnicity_impact_percentages(
    noise_impact_df: pd.DataFrame,
    threshold: float = 55.0,
    filename_prefix: str = "eth_impact_pct",
) -> pd.DataFrame:
    summary, _, _ = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="pct",
        filename_prefix=filename_prefix,
        sort="desc",
        annotate=True,
    )
    return summary


def plot_single_sim_ethnicity_impact_pct_and_abs_shared_legend(
    noise_impact_df: pd.DataFrame,
    *,
    threshold: float = 55.0,
    pct_prefix: str = "eth_impact_pct",
    abs_prefix: str = "eth_impact_abs",
    legend_prefix: str = "eth_impact_legend",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    thr = int(threshold)

    pct_summary, codes_order, display_codes = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="pct",
        filename_prefix=pct_prefix,
        sort="desc",
        annotate=True,
        legend_prefix=f"{legend_prefix}_{thr}",
        make_legend=True,
    )

    abs_summary, _, _ = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="count",
        filename_prefix=abs_prefix,
        shared_codes_order=codes_order,
        shared_display_codes=display_codes,
        make_legend=False,
        sort=None,
    )

    return pct_summary, abs_summary


def plot_single_sim_age_impact_pct_and_abs_shared_legend(
    noise_impact_df: pd.DataFrame,
    *,
    threshold: float = 55.0,
    pct_prefix: str = "age_impact_pct",
    abs_prefix: str = "age_impact_abs",
    legend_prefix: str = "age_impact_legend",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    thr = int(threshold)

    pct_summary, codes_order, display_codes = plot_single_sim_age_impact(
        noise_impact_df,
        threshold=threshold,
        mode="pct",
        filename_prefix=pct_prefix,
        sort="desc",
        annotate=True,
        legend_prefix=f"{legend_prefix}_{thr}",
        make_legend=True,
    )

    abs_summary, _, _ = plot_single_sim_age_impact(
        noise_impact_df,
        threshold=threshold,
        mode="count",
        filename_prefix=abs_prefix,
        shared_codes_order=codes_order,
        shared_display_codes=display_codes,
        make_legend=False,
        sort=None,
    )

    return pct_summary, abs_summary
