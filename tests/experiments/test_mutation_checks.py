import pytest

from experiments.revision.run_mutation_checks import (
    MUTATIONS,
    REPOSITORY_ROOT,
    apply_mutation,
    build_test_environment,
    remove_compiled_files,
)


def test_mutation_replaces_the_single_occurrence():
    """Hand-built case: one occurrence of the original fragment is swapped for the mutated one."""
    assert apply_mutation("level = 10.0 * log(x)", "10.0 * log", "20.0 * log") == "level = 20.0 * log(x)"


@pytest.mark.parametrize("source_text", ["no such fragment", "twice: a + b, a + b"])
def test_mutation_must_match_exactly_once(source_text):
    """An absent or ambiguous fragment would make the check meaningless, so it is an error."""
    with pytest.raises(ValueError):
        apply_mutation(source_text, "a + b", "a - b")


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda mutation: mutation.function_name)
def test_every_listed_mutation_applies_to_the_current_source(mutation):
    """Invariant: the mutation table stays in step with the code it mutates."""
    source_text = (REPOSITORY_ROOT / mutation.source_path).read_text()
    assert apply_mutation(source_text, mutation.original, mutation.mutated) != source_text
    assert all((REPOSITORY_ROOT / test_path.split("::")[0]).exists() for test_path in mutation.test_paths)


def test_tests_of_a_mutant_do_not_write_compiled_files():
    """A compiled mutant must never be cached: on a drive with two-second timestamps it can outlive the
    restored source, which then keeps running as the mutant."""
    environment = build_test_environment({"PATH": "/usr/bin"})
    assert environment == {"PATH": "/usr/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def test_compiled_files_of_the_mutated_module_are_removed(tmp_path):
    """Hand-built package: only the caches of `energy.py` go, for every interpreter tag; others stay."""
    source_file = tmp_path / "energy.py"
    source_file.write_text("LEVEL = 1\n")
    cache_directory = tmp_path / "__pycache__"
    cache_directory.mkdir()
    for name in ["energy.cpython-312.pyc", "energy.cpython-312-pytest-9.1.1.pyc", "energy_tracker.cpython-312.pyc"]:
        (cache_directory / name).write_bytes(b"compiled")

    remove_compiled_files(source_file)

    assert sorted(path.name for path in cache_directory.iterdir()) == ["energy_tracker.cpython-312.pyc"]
    assert source_file.read_text() == "LEVEL = 1\n"


def test_module_without_a_cache_directory_needs_no_cleaning(tmp_path):
    source_file = tmp_path / "energy.py"
    source_file.write_text("LEVEL = 1\n")
    remove_compiled_files(source_file)
    assert [path.name for path in tmp_path.iterdir()] == ["energy.py"]
