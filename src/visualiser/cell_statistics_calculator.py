from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd


def _impacted_cells(noise_impact_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    m = (noise_impact_df["combined_noise"] > threshold) & (noise_impact_df["noise_level"] < threshold)
    return noise_impact_df.loc[m, ["row", "col"]].drop_duplicates(ignore_index=True)


def _ensure_cols(x: Iterable | int) -> list:
    if isinstance(x, (int, np.integer, str)):
        return [x]
    return list(x)


def _merge_cells(cells: pd.DataFrame, cell_values_df: pd.DataFrame, value_cols: Sequence) -> pd.DataFrame:
    return cells.merge(cell_values_df[["row", "col", *value_cols]], on=["row", "col"], how="left")


def calculate_cells_exceeding_threshold(main_df: pd.DataFrame, threshold: float = 55) -> pd.DataFrame:
    rows = []
    for _, r in main_df.iterrows():
        count = _impacted_cells(r["noise_impact_df"], threshold).shape[0]
        rows.append({
            "dataset": r["dataset"],
            "dataset_name": r["dataset_name"],
            "num_drones": r["num_drones"],
            "navigation_type": r["navigation_type"],
            "cells_exceeding_threshold": int(count),
        })
    return pd.DataFrame(rows)


def calculate_impacted_totals(
    main_df: pd.DataFrame,
    cell_values_df: pd.DataFrame,
    value_cols: Iterable | int | str,
    threshold: float = 55,
    rename_map: dict | None = None,
) -> pd.DataFrame:
    value_cols = _ensure_cols(value_cols)
    rows = []

    for _, r in main_df.iterrows():
        cells = _impacted_cells(r["noise_impact_df"], threshold)
        if cells.empty:
            totals = {str(c): 0.0 for c in value_cols}
        else:
            joined = _merge_cells(cells, cell_values_df, value_cols)
            totals = joined[value_cols].sum(numeric_only=True).to_dict()
            totals = {str(k): float(v) for k, v in totals.items()}

        row = {
            "dataset": r["dataset"],
            "dataset_name": r["dataset_name"],
            "num_drones": r["num_drones"],
            "navigation_type": r["navigation_type"],
            **totals,
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    if rename_map:
        out = out.rename(columns={str(k): v for k, v in rename_map.items()})
    return out


def get_impacted_cells_with_values(
    main_df: pd.DataFrame,
    cell_values_df: pd.DataFrame,
    value_cols: Iterable | int | str,
    threshold: float = 55,
) -> pd.DataFrame:
    value_cols = _ensure_cols(value_cols)
    rows = []

    keep = ["row", "col", *value_cols]
    cell_sub = cell_values_df[keep]

    for _, r in main_df.iterrows():
        cells = _impacted_cells(r["noise_impact_df"], threshold)
        if cells.empty:
            continue
        joined = cells.merge(cell_sub, on=["row", "col"], how="left")
        joined["dataset_name"] = r["dataset_name"]
        joined["num_drones"] = r["num_drones"]
        rows.append(joined)

    if not rows:
        return pd.DataFrame(columns=["dataset_name", "num_drones", "row", "col", *map(str, value_cols)])

    df = pd.concat(rows, ignore_index=True)
    agg = {c: "sum" for c in value_cols}
    df = (df.groupby(["dataset_name", "num_drones", "row", "col"], as_index=False)
            .agg(agg))
    return df


def calculate_population_impacted_by_noise(
    main_df: pd.DataFrame,
    population_df: pd.DataFrame,  # expects columns: row, col, population
    threshold: float = 55,
) -> pd.DataFrame:
    out = calculate_impacted_totals(main_df, population_df, value_cols="population", threshold=threshold)
    return out.rename(columns={"population": "impacted_population"})


def get_cells_impacted_by_noise_with_population(
    main_df: pd.DataFrame,
    population_df: pd.DataFrame,
    threshold: float = 55,
) -> pd.DataFrame:
    df = get_impacted_cells_with_values(main_df, population_df, value_cols="population", threshold=threshold)
    return df.rename(columns={"population": "impacted_population"})


def calculate_age_impacted_by_noise(
    main_df: pd.DataFrame,
    age_df: pd.DataFrame,  # expects columns: row, col, and integer age-band columns (e.g., 0..4)
    threshold: float = 55,
    use_band_names: bool = True,
) -> pd.DataFrame:
    value_cols = [c for c in age_df.columns if isinstance(c, (int, np.integer))]
    rename_map = None
    if use_band_names:
        names = age_df.attrs.get("age_band_code_to_name", {})
        rename_map = {int(k): f"age_{names[k]}" for k in value_cols if k in names}

    return calculate_impacted_totals(main_df, age_df, value_cols=value_cols, threshold=threshold, rename_map=rename_map)


def calculate_ethnicity_impacted_by_noise(
    main_df: pd.DataFrame,
    eth_df: pd.DataFrame,  # expects columns: row, col, and integer ethnicity code columns
    threshold: float = 55,
    use_names: bool = False,
) -> pd.DataFrame:
    value_cols = [c for c in eth_df.columns if isinstance(c, (int, np.integer))]
    rename_map = None
    if use_names:
        names = eth_df.attrs.get("ethnicity_code_to_name", {})

        rename_map = {int(k): f"eth_{names[k]}" for k in value_cols if k in names}

    return calculate_impacted_totals(main_df, eth_df, value_cols=value_cols, threshold=threshold, rename_map=rename_map)
