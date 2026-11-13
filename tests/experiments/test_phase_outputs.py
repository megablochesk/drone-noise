import json

import pandas as pd

from experiments.revision.phase_outputs import append_table_rows, write_artifact_provenance, write_phase_table


def test_table_is_written_as_csv_with_nested_values_as_json(tmp_path):
    """Invariant: scalar columns survive unchanged; dictionaries are stored as JSON text."""
    table = pd.DataFrame({"run_key": ["a"], "delivered_orders": [7], "per_warehouse": [{"DBR1": {"drones": 2}}]})
    table_path = write_phase_table(table, tmp_path / "phase6", "runs.csv")

    stored = pd.read_csv(table_path)
    assert stored["delivered_orders"].tolist() == [7]
    assert json.loads(stored["per_warehouse"].iloc[0]) == {"DBR1": {"drones": 2}}


def test_rows_are_appended_to_an_existing_table(tmp_path):
    """Hand-built case: one row, then two more, gives three rows in insertion order."""
    table_path = tmp_path / "timing.csv"
    append_table_rows(pd.DataFrame({"seed": [1], "seconds": [2.5]}), table_path)
    append_table_rows(pd.DataFrame({"seed": [2, 3], "seconds": [2.0, 3.0]}), table_path)
    assert pd.read_csv(table_path)["seed"].tolist() == [1, 2, 3]


def test_provenance_sidecar_records_commit_and_command(tmp_path):
    """Invariant: the sidecar names the artefact's generating commit and command."""
    artifact_path = tmp_path / "pool.parquet"
    artifact_path.write_bytes(b"data")
    sidecar_path = write_artifact_provenance(artifact_path, git_hash="abc123", command="python generate.py --seed 1")
    assert json.loads(sidecar_path.read_text()) == {
        "generating_commit": "abc123", "command": "python generate.py --seed 1"
    }
    assert sidecar_path.name == "pool.parquet.provenance.json"
