import pytest

from experiments.revision.run_mutation_checks import MUTATIONS, REPOSITORY_ROOT, apply_mutation


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
