"""Writing the committed outputs of a phase: tables under results/<phase>/ and artefact provenance."""
import json
from pathlib import Path

import pandas as pd

from common.path_configs import PATH_CONFIGS

PROVENANCE_SUFFIX = ".provenance.json"


def phase_directory(phase_name: str) -> Path:
    return Path(PATH_CONFIGS.revision_results_dir) / phase_name


def encode_nested_values(table: pd.DataFrame) -> pd.DataFrame:
    return table.map(lambda value: json.dumps(value) if isinstance(value, (dict, list)) else value)


def write_phase_table(table: pd.DataFrame, directory: Path, file_name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    table_path = directory / file_name
    encode_nested_values(table).to_csv(table_path, index=False)
    return table_path


def append_table_rows(rows: pd.DataFrame, table_path: Path):
    table_path.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(table_path, mode="a", header=not table_path.exists(), index=False)


def write_artifact_provenance(artifact_path: Path, git_hash: str, command: str) -> Path:
    sidecar_path = artifact_path.with_name(artifact_path.name + PROVENANCE_SUFFIX)
    sidecar_path.write_text(json.dumps({"generating_commit": git_hash, "command": command}))
    return sidecar_path
