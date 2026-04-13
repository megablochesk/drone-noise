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


def _slug(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(text)).strip("_").lower()


def _value_cols(df: pd.DataFrame) -> list[int]:
    return [column for column in df.columns if isinstance(column, (int, np.integer))]


def _impacted_cells(impact_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    mask = (impact_df["combined_noise"] > threshold) & (impact_df["noise_level"] < threshold)
    return impact_df.loc[mask, ["row", "col"]].drop_duplicates(ignore_index=True)


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

    impacted_array = impacted.to_numpy()
    totals_array = totals.to_numpy()

    pct = np.divide(
        impacted_array,
        totals_array,
        out=np.zeros_like(impacted_array, dtype=float),
        where=totals_array > 0,
    ) * 100.0

    return (
        pd.DataFrame(
            {
                "code": value_cols,
                "name": [name_map.get(int(code), str(code)) for code in value_cols],
                "impacted": impacted.to_list(),
                "total": totals.to_list(),
                "pct": pct.tolist(),
            }
        )
        .reset_index(drop=True)
    )


def _reorder_by_codes(df: pd.DataFrame, codes: list[int]) -> pd.DataFrame:
    order = pd.Categorical(df["code"], categories=codes, ordered=True)
    return df.assign(_ord=order).sort_values("_ord").drop(columns=["_ord"])


def _latex_escape(text: str) -> str:
    return (
        str(text)
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


def _get_figures_root() -> Path:
    try:
        from visualiser.plot_utils import get_figure_output_directory  # type: ignore
        output_directory = get_figure_output_directory()
        return Path(output_directory) if output_directory else Path("figures")
    except Exception:
        return Path("figures")


def _save_mapping(mapping: pd.DataFrame, base_path: str) -> None:
    figures_root = _get_figures_root()
    output_path = figures_root / f"{base_path}.tex"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_mapping = mapping.sort_values("code", key=lambda col: col.str.lower()).reset_index(drop=True)

    rows = "\n".join(
        f"{_latex_escape(r.code)} & {_latex_escape(r.name)} \\\\"
        for r in sorted_mapping.itertuples(index=False)
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

    with open(output_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(tex)


def _plot_bars(
    df: pd.DataFrame,
    *,
    value_col: str,
    title: str,
    filename: str,
    sort: str | None = None,
    annotate: bool = True,
    max_items: int | None = None,
    legend_prefix: str | None = None,
    codes_override: list[str] | None = None,
    display_codes_func=None,
) -> pd.DataFrame:
    if sort == "desc":
        df = df.sort_values(value_col, ascending=False, kind="mergesort")
    elif sort == "asc":
        df = df.sort_values(value_col, ascending=True, kind="mergesort")

    if max_items is not None:
        df = df.head(max_items).copy()

    df = df.reset_index(drop=True)

    if codes_override is not None:
        display_codes = codes_override
    elif display_codes_func is not None:
        display_codes = display_codes_func(df["name"].tolist())
    else:
        display_codes = [f"E{index + 1:02d}" for index in range(len(df))]

    y_positions = np.arange(len(df))
    values = df[value_col].to_numpy(dtype=float)

    figure_height = max(3.8, 0.28 * len(df) + 1.2)
    fig, ax = plt.subplots(figsize=(10.5, figure_height), constrained_layout=True)

    # IMPORTANT: do NOT save here. Let finalise_visualisation() save everything into its output_directory.
    fig.filename = filename

    ax.barh(y_positions, values, height=0.75)
    ax.set_yticks(y_positions, display_codes)
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=11)

    if value_col == "pct":
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.2f}%"))
    else:
        ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))

    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    if annotate:
        max_value = float(np.nanmax(values)) if values.size else 0.0
        padding = 0.01 * max_value if max_value > 0 else 0.0
        for y_position, value in zip(y_positions, values):
            if value > 0:
                label = f"{value:,.2f}%" if value_col == "pct" else f"{value:,.0f}"
                ax.text(value + padding, y_position, label, va="center", ha="left", fontsize=11)

        ax.set_xlim(right=max_value * 1.12)

    mapping = pd.DataFrame({"code": display_codes, "name": df["name"].tolist()})
    if legend_prefix is not None:
        _save_mapping(mapping, legend_prefix)

    return mapping


def _age_names(value_cols: list[int]) -> dict[int, str]:
    return {code: AGE_BAND_DEFS[code][2] for code in value_cols if code in AGE_BAND_DEFS}


def _ethnicity_names(value_cols: list[int]) -> dict[int, str]:
    raw = CELL_ETHNICITY.attrs.get("ethnicity_code_to_name", {int(c): str(c) for c in value_cols})
    result = {}
    for code, name in raw.items():
        if int(code) not in value_cols:
            continue
        short_name = re.split(r":| - ", name, maxsplit=1)[-1].strip() if isinstance(name, str) else str(name)
        result[int(code)] = _ethnicity_full_label(short_name)
    return result


_ETHNICITY_HIGH_LEVEL_GROUP: dict[str, str] = {
    "Indian": "Asian",
    "Pakistani": "Asian",
    "Bangladeshi": "Asian",
    "Chinese": "Asian",
    "Other Asian": "Asian",
    "African": "Black",
    "Caribbean": "Black",
    "Other Black": "Black",
    "White and Black Caribbean": "Mixed",
    "White and Black African": "Mixed",
    "White and Asian": "Mixed",
    "Other Mixed or Multiple ethnic groups": "Mixed",
    "English, Welsh, Scottish, Northern Irish or British": "White",
    "Irish": "White",
    "Gypsy or Irish Traveller": "White",
    "Roma": "White",
    "Other White": "White",
    "Arab": "Other",
    "Any other ethnic group": "Other",
}

