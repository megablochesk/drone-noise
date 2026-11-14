#!/bin/bash
# Fine-grid design as a Slurm job array, one run per task. NOT TESTED on a cluster: partition name, module
# and environment lines are assumptions to adapt (CREATE HPC: partition "cpu", 48 h limit per the scheduler
# policy). Before submitting, from the repository root: python -m pytest   (the tasks do not run the suite).
#
# Submit the pilot design for seeds 1-100 (18 tasks per seed, 1,800 tasks, at most 400 at a time):
#   sbatch --array=0-1799%400 --export=ALL,SEEDS="$(seq -s ' ' 1 100)" cluster/fine_grid_array.sbatch
# Submit the design behind the paper's figures (108 tasks per seed; one submission per block of seeds keeps
# the array below the scheduler's limit on array size):
#   sbatch --array=0-1079%400 --export=ALL,DESIGN=paper-figures,SEEDS="$(seq -s ' ' 1 10)" cluster/fine_grid_array.sbatch
# The number of tasks of a design: python -m experiments.revision.run_fine_grid_task --seeds ... --design ... --count
# Afterwards, on a machine that sees the result store, write the run table and draw:
#   python -m experiments.revision.run_fine_grid_pilot --seeds ... --design paper-figures \
#       --table-name paper_figure_runs.csv --collect-only
#   python -m experiments.revision.paper_figures
# Measured on a laptop core: about 10 minutes for the largest fleet and about 1 GB per task.
# The destination pool of every seed must exist first (python -m experiments.revision.generate_order_pools);
# the tasks only read pools. Logs go to slurm-*.out in the repository root, which .gitignore lists: the
# tasks refuse to run from a working tree with other untracked or changed files.
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
python -m experiments.revision.run_fine_grid_task --seeds ${SEEDS} --design "${DESIGN:-pilot}" --task "${SLURM_ARRAY_TASK_ID}"
