"""The result tables of the paper's experiments read as the run table and arrays the figures are drawn from.

A stored result table has one row per run and, in `noise_impact_df`, a table with one row per cell: `row`,
`col`, `noise_level` (baseline), `average_noise` (drones alone), `combined_noise` and `noise_difference`.
"""
import numpy as np
import pandas as pd

from visualiser.figure_tables import build_grid_image

CELL_TABLE_COLUMN = "noise_impact_df"
CELL_KEY = ["row", "col"]
RUN_TABLE_COLUMNS = {
    "dataset_name": "stocking", "num_drones": "number_of_drones", "navigation_type": "navigation",
    "delivered_orders_number": "delivered_orders", "avg_noise_diff": "mean_noise_increase_db",
    "execution_time_seconds": "execution_time_s",
}
LATEX_ESCAPES = {
    "\\": "\\textbackslash{}", "&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#", "_": "\\_", "{": "\\{", "}": "\\}",
    "~": "\\textasciitilde{}", "^": "\\textasciicircum{}",
}


def find_newly_exposed_cells_of_run(cell_table: pd.DataFrame, threshold_db: float) -> np.ndarray:
    """Cells whose baseline is below the threshold and whose combined level is above it; both strict."""
    return ((cell_table["combined_noise"] > threshold_db) & (cell_table["noise_level"] < threshold_db)).to_numpy()


def sum_newly_exposed_population(cell_table: pd.DataFrame, population: pd.DataFrame, threshold_db: float) -> float:
    newly_exposed_cells = cell_table.loc[find_newly_exposed_cells_of_run(cell_table, threshold_db), CELL_KEY]
    return newly_exposed_cells.merge(population[[*CELL_KEY, "population"]], on=CELL_KEY, how="left")["population"].sum()


def convert_legacy_results(
        results: pd.DataFrame, terminal_phases: bool, population: pd.DataFrame, threshold_db: float
) -> pd.DataFrame:
    """One row per run with the column names of the revision run tables, plus the exposure of each run."""
    runs = results.rename(columns=RUN_TABLE_COLUMNS)[list(RUN_TABLE_COLUMNS.values())]
    return runs.assign(
        terminal_phases=terminal_phases,
        newly_exposed_cells=[
            int(find_newly_exposed_cells_of_run(cell_table, threshold_db).sum()) for cell_table in results[CELL_TABLE_COLUMN]
        ],
        newly_exposed_population=[
            sum_newly_exposed_population(cell_table, population, threshold_db) for cell_table in results[CELL_TABLE_COLUMN]
        ],
    )


def read_cell_image(cell_table: pd.DataFrame, column: str) -> np.ndarray:
    return build_grid_image(cell_table["row"].to_numpy(), cell_table["col"].to_numpy(), cell_table[column].to_numpy())


def align_group_counts(cell_table: pd.DataFrame, group_table: pd.DataFrame) -> dict[int, np.ndarray]:
    """Residents of every group (the integer-named columns) in the cell order of the run."""
    group_codes = [column for column in group_table.columns if isinstance(column, (int, np.integer))]
    aligned = cell_table[CELL_KEY].merge(group_table[[*CELL_KEY, *group_codes]], on=CELL_KEY, how="left")
    if aligned[group_codes].isna().any().any():
        raise ValueError("The group table has no counts for some cells of the run")
    return {int(code): aligned[code].to_numpy() for code in group_codes}


def escape_for_latex(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(character, character) for character in str(text))


def format_code_table_as_latex(codes: list[str], names: list[str]) -> str:
    """The legend table of the group charts: code and group, sorted by code."""
    rows = "\n".join(
        f"{escape_for_latex(code)} & {escape_for_latex(name)} \\\\"
        for code, name in sorted(zip(codes, names), key=lambda pair: pair[0].lower())
    )
    return f"\\begin{{tabular}}{{ll}}\n\\hline\nCode & Group \\\\\n\\hline\n{rows}\n\\hline\n\\end{{tabular}}\n"
