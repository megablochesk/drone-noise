## How to run

1. Install required packages
    ```bash
    pip install -r requirements.txt
    ```

2. Configure simulation settings. You can set the number of orders, number of drones, locations of warehouses, prioritizing factor K or P and size of cells in `src/commons/configurations.py`

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

The derived cell tables are also computed on first use if they are missing (population: several minutes).

Two baseline noise maps can be used (`BaselineNoiseMap`): the published one (default) and Defra Round 4 road
noise, LAeq,16h. The Round 4 raster is the one external file that can be fetched by a script:

```bash
python -m datasets.download_round4_road_noise   # 42 tiles from the Defra WCS, merged into one GeoTIFF
python -m datasets.round4_baseline              # 500 m baseline from the raster (also built on first use)
```
After replacing an input on purpose, run `python -m datasets.prepare_data --write-manifest`.

The seeded order pools of the revision experiments are not part of the catalogue; they are written on demand
by `python -m experiments.revision.generate_order_pools` and are a deterministic function of their seed.

## Tests

From the repository root:

```bash
python -m pytest            # fast suite
python -m pytest -m slow    # full-size regression runs against the published results (needs all data)
```
