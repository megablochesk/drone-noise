import importlib
import json
import os
from functools import lru_cache

import numpy as np
import pandas as pd

from common.enum import BaselineNoiseMap
from common.model_configs import model_config
from common.path_configs import BASE_NOISE_PATH, PATH_CONFIGS
from noise.noise_math_utils import add_two_decibel_levels, calculate_leq


PUBLISHED_CELL_SIZE_M = model_config.grid.noise_cell_m
PARQUET_SUFFIX = ".parquet"
PARQUET_ENGINE = "fastparquet"
BASE_NOISE_PATH_BUILDERS = {
    BaselineNoiseMap.PUBLISHED: PATH_CONFIGS.base_noise_path,
    BaselineNoiseMap.ROUND_4_ROAD: PATH_CONFIGS.round4_base_noise_path,
    BaselineNoiseMap.ROUND_4_ROAD_ENERGY: PATH_CONFIGS.round4_energy_base_noise_path,
}
# 'package.module:function' that writes the file of a map derived from other data; imported only when needed.
ROUND4_BASELINE_GENERATOR = "datasets.round4_baseline:write_round4_baseline_file"
BASE_NOISE_GENERATORS = {
    BaselineNoiseMap.ROUND_4_ROAD: ROUND4_BASELINE_GENERATOR,
    BaselineNoiseMap.ROUND_4_ROAD_ENERGY: ROUND4_BASELINE_GENERATOR,
}


def find_base_noise_path(baseline_noise_map: BaselineNoiseMap, cell_size_m: int = PUBLISHED_CELL_SIZE_M) -> str:
    return BASE_NOISE_PATH_BUILDERS[baseline_noise_map](cell_size_m)


def generate_base_noise_file(baseline_noise_map: BaselineNoiseMap, cell_size_m: int):
    module_name, function_name = BASE_NOISE_GENERATORS[baseline_noise_map].split(":")
    getattr(importlib.import_module(module_name), function_name)(baseline_noise_map, cell_size_m)


def read_base_noise_data(file_path: str = BASE_NOISE_PATH) -> pd.DataFrame:
    if file_path.endswith(PARQUET_SUFFIX):
        return pd.read_parquet(file_path, engine=PARQUET_ENGINE)

    with open(file_path, 'r') as f:
        data = json.load(f)

    records = []
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        records.append({
            'row': props.get('row', 0),
            'col': props.get('col', 0),
            'noise_level': props.get('noise_level', 0.0),
            'geometry': geometry
        })

    return pd.DataFrame(records)


@lru_cache(maxsize=None)
def load_base_noise_file_once(baseline_noise_map: BaselineNoiseMap, cell_size_m: int) -> pd.DataFrame:
    file_path = find_base_noise_path(baseline_noise_map, cell_size_m)
    if not os.path.exists(file_path) and baseline_noise_map in BASE_NOISE_GENERATORS:
        generate_base_noise_file(baseline_noise_map, cell_size_m)

    return read_base_noise_data(file_path)


def load_base_noise_data(
        baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED, cell_size_m: int = PUBLISHED_CELL_SIZE_M
) -> pd.DataFrame:
    return load_base_noise_file_once(baseline_noise_map, cell_size_m)


def generate_drone_noise_df(drone_noise_data) -> pd.DataFrame:
    records = [
        {
            "row": cell.row,
            "col": cell.column,
            "average_noise": calculate_leq(np.array(cell.noise_history)),
            "maximum_noise": cell.max_noise,
        }
        for cell in drone_noise_data
    ]

    return pd.DataFrame(records).set_index(['row', 'col'])


def combine_noise_levels(drone_noise_df: pd.DataFrame, base_noise_df: pd.DataFrame) -> pd.DataFrame:
    merged_df = pd.merge(
        drone_noise_df,
        base_noise_df,
        on=['row', 'col'],
        how='inner',
        suffixes=('_drone', '_base')
    )

    merged_df['combined_noise'] = merged_df.apply(
        lambda x: add_two_decibel_levels(x['average_noise'], x['noise_level']),
        axis=1
    )

    merged_df['noise_difference'] = merged_df['combined_noise'] - merged_df['noise_level']

    return merged_df


def combine_base_and_drone_noise(
        drone_noise_data, baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED
) -> pd.DataFrame:
    drone_noise_df = generate_drone_noise_df(drone_noise_data)

    return combine_noise_levels(drone_noise_df, load_base_noise_data(baseline_noise_map))
