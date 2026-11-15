# Running the 100-seed fine-grid experiment on KCL CREATE HPC

This runbook goes from a fresh login to the run tables and figures. No step has yet been run on CREATE.
Anything marked **CONFIRM** is an assumption the saved CREATE pages do not settle. Those pages are a node list
(most CPU nodes have 128 cores and 1 TB of memory; some have 32 cores and 190 GB), the "Stats" page, and a
"Scheduler Policy" page that was saved as a 404. Partition names, time limits, array limits, quotas and module
names therefore come from `sinfo`, `scontrol` and the CREATE documentation (Running Jobs, Scheduler Policy,
Storage, Software → Python), not from this file.

The scripts:

| file | what it does |
|---|---|
| `fine_grid_array.sbatch` | one run of a design per array task: `run_fine_grid_task --seeds $SEEDS --design $DESIGN --task $SLURM_ARRAY_TASK_ID` |
| `submit_design.sh` | submits a design for a range of seeds as chained arrays of valid size; `--missing` resubmits only unstored runs |
| `order_pools.sbatch` | generates the destination pools of new seeds, once, before the arrays |
| `environment.yml` | the pinned conda environment that produced the stored runs |

Tasks refuse a working tree with any uncommitted or untracked file, so **never edit or commit tracked files on
the cluster**. Set cluster-specific options with `SBATCH_*` variables or `EXTRA_SBATCH_OPTIONS` (step 6), not
by editing the scripts. Every row records the commit it ran on, and that commit exists on the laptop because
the code arrives as a bundle of the laptop branch.

## What runs, and what it costs

These sizes come from the stored run tables in `results/fine_grid/`. Times are wall time on one laptop core
while three runs shared the machine. The slowest run took 21 minutes; every run uses about 1 GB of memory and
about 1.4 MB of store.

| design | runs per seed | core-hours per seed (source table) | 100 seeds: runs | core-hours | store |
|---|---|---|---|---|---|
| paper-figures | 108 | 8.94 (`paper_figure_runs.csv`, seed 1) | 10,800 | 894 | 14.4 GB |
| single-landing | 9 | 1.30 (`single_landing_runs.csv`, 3.89 for seeds 1-3) | 900 | 130 | 1.2 GB |
| slant-floor | 3 | 0.79 (`slant_floor_runs.csv`, seed 1) | 300 | 79 | 0.4 GB |
| pilot | 18 | 2.64 (`runs.csv`, 7.92 for seeds 1-3) | 1,800 | (264) | contained in paper-figures |
| noise-aware | 12 | 0.93 (`noise_aware_runs.csv`, seed 1) | 1,200 | (93) | contained in paper-figures |

The pilot and noise-aware runs are all part of paper-figures (same run keys), so submitting paper-figures,
single-landing and slant-floor covers all five designs. That comes to 12,000 runs, about **1,100 core-hours**
and about **17 GB** of store. New pools for seeds 31-100 add 70 × 12 MB = 0.8 GB, and the job logs add
12,000 small files. Runs that are already stored (seeds 1-3 of several designs) are skipped, so they cost
nothing.

Wall time: `submit_design.sh` chains the arrays of a design so that at most `THROTTLE` tasks run at once. If
the scheduler grants all of them, wall time ≈ core-hours / `THROTTLE`. That is about 11 h at 100 and about
5.5 h at 200, plus queueing, plus a short tail per array (each array ends with its smallest fleets). These are
laptop-core figures: the smoke test in step 7 measures a CREATE core.

## 1. On the laptop: pack code, inputs and store

Wait until no batch is running, so that the store is complete and the tree is clean. Then, from the
repository root:

```bash
mkdir -p ~/drone-noise-transfer
git status --short                      # must print nothing
git bundle create ~/drone-noise-transfer/drone-noise.bundle revision/mc-pilot
cd src
python -c "import pandas as pd; print('\n'.join(pd.read_csv('../DATA_MANIFEST.csv').path))" > ~/drone-noise-transfer/input_files.txt
ls recourses/data/noise_graph_navigation/warehouse_paths_cache__mixed__*.pkl >> ~/drone-noise-transfer/input_files.txt
tar -cf ~/drone-noise-transfer/inputs.tar -T ~/drone-noise-transfer/input_files.txt
xargs -a ~/drone-noise-transfer/input_files.txt sha256sum > ~/drone-noise-transfer/inputs.sha256
cd ../results
tar -cf ~/drone-noise-transfer/store.tar artifacts
find artifacts -type f -print0 | xargs -0 sha256sum > ~/drone-noise-transfer/store.sha256
cd ~/drone-noise-transfer && sha256sum drone-noise.bundle inputs.tar store.tar > archives.sha256
```

