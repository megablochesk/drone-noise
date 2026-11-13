import json

import pandas as pd

from experiments.revision.build_artifact_manifest import build_manifest, calculate_sha256

ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_of_the_standard_test_vector(tmp_path):
    """Published test vector (FIPS 180-2): SHA-256 of "abc"."""
    file_path = tmp_path / "abc.bin"
    file_path.write_bytes(b"abc")
    assert calculate_sha256(file_path) == ABC_SHA256


def test_manifest_lists_run_artefacts_and_sidecar_provenance(tmp_path):
    """Hand-built artefact folder: one run (row + map) and one pool with a provenance sidecar. The run's
    files cite the commit stored in its row and the command of the table that lists it; the pool cites its
    sidecar; rows and sidecars themselves are not listed as artefacts."""
    runs_directory = tmp_path / "runs"
    runs_directory.mkdir()
    (runs_directory / "k1.json").write_text(json.dumps({"run_key": "k1", "git_hash": "commit-of-run"}))
    (runs_directory / "k1_drone_levels.npz").write_bytes(b"abc")
    pools_directory = tmp_path / "order_pools"
    pools_directory.mkdir()
    (pools_directory / "pool.parquet").write_bytes(b"abc")
    (pools_directory / "pool.parquet.provenance.json").write_text(
        json.dumps({"generating_commit": "commit-of-pool", "command": "generate --seeds 1"})
    )

    manifest = build_manifest(tmp_path, command_by_run_key={"k1": "run_phase6 --seeds 1"})

    assert manifest["path"].tolist() == ["order_pools/pool.parquet", "runs/k1_drone_levels.npz"]
    assert manifest["size_bytes"].tolist() == [3, 3]
    assert manifest["sha256"].tolist() == [ABC_SHA256, ABC_SHA256]
    assert manifest["generating_commit"].tolist() == ["commit-of-pool", "commit-of-run"]
    assert manifest["command"].tolist() == ["generate --seeds 1", "run_phase6 --seeds 1"]


def test_artefact_without_any_provenance_is_listed_with_blank_provenance(tmp_path):
    """A file that has neither a sidecar nor a run row must still appear, visibly unattributed."""
    (tmp_path / "phase8").mkdir()
    (tmp_path / "phase8" / "orphan.npz").write_bytes(b"abc")

    manifest = build_manifest(tmp_path, command_by_run_key={})

    assert manifest["path"].tolist() == ["phase8/orphan.npz"]
    assert manifest["generating_commit"].tolist() == [""]
    assert manifest["command"].tolist() == [""]
