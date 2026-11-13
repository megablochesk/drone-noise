import time

from experiments.revision.result_store import ResultStore
from experiments.revision.run_executor import destination_pool_path
from experiments.revision.run_specification import RunSpecification
from orders.seeded_order_pool import DemandZone, generate_destinations, save_destination_pool


def generate_missing_pool(store: ResultStore, specification: RunSpecification, zones: list[DemandZone]) -> float | None:
    """Generates the destination pool a specification needs; returns the seconds taken, or None if it exists."""
    pool_path = destination_pool_path(store, specification)
    if pool_path.exists():
        return None

    started_at_s = time.perf_counter()
    destinations = generate_destinations(specification.seed, specification.pool_size, zones)
    pool_path.parent.mkdir(parents=True, exist_ok=True)
    save_destination_pool(destinations, pool_path)
    return time.perf_counter() - started_at_s
