"""Lists every file under results/artifacts/ with size, SHA-256, generating commit and command.

Usage (from src/): python -m experiments.revision.build_artifact_manifest
"""
import json
from pathlib import Path

import pandas as pd

from common.checksum import calculate_sha256
from common.path_configs import PATH_CONFIGS
from experiments.revision.phase_outputs import PROVENANCE_SUFFIX, write_phase_table

MANIFEST_NAME = "MANIFEST.csv"
RUN_ROW_SUFFIX = ".json"
RUN_KEY_SEPARATOR = "_"
# The command that produced each committed run table, and therefore every run listed in it.
RUN_TABLE_COMMANDS = {
    "phase5/large_pool_runs.csv": "python -m experiments.revision.run_phase5_large_pool --workers 3",
    "phase6/replication_runs_pilot.csv":
        "python -m experiments.revision.run_phase6_replication --seeds 1 2 3 4 5 --workers 3",
    "phase8/minimum_slant_distance_runs.csv": "python -m experiments.revision.run_phase8_batches --workers 3",
    "phase8/time_step_runs.csv": "python -m experiments.revision.run_phase8_batches --workers 3",
    "phase9/runs.csv": "python -m experiments.revision.run_reduced_design_phase --phase phase9 --workers 3 (flag before fd0b3e3)",
    "phase10/runs.csv": "python -m experiments.revision.run_reduced_design_phase --phases phase10 --workers 3",
    "phase11/runs.csv": "python -m experiments.revision.run_reduced_design_phase --phases phase11 --workers 3",
    "phase12/runs.csv": "python -m experiments.revision.run_reduced_design_phase --phases phase12 --workers 3",
}
ADAPTIVE_TABLE_PATTERN = "phase6/replication_runs_fleet*_seeds*.csv"
ADAPTIVE_COMMAND = "python -m experiments.revision.run_phase6_adaptive_block (fleet and seeds as in the table name)"


def read_sidecar_provenance(file_path: Path) -> dict | None:
    sidecar_path = file_path.with_name(file_path.name + PROVENANCE_SUFFIX)
    return json.loads(sidecar_path.read_text()) if sidecar_path.exists() else None


def read_run_provenance(file_path: Path, command_by_run_key: dict[str, str]) -> dict:
    run_key = file_path.name.split(RUN_KEY_SEPARATOR)[0]
    row_path = file_path.parent / f"{run_key}{RUN_ROW_SUFFIX}"
    if not row_path.exists():
        return {"generating_commit": "", "command": ""}

    row = json.loads(row_path.read_text())
    return {"generating_commit": row["git_hash"], "command": command_by_run_key.get(run_key, "")}


def is_listed_artifact(file_path: Path) -> bool:
    return file_path.is_file() and not file_path.name.endswith((PROVENANCE_SUFFIX, RUN_ROW_SUFFIX, ".tmp"))


def build_manifest(artifacts_directory: Path, command_by_run_key: dict[str, str]) -> pd.DataFrame:
    rows = []
    for file_path in sorted(path for path in artifacts_directory.rglob("*") if is_listed_artifact(path)):
        provenance = read_sidecar_provenance(file_path) or read_run_provenance(file_path, command_by_run_key)
        rows.append({
            "path": file_path.relative_to(artifacts_directory).as_posix(),
            "size_bytes": file_path.stat().st_size,
            "sha256": calculate_sha256(file_path),
            **provenance,
        })
    return pd.DataFrame(rows)


def map_run_keys_to_commands(results_directory: Path) -> dict[str, str]:
    """A run stored by an earlier table keeps that table's command; later tables only add new runs."""
    commands = dict(RUN_TABLE_COMMANDS)
    commands.update({
        path.relative_to(results_directory).as_posix(): ADAPTIVE_COMMAND
        for path in sorted(results_directory.glob(ADAPTIVE_TABLE_PATTERN))
    })
    command_by_run_key = {}
    for table_name, command in commands.items():
        table_path = results_directory / table_name
        if table_path.exists():
            for run_key in pd.read_csv(table_path, usecols=["run_key"])["run_key"]:
                command_by_run_key.setdefault(run_key, command)
    return command_by_run_key


def main():
    results_directory = Path(PATH_CONFIGS.revision_results_dir)
    manifest = build_manifest(Path(PATH_CONFIGS.revision_artifacts_dir), map_run_keys_to_commands(results_directory))
    write_phase_table(manifest, results_directory, MANIFEST_NAME)


if __name__ == "__main__":
    main()
