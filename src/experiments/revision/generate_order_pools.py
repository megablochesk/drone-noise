"""Phase 5: generate seed-labelled destination pools (Parquet) and time the generation.

Usage (from src/): python -m experiments.revision.generate_order_pools --seeds 1 2 3 --pool-size 500000
"""
import argparse
import sys

import pandas as pd

from common.enum import OrderDatasetType
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.order_pool_generation import generate_missing_pool
from experiments.revision.phase_outputs import append_table_rows, phase_directory, write_artifact_provenance
from experiments.revision.run_executor import destination_pool_path
from experiments.revision.run_guard import ensure_ready_to_run
from experiments.revision.run_specification import DemandModel, RunSpecification
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import DemandZone, weight_zones_by_area

TIMING_TABLE_NAME = "order_pool_generation.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--pool-size", type=int, required=True)
    parser.add_argument("--demand-model", choices=[model.value for model in DemandModel], default="population")
    return parser.parse_args()


def load_demand_zones(demand_model: DemandModel) -> list[DemandZone]:
    population_zones = load_population_zones()
    return weight_zones_by_area(population_zones) if demand_model is DemandModel.AREA else population_zones


def pool_specification(seed: int, pool_size: int, demand_model: DemandModel) -> RunSpecification:
    """Only seed, size and demand model locate a pool; the remaining fields are placeholders."""
    return RunSpecification(
        stocking=OrderDatasetType.CLOSEST, number_of_drones=1, terminal_phases=False,
        seed=seed, pool_size=pool_size, demand_model=demand_model,
    )


def generate_pool(specification: RunSpecification, zones: list[DemandZone], git_hash: str) -> dict | None:
    store = default_result_store()
    generation_seconds = generate_missing_pool(store, specification, zones)
    if generation_seconds is None:
        return None

    pool_path = destination_pool_path(store, specification)
    write_artifact_provenance(pool_path, git_hash, command=" ".join(sys.argv))
    return {
        "demand_model": specification.demand_model.value, "seed": specification.seed,
        "pool_size": specification.pool_size, "generation_seconds": generation_seconds,
        "file_size_bytes": pool_path.stat().st_size, "git_hash": git_hash,
    }


def main():
    arguments = parse_arguments()
    git_hash = ensure_ready_to_run(REPOSITORY_ROOT)
    demand_model = DemandModel(arguments.demand_model)
    zones = load_demand_zones(demand_model)

    timing_rows = []
    for seed in arguments.seeds:
        timing_row = generate_pool(pool_specification(seed, arguments.pool_size, demand_model), zones, git_hash)
        if timing_row is None:
            print(f"seed {seed}: pool already exists", flush=True)
            continue
        timing_rows.append(timing_row)
        print(f"seed {seed}: generated in {timing_row['generation_seconds']:.1f} s", flush=True)

    # Written once at the end so that the working tree stays clean for other batches meanwhile.
    if timing_rows:
        append_table_rows(pd.DataFrame(timing_rows), phase_directory("phase5") / TIMING_TABLE_NAME)


if __name__ == "__main__":
    main()
