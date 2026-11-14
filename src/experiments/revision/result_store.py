from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from noise.noise_grid import NoiseGrid

PARQUET_ENGINE = "fastparquet"
RUNS_DIRECTORY_NAME = "runs"
RUN_ROW_SUFFIX = ".json"
GRIDS_DIRECTORY_NAME = "grids"
GRID_FINGERPRINT_LENGTH = 16
GRID_FINGERPRINT_COLUMN = "grid_fingerprint"


@dataclass(frozen=True)
class ResultStore:
    """One JSON row, one drone-only level map and one trip log per run, addressed by run key; and every grid
    a map was computed on, addressed by its fingerprint."""
    root: Path

    @property
    def runs_directory(self) -> Path:
        return Path(self.root) / RUNS_DIRECTORY_NAME

    def row_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}{RUN_ROW_SUFFIX}"

    def drone_levels_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}_drone_levels.npz"

    def trips_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}_trips.parquet"

    def grid_path(self, grid_fingerprint: str) -> Path:
        return Path(self.root) / GRIDS_DIRECTORY_NAME / f"{grid_fingerprint}.npz"


def has_result(store: ResultStore, run_key: str) -> bool:
    return store.row_path(run_key).exists()


def select_pending(store: ResultStore, run_keys: list[str]) -> list[str]:
    return [run_key for run_key in run_keys if not has_result(store, run_key)]


def write_json_atomically(content: dict, path: Path):
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(content, indent=2))
    os.replace(temporary_path, path)


def save_result(store: ResultStore, run_key: str, row: dict, drone_levels_db: np.ndarray, trip_distances_m: np.ndarray):
    store.runs_directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(store.drone_levels_path(run_key), drone_levels_db=drone_levels_db)
    pd.DataFrame({"trip_distance_m": trip_distances_m}).to_parquet(
        store.trips_path(run_key), engine=PARQUET_ENGINE, index=False
    )
    # The row marks the run as finished, so it goes last.
    write_json_atomically(row, store.row_path(run_key))


def load_row(store: ResultStore, run_key: str) -> dict:
    return json.loads(store.row_path(run_key).read_text())


def load_drone_levels(store: ResultStore, run_key: str) -> np.ndarray:
    with np.load(store.drone_levels_path(run_key)) as archive:
        return archive["drone_levels_db"]


def load_trip_distances(store: ResultStore, run_key: str) -> np.ndarray:
    trips = pd.read_parquet(store.trips_path(run_key), engine=PARQUET_ENGINE)
    return trips["trip_distance_m"].to_numpy()


def collect_rows(store: ResultStore, run_keys: list[str]) -> pd.DataFrame:
    return pd.DataFrame([load_row(store, run_key) for run_key in run_keys])


def calculate_grid_fingerprint(grid: NoiseGrid) -> str:
    """Names the cells of a grid and their order: a map is a list of levels in exactly this order."""
    cells = np.column_stack([grid.rows, grid.columns]).astype(np.int64)
    return hashlib.sha256(cells.tobytes()).hexdigest()[:GRID_FINGERPRINT_LENGTH]


def save_grid(store: ResultStore, grid: NoiseGrid) -> str:
    """Stores the grid under its fingerprint unless it is there already; returns the fingerprint."""
    fingerprint = calculate_grid_fingerprint(grid)
    grid_path = store.grid_path(fingerprint)
    if not grid_path.exists():
        grid_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = grid_path.with_suffix(f".{os.getpid()}.tmp.npz")
        np.savez_compressed(
            temporary_path, rows=grid.rows, columns=grid.columns, centroid_northings=grid.centroid_northings,
            centroid_eastings=grid.centroid_eastings,
        )
        os.replace(temporary_path, grid_path)
    return fingerprint


def load_stored_grid(store: ResultStore, grid_fingerprint: str) -> NoiseGrid:
    with np.load(store.grid_path(grid_fingerprint)) as archive:
        return NoiseGrid(
            rows=archive["rows"], columns=archive["columns"], centroid_northings=archive["centroid_northings"],
            centroid_eastings=archive["centroid_eastings"],
        )


def ensure_runs_are_on_grid(runs: pd.DataFrame, grid: NoiseGrid):
    """Refuses runs whose maps were computed on another grid; runs without a recorded grid pass."""
    if GRID_FINGERPRINT_COLUMN not in runs:
        return
    recorded = runs[GRID_FINGERPRINT_COLUMN].dropna()
    on_another_grid = recorded[recorded != calculate_grid_fingerprint(grid)]
    if len(on_another_grid) > 0:
        raise ValueError(
            f"{len(on_another_grid)} runs were computed on another grid than the present one; "
            "read their maps with the grid stored under their fingerprint"
        )


def record_grid_of_stored_run(store: ResultStore, run_key: str, grid: NoiseGrid) -> bool:
    """Writes the grid's fingerprint into the row of a run that names no grid; returns whether it did."""
    row = load_row(store, run_key)
    if row.get(GRID_FINGERPRINT_COLUMN):
        return False
    number_of_cells = len(load_drone_levels(store, run_key))
    if number_of_cells != len(grid.rows):
        raise ValueError(f"The map of {run_key} has {number_of_cells} cells, the grid {len(grid.rows)}")
    write_json_atomically({**row, GRID_FINGERPRINT_COLUMN: save_grid(store, grid)}, store.row_path(run_key))
    return True
