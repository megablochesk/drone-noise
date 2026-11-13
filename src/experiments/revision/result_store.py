from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PARQUET_ENGINE = "fastparquet"
RUNS_DIRECTORY_NAME = "runs"


@dataclass(frozen=True)
class ResultStore:
    """One JSON row, one drone-only level map and one trip log per run, addressed by run key."""
    root: Path

    @property
    def runs_directory(self) -> Path:
        return Path(self.root) / RUNS_DIRECTORY_NAME

    def row_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}.json"

    def drone_levels_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}_drone_levels.npz"

    def trips_path(self, run_key: str) -> Path:
        return self.runs_directory / f"{run_key}_trips.parquet"


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
