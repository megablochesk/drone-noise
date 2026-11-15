#!/bin/bash
# Submits a fine-grid design for seeds FIRST..LAST as Slurm job arrays of at most MAX_ARRAY_SIZE tasks, one
# array per block of seeds, each array waiting for the one before it so that at most THROTTLE tasks run at once.
# With --missing only the tasks whose runs are not stored are submitted: run it again after the arrays finish
# until it reports nothing to submit.
#
# Usage, with the conda environment active (from any folder; it submits from the repository root):
#   cluster/submit_design.sh DESIGN FIRST_SEED LAST_SEED [--missing]
# Environment: THROTTLE (default 100) running tasks; MAX_ARRAY_SIZE (default 1000; the cluster's limit is
# MaxArraySize - 1 from `scontrol show config`); EXTRA_SBATCH_OPTIONS, for example "--account=... --time=02:00:00".
set -euo pipefail

usage="usage: cluster/submit_design.sh DESIGN FIRST_SEED LAST_SEED [--missing]"
[ $# -ge 3 ] && [ $# -le 4 ] || { echo "$usage" >&2; exit 2; }
design="$1"
first_seed="$2"
last_seed="$3"
selection="${4:-}"
[ -z "$selection" ] || [ "$selection" = "--missing" ] || { echo "$usage" >&2; exit 2; }
throttle="${THROTTLE:-100}"
max_array_size="${MAX_ARRAY_SIZE:-1000}"

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plan="$(cd "$repository_root/src" && python -m experiments.revision.job_array --design "$design" \
    --seeds $(seq "$first_seed" "$last_seed") --max-array-size "$max_array_size" $selection)"
if [ -z "$plan" ]; then
    echo "nothing to submit: every run of $design for seeds $first_seed-$last_seed is stored"
    exit 0
fi

cd "$repository_root"
previous_job=""
while IFS=$'\t' read -r task_indices seeds; do
    dependency=()
    [ -z "$previous_job" ] || dependency=("--dependency=afterany:${previous_job}")
    # shellcheck disable=SC2086  (EXTRA_SBATCH_OPTIONS holds several options)
    previous_job="$(sbatch --parsable --array="${task_indices}%${throttle}" "${dependency[@]}" ${EXTRA_SBATCH_OPTIONS:-} \
        --export=ALL,DESIGN="${design}",SEEDS="${seeds}" cluster/fine_grid_array.sbatch)"
    previous_job="${previous_job%%;*}"
    echo "submitted job $previous_job: $design, seeds $seeds, tasks $task_indices"
done <<< "$plan"