_ETHNICITY_ABBREVIATIONS: dict[str, str] = {
    "Indian": "A:IND",
    "Pakistani": "A:PAK",
    "Bangladeshi": "A:BAN",
    "Chinese": "A:CHN",
    "Other Asian": "A:OASN",
    "African": "B:AFR",
    "Caribbean": "B:CRB",
    "Other Black": "B:OBLK",
    "White and Black Caribbean": "M:WBCR",
    "White and Black African": "M:WBAF",
    "White and Asian": "M:WASN",
    "Other Mixed or Multiple ethnic groups": "M:OMIX",
    "English, Welsh, Scottish, Northern Irish or British": "W:BRIT",
    "Irish": "W:IRI",
    "Gypsy or Irish Traveller": "W:GIT",
    "Roma": "W:ROM",
    "Other White": "W:OWHT",
    "Arab": "O:ARB",
    "Any other ethnic group": "O:OTH",
}


def _ethnicity_full_label(name: str) -> str:
    group = _ETHNICITY_HIGH_LEVEL_GROUP.get(name)
    if group is None:
        return name
    return f"{group}: {name}"


def _ethnicity_display_codes(names: list[str]) -> list[str]:
    def _abbreviate(full_label: str) -> str:
        short_name = full_label.split(": ", 1)[-1] if ": " in full_label else full_label
        return _ETHNICITY_ABBREVIATIONS.get(short_name, full_label)
    return [_abbreviate(name) for name in names]


def plot_single_sim_group_impact(
    *,
    noise_impact_df: pd.DataFrame,
    cell_values_df: pd.DataFrame,
    label: str,
    name_map_func,
    threshold: float = 55.0,
    mode: str = "count",  # 'count' | 'pct'
    filename_prefix: str | None = None,
    sort: str | None = None,
    annotate: bool | None = None,
    max_items: int | None = None,
    legend_prefix: str | None = None,
    shared_codes_order: list[int] | None = None,
    shared_display_codes: list[str] | None = None,
    make_legend: bool = True,
    display_codes_func=None,
) -> tuple[pd.DataFrame, list[int], list[str]]:
    impacted_cells = _impacted_cells(noise_impact_df, threshold)
    value_cols = _value_cols(cell_values_df)
    names = name_map_func(value_cols)
    summary = _summarise_groups(impacted_cells, cell_values_df, value_cols, names)

    if shared_codes_order is not None:
        summary = _reorder_by_codes(summary, shared_codes_order)
        sort = None

    threshold_int = int(threshold)
    prefix = filename_prefix or f"{_slug(label)}_impact_{'pct' if mode == 'pct' else 'abs'}"
    legend_out = legend_prefix or f"{_slug(label)}_impact_legend_{threshold_int}"

    if mode == "pct":
        annotate = True if annotate is None else annotate
        sort = "desc" if sort is None else sort

        mapping = _plot_bars(
            summary,
            value_col="pct",
            title=None,
            filename=f"{prefix}_{threshold_int}",
            sort=sort,
            annotate=annotate,
            max_items=max_items,
            legend_prefix=legend_out if make_legend else None,
            codes_override=shared_display_codes,
            display_codes_func=display_codes_func,
        )

        ordered_codes = (
            summary.sort_values("pct", ascending=False, kind="mergesort")["code"].tolist()
            if shared_codes_order is None
            else shared_codes_order
        )
        display_codes = mapping["code"].tolist() if shared_display_codes is None else shared_display_codes
        return summary, ordered_codes, display_codes

    annotate = True if annotate is None else annotate

    mapping = _plot_bars(
        summary,
        value_col="impacted",
        title=None,
        filename=f"{prefix}_{threshold_int}",
        sort=sort,
        annotate=annotate,
        max_items=max_items,
        legend_prefix=legend_out if make_legend else None,
        codes_override=shared_display_codes,
        display_codes_func=display_codes_func,
    )

    ordered_codes = summary["code"].tolist() if shared_codes_order is not None else summary["code"].tolist()
    display_codes = mapping["code"].tolist() if shared_display_codes is None else shared_display_codes
    return summary, ordered_codes, display_codes


def _age_display_codes(names: list[str]) -> list[str]:
    return names


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
        display_codes_func=_age_display_codes,
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
        display_codes_func=_ethnicity_display_codes,
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
    threshold_int = int(threshold)

    pct_summary, codes_order, display_codes = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="pct",
        filename_prefix=pct_prefix,
        sort="desc",
        annotate=True,
        legend_prefix=f"{legend_prefix}_{threshold_int}",
        make_legend=True,
    )

    abs_summary, _, _ = plot_single_sim_ethnicity_impact(
        noise_impact_df,
        threshold=threshold,
        mode="count",
        filename_prefix=abs_prefix,
        shared_codes_order=codes_order,
        shared_display_codes=display_codes,
        legend_prefix=f"{legend_prefix}_{threshold_int}",
        make_legend=False,
    )

    return pct_summary, abs_summary