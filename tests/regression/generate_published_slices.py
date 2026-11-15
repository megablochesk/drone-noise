"""Writes the reference slices of the short-period regression tests (tests/regression/data/published_slices).

Each published configuration is run for its first 10 simulated minutes through the runners that the full-day
tests check against the manuscript; the headline values and the per-cell map are stored. Run it only at a
commit where `python -m pytest -m slow tests/regression` passes, so the slices stand for the published results.

Usage (from the repository root): python tests/regression/generate_published_slices.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRECTORY = REPOSITORY_ROOT / "src"
sys.path[:0] = [str(REPOSITORY_ROOT), str(SOURCE_DIRECTORY)]
# The model resolves its data paths relative to src/ and reads several of them at import time.
os.chdir(SOURCE_DIRECTORY)

from tests.regression.published_runs import (  # noqa: E402
    MAP_KEY,
    PUBLISHED_NOISE_AWARE_CONFIGURATION,
    PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS,
    REFERENCE_SLICES_DIRECTORY,
    SLICE_SIMULATION_END_S,
    PublishedConfiguration,
    headline_path,
    map_path,
    per_cell_map,
    run_published_configuration,
    summarise_energy_sum_runner,
    summarise_published_runner,
)


def read_git_hash() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def build_headline(configuration: PublishedConfiguration, git_hash: str, with_energy_sum_runner: bool) -> dict:
    headline = {
        "git_hash": git_hash,
        "simulation_end_s": SLICE_SIMULATION_END_S,
        "published_runner": summarise_published_runner(configuration, SLICE_SIMULATION_END_S),
    }
    if with_energy_sum_runner:
        headline["energy_sum_runner"] = summarise_energy_sum_runner(configuration, SLICE_SIMULATION_END_S)
    return headline


def write_slice(configuration: PublishedConfiguration, git_hash: str, with_energy_sum_runner: bool):
    headline = build_headline(configuration, git_hash, with_energy_sum_runner)
    headline_path(configuration).write_text(json.dumps(headline, indent=2) + "\n")
    cell_map = per_cell_map(run_published_configuration(configuration, SLICE_SIMULATION_END_S))
    cell_map.reset_index()[[*MAP_KEY, *cell_map.columns]].to_csv(map_path(configuration), index=False)
    print(f"{headline_path(configuration).name}: {headline}", flush=True)


def main():
    git_hash = read_git_hash()
    REFERENCE_SLICES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for configuration in PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS:
        write_slice(configuration, git_hash, with_energy_sum_runner=True)
    write_slice(PUBLISHED_NOISE_AWARE_CONFIGURATION, git_hash, with_energy_sum_runner=False)


if __name__ == "__main__":
    main()