| file | content | size |
|---|---|---|
| `drone-noise.bundle` | the branch with its history, including the tracked results and the pools of seeds 1-30 | about 0.65 GB |
| `inputs.tar` | the 36 files of `DATA_MANIFEST.csv` and the four noise-aware route caches (not in the manifest; without them every noise-aware task rebuilds them) | 0.83 GB |
| `store.tar` | `results/artifacts`: runs, grids and pools, including the ignored files | about 1 GB |

## 2. Copy to CREATE

```bash
rsync -av --progress ~/drone-noise-transfer/ <k-number>@hpc.create.kcl.ac.uk:<work-directory>/drone-noise-transfer/
```

**CONFIRM**: the login host name, and which file system to work in. The repository, its store (about 20 GB at
the end) and about 50,000 small files belong where the quota allows it and every compute node sees it (see
CREATE Storage). Every path below is relative to that work directory.

## 3. Unpack and verify

```bash
cd <work-directory>/drone-noise-transfer
sha256sum -c archives.sha256
cd ..
git clone -b revision/mc-pilot drone-noise-transfer/drone-noise.bundle drone-noise
cd drone-noise
git log --oneline -1                    # the commit the laptop had at step 1
(cd src && tar -xf ../../drone-noise-transfer/inputs.tar && sha256sum --quiet -c ../../drone-noise-transfer/inputs.sha256)
(cd results && tar -xf ../../drone-noise-transfer/store.tar && sha256sum --quiet -c ../../drone-noise-transfer/store.sha256)
git status --short                      # must print nothing: inputs, store and logs are all ignored
```

`sha256sum --quiet -c` prints only mismatches and exits non-zero on any of them.

## 4. Environment

```bash
module avail 2>&1 | grep -i -E "conda|mamba|python"     # CONFIRM the module name; CREATE documents it under Software → Python
module load <anaconda-module>
conda env create -f cluster/environment.yml             # once; creates the environment "drone-noise"
conda activate drone-noise                              # or `source activate drone-noise`, as the module documents
cd src
python -m datasets.prepare_data --verify                # expect "all catalogued data files are present" and exit 0
cd ..
python -m pytest                                        # the fast suite; the tasks do not run it
git status --short                                      # still nothing
```

`environment.yml` uses the conda-forge and defaults channels and pins every version. If the defaults channel is
unavailable on CREATE, remove it and retry (**CONFIRM**). Run the suite on a compute node (`srun --pty`, or a
one-line batch job) if the login nodes limit CPU time (**CONFIRM**).

## 5. Destination pools for seeds 31-100

The bundle holds the pools of seeds 1-30. Generate the others in one job. The job runs the fast suite first.

```bash
sbatch --export=ALL,SEEDS="$(seq -s ' ' 31 100)" cluster/order_pools.sbatch
# when it has finished (sacct -j <job>; log in slurm-<job>.out):
ls results/artifacts/order_pools/destinations_population_seed{1..100}_n650000.parquet > /dev/null && echo all pools present
cp results/phase5/order_pool_generation.csv ../order_pool_generation_cluster.csv
git checkout -- results/phase5/order_pool_generation.csv
git status --short                      # nothing again
```

The generator appends its timings to that tracked table. Without the last step the tree is dirty and every
array task refuses to start. The copy keeps the timings.

## 6. Cluster settings for this shell

```bash
export SBATCH_PARTITION=<cpu-partition>        # CONFIRM with sinfo; the scripts name "cpu"
export SBATCH_ACCOUNT=<account>                # only if CREATE requires one (CONFIRM)
scontrol show config | grep -i -E "MaxArraySize|MaxJobCount"
export MAX_ARRAY_SIZE=1000                     # MaxArraySize - 1; 1000 matches Slurm's default of 1001
export THROTTLE=100                            # tasks of one design running at once
sacctmgr show assoc user=$USER format=user,account,partition,maxjobs,maxsubmit 2>/dev/null
```

**CONFIRM** the per-user limits. Each array task counts as one job, and every array is submitted at once (the
later ones wait on a dependency), so a limit on submitted jobs below 10,800 refuses the later paper-figures
arrays. In that case submit seeds in ranges, for example `1 50` and later `51 100`.

