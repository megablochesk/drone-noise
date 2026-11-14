#!/bin/bash
# Fine-grid design as a Slurm job array, one run per task. NOT TESTED on a cluster: partition name, module
# and environment lines are assumptions to adapt (CREATE HPC: partition "cpu", 48 h limit per the scheduler
# policy). Before submitting, from the repository root: python -m pytest   (the tasks do not run the suite).
#
# Submit for seeds 1-100 (18 tasks per seed, 1,800 tasks, at most 400 at a time):
#   sbatch --array=0-1799%400 --export=ALL,SEEDS="$(seq -s ' ' 1 100)" cluster/fine_grid_array.sbatch
# Measured on a laptop core: under 10 minutes and about 1 GB per task.
#SBATCH --job-name=drone-noise-fine-grid
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%A_%a.out

set -euo pipefail
export NUMBA_NUM_THREADS=1
export DRONE_NOISE_MATPLOTLIB_BACKEND=Agg

cd "${SLURM_SUBMIT_DIR}/src"
python -m experiments.revision.run_fine_grid_task --seeds ${SEEDS} --task "${SLURM_ARRAY_TASK_ID}"
