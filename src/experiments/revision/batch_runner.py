"""Runs the missing specifications of a batch in worker processes and returns the table of all its rows."""
from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import pandas as pd

from common.path_configs import PATH_CONFIGS
from experiments.revision.result_store import ResultStore, collect_rows, has_result
from experiments.revision.run_executor import execute_run
from experiments.revision.run_guard import ensure_ready_to_run
from experiments.revision.run_specification import RunSpecification, build_run_key

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NUMBA_THREADS_VARIABLE = "NUMBA_NUM_THREADS"
MATPLOTLIB_BACKEND_VARIABLE = "DRONE_NOISE_MATPLOTLIB_BACKEND"
HEADLESS_MATPLOTLIB_BACKEND = "Agg"


def default_result_store() -> ResultStore:
    return ResultStore(Path(PATH_CONFIGS.revision_artifacts_dir))


def select_pending_specifications(specifications: list[RunSpecification], store: ResultStore) -> list[RunSpecification]:
    unique_by_key = {build_run_key(specification): specification for specification in specifications}
    return [specification for run_key, specification in unique_by_key.items() if not has_result(store, run_key)]


def execute_and_report(specification: RunSpecification, store: ResultStore, git_hash: str) -> str:
    row = execute_run(specification, store, git_hash)
    return (
        f"{row['run_key']} {row['stocking']:8s} drones={row['number_of_drones']:4d} seed={row['seed']:2d} "
        f"terminal={row['terminal_phases']!s:5s} delivered={row['delivered_orders']:6d} "
        f"increase={row['mean_noise_increase_db']:.3f} dB wall={row['wall_time_s']:.0f} s"
    )


def run_in_worker_processes(
        pending: list[RunSpecification], store: ResultStore, git_hash: str, number_of_workers: int
) -> list[str]:
    """Returns one failure description per run that raised; the other runs are stored."""
    # One numba thread per worker: the simulation is single-threaded anyway and workers must not oversubscribe.
    os.environ[NUMBA_THREADS_VARIABLE] = "1"
    os.environ[MATPLOTLIB_BACKEND_VARIABLE] = HEADLESS_MATPLOTLIB_BACKEND
    failures = []
    with ProcessPoolExecutor(max_workers=number_of_workers, mp_context=get_context("spawn")) as pool:
        futures = {pool.submit(execute_and_report, specification, store, git_hash): specification for specification in pending}
        for finished, future in enumerate(as_completed(futures), start=1):
            try:
                print(f"[{time.strftime('%H:%M:%S')}] {finished}/{len(pending)} {future.result()}", flush=True)
            except Exception as error:
                failures.append(f"{build_run_key(futures[future])}: {error!r}")
                print(f"[{time.strftime('%H:%M:%S')}] {finished}/{len(pending)} FAILED {failures[-1]}", flush=True)
    return failures


def run_pending_specifications(
        specifications: list[RunSpecification], store: ResultStore, git_hash: str, number_of_workers: int
) -> list[str]:
    pending = select_pending_specifications(specifications, store)
    print(f"{len(specifications) - len(pending)} of {len(specifications)} runs already stored", flush=True)
    if number_of_workers == 1:
        for specification in pending:
            print(execute_and_report(specification, store, git_hash), flush=True)
        return []
    return run_in_worker_processes(pending, store, git_hash, number_of_workers)


def run_guarded_batch(specifications: list[RunSpecification], number_of_workers: int) -> pd.DataFrame:
    """Refuses to start on uncommitted code or a failing fast suite; raises if any run failed."""
    git_hash = ensure_ready_to_run(REPOSITORY_ROOT)
    store = default_result_store()
    failures = run_pending_specifications(specifications, store, git_hash, number_of_workers)
    if failures:
        raise RuntimeError("Some runs failed:\n" + "\n".join(failures))
    return collect_rows(store, [build_run_key(specification) for specification in specifications])
