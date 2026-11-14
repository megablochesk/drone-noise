"""Which catalogued data files exist, which can be generated, and a manifest of sizes and checksums."""
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from common.checksum import calculate_sha256
from datasets.data_catalogue import DataFile, DataOrigin

CHECKSUMMED_ORIGINS = (DataOrigin.EXTERNAL.value, DataOrigin.PUBLISHED.value)


@dataclass(frozen=True)
class GenerationOutcome:
    generated: list[DataFile]
    blocked: dict[DataFile, list[DataFile]]
    still_missing: list[DataFile]


def find_missing_data_files(catalogue: tuple[DataFile, ...], data_root: Path) -> list[DataFile]:
    return [data_file for data_file in catalogue if not (data_root / data_file.relative_path).exists()]


def resolve_generator(generator: str) -> Callable:
    """`generator` names a function as 'package.module:function'."""
    module_name, function_name = generator.split(":")
    return getattr(importlib.import_module(module_name), function_name)


def run_generator(data_file: DataFile):
    resolve_generator(data_file.generator)()


def find_missing_requirements(data_file: DataFile, catalogue: tuple[DataFile, ...], data_root: Path) -> list[DataFile]:
    missing_names = {missing.name for missing in find_missing_data_files(catalogue, data_root)}
    return [required for required in catalogue if required.name in data_file.requires and required.name in missing_names]


def generate_missing_derived_files(
        catalogue: tuple[DataFile, ...], data_root: Path, generate: Callable[[DataFile], None] = run_generator
) -> GenerationOutcome:
    """Generates, in catalogue order, every missing derived file whose required files exist."""
    generated, blocked = [], {}
    for data_file in find_missing_data_files(catalogue, data_root):
        if data_file.origin is not DataOrigin.DERIVED:
            continue

        missing_requirements = find_missing_requirements(data_file, catalogue, data_root)
        if missing_requirements:
            blocked[data_file] = missing_requirements
            continue

        generate(data_file)
        if not (data_root / data_file.relative_path).exists():
            raise FileNotFoundError(f"The generator of '{data_file.name}' did not write {data_file.relative_path}")
        generated.append(data_file)

    return GenerationOutcome(generated, blocked, find_missing_data_files(catalogue, data_root))


def describe_data_file(data_file: DataFile, data_root: Path) -> dict:
    path = data_root / data_file.relative_path
    present = path.exists()
    return {
        "name": data_file.name,
        "path": data_file.relative_path,
        "origin": data_file.origin.value,
        "present": present,
        "size_bytes": path.stat().st_size if present else 0,
        "sha256": calculate_sha256(path) if present else "",
        "description": data_file.description,
        "obtained_from": data_file.obtained_from,
        "generator": data_file.generator or "",
    }


def build_data_manifest(catalogue: tuple[DataFile, ...], data_root: Path) -> pd.DataFrame:
    return pd.DataFrame([describe_data_file(data_file, data_root) for data_file in catalogue])


def find_changed_files(manifest: pd.DataFrame, data_root: Path) -> list[str]:
    """Names of external and published files whose content differs from the manifest."""
    checked = manifest[manifest["origin"].isin(CHECKSUMMED_ORIGINS) & (manifest["sha256"] != "")]
    return [
        entry.name for entry in checked.itertuples()
        if (data_root / entry.path).exists() and calculate_sha256(data_root / entry.path) != entry.sha256
    ]
