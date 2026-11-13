import pandas as pd
from shapely.geometry import box

from experiments.revision.order_pool_generation import generate_missing_pool
from experiments.revision.result_store import ResultStore
from experiments.revision.run_executor import destination_pool_path
from experiments.revision.run_specification import RunSpecification
from common.enum import OrderDatasetType
from orders.seeded_order_pool import DemandZone, generate_destinations, load_destination_pool

ZONES = [DemandZone(code="ONLY", polygon=box(0.0, 0.0, 100.0, 100.0), weight=1.0)]
SPECIFICATION = RunSpecification(
    stocking=OrderDatasetType.RANDOM, number_of_drones=10, terminal_phases=False, seed=4, pool_size=50
)


def test_missing_pool_is_generated_where_the_executor_looks_for_it(tmp_path):
    """Invariant: the stored pool is exactly the seeded destinations for (seed, size)."""
    store = ResultStore(tmp_path)
    generation_seconds = generate_missing_pool(store, SPECIFICATION, ZONES)

    assert generation_seconds > 0
    stored_pool = load_destination_pool(destination_pool_path(store, SPECIFICATION))
    pd.testing.assert_frame_equal(stored_pool, generate_destinations(4, 50, ZONES))


def test_existing_pool_is_not_generated_again(tmp_path):
    """Resumability: a second call finds the pool and reports that nothing was generated."""
    store = ResultStore(tmp_path)
    generate_missing_pool(store, SPECIFICATION, ZONES)
    modification_time = destination_pool_path(store, SPECIFICATION).stat().st_mtime_ns

    assert generate_missing_pool(store, SPECIFICATION, ZONES) is None
    assert destination_pool_path(store, SPECIFICATION).stat().st_mtime_ns == modification_time
