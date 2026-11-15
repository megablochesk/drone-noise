## How to run

1. Install required packages
    ```bash
    pip install -r requirements.txt
    ```

2. Configure runs in `src/common/simulation_configs.py` (orders, drones, routing, noise map) and `src/common/model_configs.py` (cell size, time step, drone, warehouses)

3. Run the application in `src/application.py`

## Data

No data file is kept in this repository. The model reads its inputs from `src/recourses/`; every file it
needs is listed in `src/datasets/data_catalogue.py` and, with size and SHA-256, in `DATA_MANIFEST.csv`.

| Origin | Meaning | What to do when a file is missing |
|---|---|---|
| external | obtained outside this repository | place it at the path given in the manifest |
| published | written once for the paper by unseeded or long-running scripts | obtain the published file; regenerating it gives different data |
| derived | computed from other files | generated automatically |
| cache | built by the noise-based navigation on first use | nothing |

Check the data, and generate the derived files that are missing, from `src/`:

```bash
python -m datasets.prepare_data             # generate missing derived files, list what is still missing
python -m datasets.prepare_data --verify    # also compare external and published files with DATA_MANIFEST.csv
```

The derived cell tables are also computed on first use if they are missing (population: seconds; age and ethnicity at 500 m: the slower cell-by-cell calculation).

Two baseline noise maps can be used (`BaselineNoiseMap`): the published one (default) and Defra Round 4 road
noise, LAeq,16h. The Round 4 raster is the one external file that can be fetched by a script:

```bash
python -m datasets.download_round4_road_noise   # 42 tiles from the Defra WCS, merged into one GeoTIFF
python -m datasets.round4_baseline              # 500 m baseline from the raster (any cell size is built on first use)
```
After replacing an input on purpose, run `python -m datasets.prepare_data --write-manifest`.

The seeded order pools of the revision experiments are not part of the catalogue; they are written on demand
by `python -m experiments.revision.generate_order_pools` and are a deterministic function of their seed.

## Revision design: Round 4 baseline, 100 m cells, 10 s step

Run parameters live in `RunSpecification` (`src/experiments/revision/run_specification.py`); every default
reproduces the published model. The revision design changes four of them: `baseline_noise_map` (Round 4 road
noise), `noise_cell_m` (100), `time_step_s` (10) and `boundary_datum` (`OSGB36`). The boundary file holds OSGB36
latitudes and longitudes; the published model reads them as WGS84 (`boundary_datum` `WGS84`, the default), which
puts the study area about 110 m east and 55 m south of the census extent. The cell origin is the same under both
readings; the census tables of the OSGB36 grid are files of their own (`cell_population_100_osgb36.pkl` and
the like). `land_once_at_customer` removes the second climb and
descent that the published model flies at the customer; `navigation` selects noise-aware routing on the run's
baseline map (default straight-line). `run_fine_grid_pilot` and `run_fine_grid_task` take `--design` (`pilot`,
`single-landing`, `slant-floor`, `noise-aware`, `paper-figures`); `python -m experiments.revision.paper_figures` redraws the
paper's figures as EPS.

On one machine, from `src/` (refuses uncommitted code, runs the fast suite first, skips stored runs):

```bash
python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --workers 3
python -m experiments.revision.summarise_fine_grid
```

On a cluster, one run per array task (`cluster/fine_grid_array.sbatch`, untested; a task takes about ten
minutes for the largest fleet and about 1 GB on a laptop core):

```bash
python -m pytest                                                        # once, before submitting
sbatch --array=0-1799%400 --export=ALL,SEEDS="$(seq -s ' ' 1 100)" cluster/fine_grid_array.sbatch
```

Each seed needs its order pool, about 10 s per pool:
`python -m experiments.revision.generate_order_pools --seeds 1 2 3 --pool-size 650000`.

### Results kept for figures

Every run is stored once in the result store (`results/artifacts/`, not under version control) and nothing
else is needed to redraw or change a figure:

- `runs/<key>.json`: the run's specification, commit, metrics and the fingerprint of its grid;
- `runs/<key>_drone_levels.npz`: the drone-only level of every cell (about 1.2 MB at 100 m), from which any
  exposure metric, threshold or map can be recomputed against any baseline;
- `runs/<key>_trips.parquet`: the distance of every delivered trip;
- `grids/<fingerprint>.npz`: each grid a map was computed on (cell rows, columns and centres), so a map stays
  readable if the study boundary or the grid changes;
- `order_pools/`: the destination pool of each seed (regenerable from the seed).

A run is addressed by a key computed from its specification, so the store can be copied between machines and
merged by copying files; a run that is stored is never computed again. The design behind the paper's figures
is 108 runs per seed, about 145 MB per seed (about 15 GB for 100 seeds).

From the store to the figures, for any set of seeds that is complete in the store:

```bash
python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --design paper-figures \
    --table-name paper_figure_runs.csv --collect-only     # the run table, without running anything
python -m experiments.revision.paper_figures               # EPS figures, each the mean over the seeds
python -m experiments.revision.build_artifact_manifest     # size, checksum, commit and command of every file
```

## Tests

From the repository root:

```bash
python -m pytest            # fast suite (needs all data)
python -m pytest -m slow    # slow checks: the published results over the whole day (needs all data)
```

The fast suite checks the published runs over their first 15 simulated minutes against stored reference
slices (`tests/regression/data/published_slices`), and the real navigation graph, Round 4 grid and census
tables on fixed samples of depots, customers and cells. The slow suite keeps what only a full-size run can
show: the four published straight-line results and the published noise-aware result over the whole day, the
warehouse route trees on the real graph against the stored cache, and the published grid code against the
stored grid. When a change moves the slices while the slow regression tests still pass, regenerate the slices
at that commit: `python tests/regression/generate_published_slices.py`.