## 7. Smoke test: two tasks

Seed 4 has a stored pool and no stored runs. Task 2 is the slowest run in the stored tables (1,250 drones, random
stocking). Task 36 is a noise-aware run, which reads the route caches.

```bash
sbatch --array=2,36 --export=ALL,DESIGN=paper-figures,SEEDS=4 cluster/fine_grid_array.sbatch
# afterwards:
sacct -j <job> --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 3 slurm-<job>_2.out slurm-<job>_36.out
git status --short                      # nothing
```

Both tasks must be `COMPLETED` with exit code 0. Their logs end with a line containing `wall=... s`.
`Elapsed` gives the time limit's margin: raise `--time` (with `EXTRA_SBATCH_OPTIONS="--time=02:00:00"`) if
task 2 used more than half of the 1 h limit. `MaxRSS` checks the 3 GB request. Resubmit the same command: both
tasks must finish within a minute, printing `1 of 1 runs already stored`.

## 8. The full arrays

```bash
cluster/submit_design.sh paper-figures 1 100       # 12 arrays: 11 of 9 seeds (972 tasks), 1 of 1 seed
cluster/submit_design.sh single-landing 1 100      # 1 array of 100 seeds (900 tasks)
cluster/submit_design.sh slant-floor 1 100         # 1 array of 100 seeds (300 tasks)
squeue -u $USER
```

Each design's arrays run one after another. The three designs run side by side, so up to 3 × `THROTTLE`
tasks run at once. To run them one after another instead, submit the next design after the previous one
finishes. `python -m experiments.revision.job_array --design <design> --seeds $(seq 1 100)` (from `src/`) prints
the plan without submitting.

## 9. Missing tasks and resubmission

When `squeue -u $USER` is empty:

```bash
sacct -S <start-date> -X --state=FAILED,TIMEOUT,OUT_OF_MEMORY,NODE_FAIL --format=JobID,State,ExitCode | head
cluster/submit_design.sh paper-figures 1 100 --missing
cluster/submit_design.sh single-landing 1 100 --missing
cluster/submit_design.sh slant-floor 1 100 --missing
```

`--missing` submits only tasks whose run has no stored row. It prints `nothing to submit` once a design is
complete. A run counts as stored only when its row is written, and the row is written last, after the map and
the trip log. So a task that was killed, timed out or failed counts as missing and simply runs again. Read the
log of a failed task before resubmitting: if the same task fails twice, the cause is not the cluster.

## 10. Copy the runs back, then collect and draw on the laptop

On CREATE, from the repository root:

```bash
cd results && find artifacts -type f -newer ../../drone-noise-transfer/store.tar -print0 | xargs -0 sha256sum > ../../new_runs.sha256
tar -cf ../../new_runs.tar -T <(cut -c67- ../../new_runs.sha256)
```

On the laptop, from the repository root, with no batch running:

```bash
rsync -av <k-number>@hpc.create.kcl.ac.uk:<work-directory>/{new_runs.tar,new_runs.sha256,order_pool_generation_cluster.csv} ~/drone-noise-transfer/
cd results && tar --skip-old-files -xf ~/drone-noise-transfer/new_runs.tar && sha256sum --quiet -c ~/drone-noise-transfer/new_runs.sha256
cd ../src
python -m experiments.revision.run_fine_grid_pilot --seeds $(seq 1 100) --design paper-figures --table-name paper_figure_runs.csv --collect-only
python -m experiments.revision.run_fine_grid_pilot --seeds $(seq 1 100) --design pilot --table-name runs.csv --collect-only
python -m experiments.revision.run_fine_grid_pilot --seeds $(seq 1 100) --design noise-aware --table-name noise_aware_runs.csv --collect-only
python -m experiments.revision.run_fine_grid_pilot --seeds $(seq 1 100) --design single-landing --table-name single_landing_runs.csv --collect-only
python -m experiments.revision.run_fine_grid_pilot --seeds $(seq 1 100) --design slant-floor --table-name slant_floor_runs.csv --collect-only
python -m experiments.revision.paper_figures
```

`--skip-old-files` never overwrites a file the laptop already holds; the checksum check then reports any such file whose content differs. Collection fails if any run of a design is missing,
so a table never drops a run silently. The new tables and figures are then committed on the laptop as usual.
The new pools and runs stay in the ignored part of `results/artifacts`. Rebuild the artefact manifest with
`python -m experiments.revision.build_artifact_manifest`.
