"""Checking, generating and listing data files, on a hand-built catalogue in a temporary directory."""
import math

import pandas as pd
import pytest

from datasets.data_catalogue import DataFile, DataOrigin
from datasets.data_manifest import (
    build_data_manifest,
    find_changed_files,
    find_missing_data_files,
    generate_missing_derived_files,
    resolve_generator,
)

SHA256_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
BOUNDARY = DataFile("boundary", "data/boundary.json", DataOrigin.EXTERNAL, "study boundary", "a public portal")
ORDERS = DataFile("orders", "data/orders.csv", DataOrigin.PUBLISHED, "published orders", "an unseeded script")
POPULATION = DataFile(
    "cell population", "data/cell_population.pkl", DataOrigin.DERIVED, "people per cell", "computed from the boundary",
    generator="package.module:compute_population", requires=("boundary",),
)
AGE = DataFile(
    "cell age", "data/cell_age.pkl", DataOrigin.DERIVED, "age bands per cell", "computed from the age table",
    generator="package.module:compute_age", requires=("age table",),
)
AGE_TABLE = DataFile("age table", "census/age.csv", DataOrigin.EXTERNAL, "age by area", "a public portal")
GRAPH = DataFile("navigation graph", "data/graph.pkl", DataOrigin.CACHE, "routing graph", "built on first use")
CATALOGUE = (BOUNDARY, ORDERS, POPULATION, AGE, AGE_TABLE, GRAPH)


def write_file(data_root, data_file: DataFile, content: bytes = b"abc"):
    path = data_root / data_file.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_files_that_do_not_exist_are_reported_missing(tmp_path):
    write_file(tmp_path, BOUNDARY)
    write_file(tmp_path, GRAPH)
    assert find_missing_data_files(CATALOGUE, tmp_path) == [ORDERS, POPULATION, AGE, AGE_TABLE]


def test_only_missing_derived_files_with_their_requirements_are_generated(tmp_path):
    """The boundary exists, so the population is generated; the age table is missing, so the age dataset is
    not; published, external and cache files are never generated."""
    write_file(tmp_path, BOUNDARY)
    generated_names = []

    def generate(data_file: DataFile):
        generated_names.append(data_file.name)
        write_file(tmp_path, data_file, b"generated")

    outcome = generate_missing_derived_files(CATALOGUE, tmp_path, generate)

    assert generated_names == ["cell population"]
    assert outcome.generated == [POPULATION]
    assert outcome.blocked == {AGE: [AGE_TABLE]}
    assert outcome.still_missing == [ORDERS, AGE, AGE_TABLE, GRAPH]


def test_existing_derived_file_is_left_alone(tmp_path):
    write_file(tmp_path, BOUNDARY)
    write_file(tmp_path, POPULATION, b"already there")

    def refuse_to_generate(data_file: DataFile):
        raise AssertionError(f"{data_file.name} exists and must not be generated again")

    outcome = generate_missing_derived_files((BOUNDARY, POPULATION), tmp_path, refuse_to_generate)

    assert outcome.generated == [] and outcome.still_missing == []
    assert (tmp_path / POPULATION.relative_path).read_bytes() == b"already there"


def test_generator_that_writes_nothing_is_an_error(tmp_path):
    write_file(tmp_path, BOUNDARY)
    with pytest.raises(FileNotFoundError, match="cell population"):
        generate_missing_derived_files((BOUNDARY, POPULATION), tmp_path, lambda data_file: None)


def test_generator_is_named_as_module_and_function():
    assert resolve_generator("math:sqrt") is math.sqrt


def test_manifest_lists_size_and_checksum_of_present_files(tmp_path):
    """Standard test vector: SHA-256 of the three bytes 'abc'."""
    write_file(tmp_path, BOUNDARY)
    manifest = build_data_manifest((BOUNDARY, ORDERS), tmp_path)

    assert manifest.to_dict("records") == [
        {"name": "boundary", "path": "data/boundary.json", "origin": "external", "present": True, "size_bytes": 3,
         "sha256": SHA256_OF_ABC, "description": "study boundary", "obtained_from": "a public portal", "generator": ""},
        {"name": "orders", "path": "data/orders.csv", "origin": "published", "present": False, "size_bytes": 0,
         "sha256": "", "description": "published orders", "obtained_from": "an unseeded script", "generator": ""},
    ]


def test_changed_external_and_published_files_are_found(tmp_path):
    """Derived files are not compared: recomputing them need not give the same bytes."""
    for data_file in (BOUNDARY, ORDERS, POPULATION):
        write_file(tmp_path, data_file)
    manifest = build_data_manifest((BOUNDARY, ORDERS, POPULATION), tmp_path)
    assert find_changed_files(manifest, tmp_path) == []

    write_file(tmp_path, ORDERS, b"different orders")
    write_file(tmp_path, POPULATION, b"different population")
    assert find_changed_files(manifest, tmp_path) == ["orders"]


def test_manifest_survives_a_csv_round_trip(tmp_path):
    write_file(tmp_path, BOUNDARY)
    manifest = build_data_manifest(CATALOGUE, tmp_path)
    manifest.to_csv(tmp_path / "manifest.csv", index=False)
    reloaded = pd.read_csv(tmp_path / "manifest.csv", keep_default_na=False)
    assert find_changed_files(reloaded, tmp_path) == []
