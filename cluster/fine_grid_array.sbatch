#!/bin/bash
# One run of a fine-grid design per task of a Slurm job array. Submit with cluster/submit_design.sh, which splits
# a design into arrays of valid size; cluster/README.md is the runbook. Not yet run on a cluster: the lines under
# "CONFIRM ON THE CLUSTER" are assumptions, and sbatch options on the command line or in SBATCH_* variables
# (SBATCH_PARTITION, SBATCH_ACCOUNT, SBATCH_TIMELIMIT) override them without editing this tracked file.
#
# Each task runs, from src/:
#   python -m experiments.revision.run_fine_grid_task --seeds $SEEDS --design $DESIGN --task $SLURM_ARRAY_TASK_ID
# The task refuses a working tree with uncommitted or untracked files, records the commit in its row, and ends
# successfully at once when its run is already stored. It does not run the test suite: run python -m pytest once
# before submitting. The python on PATH at submission runs the task (sbatch passes the submitting shell's
# environment), so activate the conda environment before sbatch.
#
# Resources: the slowest stored fine-grid run took 21 minutes on a laptop core and about 1 GB of memory.
# Logs: slurm-<job>_<task>.out in the repository root, which .gitignore lists.
#
# CONFIRM ON THE CLUSTER: partition name, time limit (the smoke tasks' wall_time_s show the margin), memory.
#SBATCH --job-name=drone-noise-fine-grid
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%A_%a.out

set -euo pipefail

fail() {
    echo "fine_grid_array.sbatch: $*" >&2
    exit 1
}

[ -n "${SLURM_SUBMIT_DIR:-}" ] || fail "SLURM_SUBMIT_DIR is not set: submit this script with sbatch"
[ -f "${SLURM_SUBMIT_DIR}/cluster/fine_grid_array.sbatch" ] \
    || fail "submit from the repository root (the job was submitted from ${SLURM_SUBMIT_DIR})"
[ -n "${SLURM_ARRAY_TASK_ID:-}" ] || fail "SLURM_ARRAY_TASK_ID is not set: submit as a job array (--array)"
[ -n "${SEEDS:-}" ] || fail "SEEDS is not set: submit with --export=ALL,DESIGN=...,SEEDS=\"1 2 3\""
[ -n "${DESIGN:-}" ] || fail "DESIGN is not set: submit with --export=ALL,DESIGN=...,SEEDS=\"1 2 3\""

export NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export DRONE_NOISE_MATPLOTLIB_BACKEND=Agg
# Hundreds of tasks read one repository: git status must not take the index lock to refresh it.
export GIT_OPTIONAL_LOCKS=0

cd "${SLURM_SUBMIT_DIR}/src"
python -c "import numba, fastparquet, geopandas" \
    || fail "python on PATH ($(command -v python || echo none)) lacks the model's packages: activate the conda environment before sbatch"
echo "host $(hostname) python $(command -v python) commit $(git rev-parse --short HEAD) design ${DESIGN} seeds ${SEEDS} task ${SLURM_ARRAY_TASK_ID}"
# The seeds are separate arguments, so SEEDS stays unquoted.
python -m experiments.revision.run_fine_grid_task --seeds ${SEEDS} --design "${DESIGN}" --task "${SLURM_ARRAY_TASK_ID}"
