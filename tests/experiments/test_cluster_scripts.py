"""The Slurm scripts run on this machine with stand-ins for python and sbatch: what each task executes, and that
every misconfiguration stops the task with a non-zero exit and a message saying what to fix."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.revision.revision_design import REVISION_POOL_SIZE

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARRAY_SCRIPT = REPOSITORY_ROOT / "cluster" / "fine_grid_array.sbatch"
POOL_SCRIPT = REPOSITORY_ROOT / "cluster" / "order_pools.sbatch"
SUBMIT_SCRIPT = REPOSITORY_ROOT / "cluster" / "submit_design.sh"
FAILING_EXIT_STATUS = "3"

STAND_IN_PYTHON = """#!/bin/bash
echo "$PWD|${NUMBA_NUM_THREADS:-}|${OMP_NUM_THREADS:-}|${GIT_OPTIONAL_LOCKS:-}|$*" >> "$STAND_IN_LOG"
case "$1" in
    -c) exit "${STAND_IN_IMPORT_STATUS:-0}" ;;
    -m) exit "${STAND_IN_RUN_STATUS:-0}" ;;
esac
"""
STAND_IN_SBATCH = """#!/bin/bash
echo "$PWD|$*" >> "$STAND_IN_LOG"
echo "1000$(wc -l < "$STAND_IN_LOG")"
"""


def install_stand_in(directory: Path, name: str, script: str) -> Path:
    directory.mkdir(exist_ok=True)
    path = directory / name
    path.write_text(script)
    path.chmod(0o755)
    return path


@pytest.fixture
def stand_in_python(tmp_path) -> dict[str, str]:
    """An environment in which `python` records its working directory, thread settings and arguments."""
    install_stand_in(tmp_path / "bin", "python", STAND_IN_PYTHON)
    return {
        "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin", "HOME": str(tmp_path), "STAND_IN_LOG": str(tmp_path / "calls.log"),
        "SLURM_SUBMIT_DIR": str(REPOSITORY_ROOT), "SLURM_ARRAY_TASK_ID": "36", "SLURM_JOB_ID": "7",
        "SEEDS": "4 5", "DESIGN": "paper-figures",
    }


def run_script(script: Path, environment: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script)], env=environment, capture_output=True, text=True, cwd=REPOSITORY_ROOT)


def read_calls(environment: dict[str, str]) -> list[list[str]]:
    log = Path(environment["STAND_IN_LOG"])
    return [line.split("|") for line in log.read_text().splitlines()] if log.exists() else []


def test_an_array_task_runs_its_task_of_the_design_from_src_on_one_thread(stand_in_python):
    completed = run_script(ARRAY_SCRIPT, stand_in_python)

    assert completed.returncode == 0, completed.stderr
    working_directory, numba_threads, blas_threads, optional_locks, arguments = read_calls(stand_in_python)[-1]
    assert working_directory == str(REPOSITORY_ROOT / "src")
    assert (numba_threads, blas_threads, optional_locks) == ("1", "1", "0")
    assert arguments == "-m experiments.revision.run_fine_grid_task --seeds 4 5 --design paper-figures --task 36"


@pytest.mark.parametrize("variable", ["SEEDS", "DESIGN", "SLURM_ARRAY_TASK_ID", "SLURM_SUBMIT_DIR"])
def test_an_array_task_without_its_settings_stops_and_names_the_missing_one(stand_in_python, variable):
    del stand_in_python[variable]

    completed = run_script(ARRAY_SCRIPT, stand_in_python)

    assert completed.returncode != 0
    assert variable in completed.stderr
    assert not any(call[-1].startswith("-m") for call in read_calls(stand_in_python))


def test_an_array_submitted_from_another_folder_stops(stand_in_python, tmp_path):
    stand_in_python["SLURM_SUBMIT_DIR"] = str(tmp_path)

    completed = run_script(ARRAY_SCRIPT, stand_in_python)

    assert completed.returncode != 0
    assert "repository root" in completed.stderr


def test_an_array_task_without_the_model_environment_stops(stand_in_python):
    stand_in_python["STAND_IN_IMPORT_STATUS"] = "1"

    completed = run_script(ARRAY_SCRIPT, stand_in_python)

    assert completed.returncode != 0
    assert "conda environment" in completed.stderr


def test_a_failing_run_fails_the_array_task(stand_in_python):
    stand_in_python["STAND_IN_RUN_STATUS"] = FAILING_EXIT_STATUS

    assert run_script(ARRAY_SCRIPT, stand_in_python).returncode != 0


def test_the_pool_job_generates_pools_of_the_size_the_design_reads(stand_in_python):
    stand_in_python["SEEDS"] = "31 32"

    completed = run_script(POOL_SCRIPT, stand_in_python)

    assert completed.returncode == 0, completed.stderr
    working_directory, *_, arguments = read_calls(stand_in_python)[-1]
    assert working_directory == str(REPOSITORY_ROOT / "src")
    assert arguments == f"-m experiments.revision.generate_order_pools --seeds 31 32 --pool-size {REVISION_POOL_SIZE}"


def test_the_pool_job_without_seeds_stops(stand_in_python):
    del stand_in_python["SEEDS"]

    completed = run_script(POOL_SCRIPT, stand_in_python)

    assert completed.returncode != 0
    assert "SEEDS" in completed.stderr


@pytest.fixture
def stand_in_sbatch(tmp_path) -> dict[str, str]:
    """The real python of this environment and an `sbatch` that records its arguments and prints a job number."""
    install_stand_in(tmp_path / "bin", "sbatch", STAND_IN_SBATCH)
    return {
        "PATH": f"{tmp_path / 'bin'}:{Path(sys.executable).parent}:/usr/bin:/bin", "HOME": str(tmp_path),
        "STAND_IN_LOG": str(tmp_path / "sbatch.log"), "THROTTLE": "50",
        **{name: value for name, value in os.environ.items() if name.startswith(("CONDA", "PROJ", "GDAL"))},
    }


def test_a_design_is_submitted_as_chained_arrays_from_the_repository_root(stand_in_sbatch):
    """60 pilot seeds are 1,080 runs: an array of 55 seeds (990 tasks), then one of 5 seeds that waits for it,
    so no more than THROTTLE tasks of the design run at once."""
    completed = subprocess.run(
        ["bash", str(SUBMIT_SCRIPT), "pilot", "1", "60"], env=stand_in_sbatch, capture_output=True, text=True,
        cwd=REPOSITORY_ROOT / "src",
    )

    assert completed.returncode == 0, completed.stderr
    first, second = [line.split("|") for line in Path(stand_in_sbatch["STAND_IN_LOG"]).read_text().splitlines()]
    seeds_of_first = " ".join(str(seed) for seed in range(1, 56))
    assert first == [
        str(REPOSITORY_ROOT),
        f"--parsable --array=0-989%50 --export=ALL,DESIGN=pilot,SEEDS={seeds_of_first} cluster/fine_grid_array.sbatch",
    ]
    assert second == [
        str(REPOSITORY_ROOT),
        "--parsable --array=0-89%50 --dependency=afterany:10001 --export=ALL,DESIGN=pilot,SEEDS=56 57 58 59 60 "
        "cluster/fine_grid_array.sbatch",
    ]
