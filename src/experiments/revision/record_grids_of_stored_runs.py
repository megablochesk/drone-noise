"""Records, for every stored run that names no grid, the grid its map was computed on.

The grid is the present one of the run's cell size, so this is only right while the study boundary and the
cell sizes are those the runs were made with. Runs record their grid themselves when they are executed.

Usage (from src/): python -m experiments.revision.record_grids_of_stored_runs
"""
from experiments.revision.batch_runner import default_result_store
from experiments.revision.result_store import RUN_ROW_SUFFIX, load_row, record_grid_of_stored_run
from experiments.revision.run_specification import PUBLISHED_NOISE_CELL_M
from noise.noise_grid import load_noise_grid


def main():
    store = default_result_store()
    run_keys = sorted(path.name.removesuffix(RUN_ROW_SUFFIX) for path in store.runs_directory.glob(f"*{RUN_ROW_SUFFIX}"))
    recorded = sum(
        record_grid_of_stored_run(store, run_key, load_noise_grid(load_row(store, run_key).get("noise_cell_m", PUBLISHED_NOISE_CELL_M)))
        for run_key in run_keys
    )
    print(f"{recorded} of {len(run_keys)} stored runs had no grid recorded and now name it")


if __name__ == "__main__":
    main()
