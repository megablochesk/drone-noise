"""Run tables are rebuilt from the result store, for example after a job array on a cluster."""
import numpy as np
import pytest

from common.enum import OrderDatasetType
from experiments.revision.batch_runner import collect_stored_runs
from experiments.revision.result_store import ResultStore, save_result
from experiments.revision.run_specification import RunSpecification, build_run_key, specification_to_record

SPECIFICATIONS = [
    RunSpecification(stocking=OrderDatasetType.CLOSEST, number_of_drones=fleet, terminal_phases=True, seed=seed)
    for fleet in (500, 100) for seed in (1, 2)
]


def store_run(store: ResultStore, specification: RunSpecification, delivered_orders: int):
    row = {"run_key": build_run_key(specification), **specification_to_record(specification), "delivered_orders": delivered_orders}
    save_result(store, row["run_key"], row, np.zeros(3), np.zeros(2))


def test_stored_runs_are_listed_in_the_order_of_the_design(tmp_path):
    store = ResultStore(tmp_path)
    for position, specification in enumerate(reversed(SPECIFICATIONS)):
        store_run(store, specification, delivered_orders=position)

    table = collect_stored_runs(SPECIFICATIONS, store)

    assert table["run_key"].tolist() == [build_run_key(specification) for specification in SPECIFICATIONS]
    assert table["delivered_orders"].tolist() == [3, 2, 1, 0]


def test_a_design_with_runs_that_are_not_stored_is_refused(tmp_path):
    store = ResultStore(tmp_path)
    store_run(store, SPECIFICATIONS[0], delivered_orders=1)

    with pytest.raises(FileNotFoundError, match="3 of 4 runs"):
        collect_stored_runs(SPECIFICATIONS, store)
