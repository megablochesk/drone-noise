"""Checks the data files the model reads, generates the derived ones that are missing and reports the rest.

Usage (from src/):
    python -m datasets.prepare_data                    generate missing derived files, report what is missing
    python -m datasets.prepare_data --verify           also compare external and published files with the manifest
    python -m datasets.prepare_data --write-manifest   rewrite DATA_MANIFEST.csv from the files that are present
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

from datasets.data_catalogue import DATA_CATALOGUE, DataFile, DataOrigin
from datasets.data_manifest import (
    GenerationOutcome,
    build_data_manifest,
    find_changed_files,
    generate_missing_derived_files,
)

DATA_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = DATA_ROOT.parent / "DATA_MANIFEST.csv"


def describe_missing_file(data_file: DataFile) -> str:
    return (
        f"missing    {data_file.name} ({data_file.origin.value}) -> {data_file.relative_path}; "
        f"from: {data_file.obtained_from}"
    )


def describe_generation_outcome(outcome: GenerationOutcome) -> list[str]:
    if not (outcome.generated or outcome.blocked or outcome.still_missing):
        return ["all catalogued data files are present"]

    generated = [f"generated  {data_file.name} -> {data_file.relative_path}" for data_file in outcome.generated]
    blocked = [
        f"blocked    {data_file.name}: needs {', '.join(required.name for required in missing_requirements)}"
        for data_file, missing_requirements in outcome.blocked.items()
    ]
    return [*generated, *blocked, *(describe_missing_file(data_file) for data_file in outcome.still_missing)]


def find_blocking_files(outcome: GenerationOutcome) -> list[DataFile]:
    return [data_file for data_file in outcome.still_missing if data_file.origin is not DataOrigin.CACHE]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    outcome = generate_missing_derived_files(DATA_CATALOGUE, DATA_ROOT)
    print("\n".join(describe_generation_outcome(outcome)))

    if arguments.write_manifest:
        build_data_manifest(DATA_CATALOGUE, DATA_ROOT).to_csv(MANIFEST_PATH, index=False)
        print(f"manifest written to {MANIFEST_PATH}")

    changed_files = find_changed_files(pd.read_csv(MANIFEST_PATH, keep_default_na=False), DATA_ROOT) if arguments.verify else []
    for name in changed_files:
        print(f"changed    {name}: content differs from the manifest")

    if find_blocking_files(outcome) or changed_files:
        sys.exit(1)


if __name__ == "__main__":
    main()
