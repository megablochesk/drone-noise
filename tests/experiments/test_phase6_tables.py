import pandas as pd

from experiments.revision.summarise_phase6_replication import read_run_tables


def test_run_tables_are_merged_without_duplicates_and_empty_blocks_are_skipped(tmp_path):
    """Hand-built case: a pilot table (runs a, b), an adaptive block repeating b and adding c, and the
    empty file left by a block that had nothing to run -> runs a, b, c once each."""
    pd.DataFrame({"run_key": ["a", "b"], "seed": [1, 2]}).to_csv(tmp_path / "replication_runs_pilot.csv", index=False)
    pd.DataFrame({"run_key": ["b", "c"], "seed": [2, 6]}).to_csv(tmp_path / "replication_runs_block.csv", index=False)
    (tmp_path / "replication_runs_empty.csv").write_text("\n")

    runs = read_run_tables(sorted(tmp_path.glob("replication_runs*.csv")))

    assert sorted(runs["run_key"]) == ["a", "b", "c"]
