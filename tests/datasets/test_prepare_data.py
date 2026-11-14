"""What the preparation script reports after trying to generate the missing files."""
from datasets.data_manifest import GenerationOutcome
from datasets.prepare_data import describe_generation_outcome, find_blocking_files
from tests.datasets.test_data_manifest import AGE, AGE_TABLE, GRAPH, ORDERS, POPULATION

OUTCOME = GenerationOutcome(generated=[POPULATION], blocked={AGE: [AGE_TABLE]}, still_missing=[ORDERS, AGE, AGE_TABLE, GRAPH])


def test_report_names_generated_blocked_and_missing_files():
    assert describe_generation_outcome(OUTCOME) == [
        "generated  cell population -> data/cell_population.pkl",
        "blocked    cell age: needs age table",
        "missing    orders (published) -> data/orders.csv; from: an unseeded script",
        "missing    cell age (derived) -> data/cell_age.pkl; from: computed from the age table",
        "missing    age table (external) -> census/age.csv; from: a public portal",
        "missing    navigation graph (cache) -> data/graph.pkl; from: built on first use",
    ]


def test_nothing_to_report_when_every_file_exists():
    assert describe_generation_outcome(GenerationOutcome([], {}, [])) == ["all catalogued data files are present"]


def test_missing_cache_files_do_not_block_but_other_missing_files_do():
    """A cache is built by the code that needs it; everything else must be there before a run."""
    assert find_blocking_files(OUTCOME) == [ORDERS, AGE, AGE_TABLE]
    assert find_blocking_files(GenerationOutcome([], {}, [GRAPH])) == []
