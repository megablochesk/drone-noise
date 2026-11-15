#!/bin/bash
# Generates the destination pools of the seeds in SEEDS in one job, before any array of those seeds runs.
# Submit from the repository root with the conda environment active (cluster/README.md, step 5):
#   sbatch --export=ALL,SEEDS="$(seq -s ' ' 31 100)" cluster/order_pools.sbatch
# The generator runs the fast test suite first and refuses a dirty tree. It appends its timings to the tracked
# results/phase5/order_pool_generation.csv, which leaves the tree dirty: move that change aside before the arrays.
# Pools: 650,000 destinations, about 12 MB and 1-2 minutes per seed on a laptop core.
#
# CONFIRM ON THE CLUSTER: partition name, memory and time limit.
#SBATCH --job-name=drone-noise-order-pools
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=08:00:00
#SBATCH --output=slurm-%j.out

set -euo pipefail

fail() {
    echo "order_pools.sbatch: $*" >&2
    exit 1
}

# The pool size of the revision design (REVISION_POOL_SIZE in src/experiments/revision/revision_design.py).
POOL_SIZE=650000

[ -n "${SLURM_SUBMIT_DIR:-}" ] || fail "SLURM_SUBMIT_DIR is not set: submit this script with sbatch"
[ -f "${SLURM_SUBMIT_DIR}/cluster/order_pools.sbatch" ] \
    || fail "submit from the repository root (the job was submitted from ${SLURM_SUBMIT_DIR})"
[ -n "${SEEDS:-}" ] || fail "SEEDS is not set: submit with --export=ALL,SEEDS=\"31 32 33\""

export NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export DRONE_NOISE_MATPLOTLIB_BACKEND=Agg

cd "${SLURM_SUBMIT_DIR}/src"
python -c "import numba, fastparquet, geopandas" \
    || fail "python on PATH ($(command -v python || echo none)) lacks the model's packages: activate the conda environment before sbatch"
# The seeds are separate arguments, so SEEDS stays unquoted.
python -m experiments.revision.generate_order_pools --seeds ${SEEDS} --pool-size "${POOL_SIZE}"
