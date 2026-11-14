import importlib
import json
import os
from functools import lru_cache

import numpy as np
import pandas as pd

from common.enum import BaselineNoiseMap
from common.path_configs import BASE_NOISE_PATH, ROUND4_BASE_NOISE_PATH
from noise.noise_math_utils import add_two_decibel_levels, calculate_leq


BASE_NOISE_PATHS = {
    BaselineNoiseMap.PUBLISHED: BASE_NOISE_PATH,
    BaselineNoiseMap.ROUND_4_ROAD: ROUND4_BASE_NOISE_PATH,
}
# 'package.module:function' that writes the file of a map derived from other data; imported only when needed.
BASE_NOISE_GENERATORS = {BaselineNoiseMap.ROUND_4_ROAD: "datasets.round4_baseline:write_round4_baseline_file"}


def find_base_noise_path(baseline_noise_map: BaselineNoiseMap) -> str:
    return BASE_NOISE_PATHS[baseline_noise_map]


def generate_base_noise_file(baseline_noise_map: BaselineNoiseMap):
    module_name, function_name = BASE_NOISE_GENERATORS[baseline_noise_map].split(":")
    getattr(importlib.import_module(module_name), function_name)()


def read_base_noise_data(file_path: str = BASE_NOISE_PATH) -> pd.DataFrame:
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
def load_base_noise_file_once(baseline_noise_map: BaselineNoiseMap) -> pd.DataFrame:
    file_path = find_base_noise_path(baseline_noise_map)
    if not os.path.exists(file_path) and baseline_noise_map in BASE_NOISE_GENERATORS:
        generate_base_noise_file(baseline_noise_map)

    return read_base_noise_data(file_path)


def load_base_noise_data(baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED) -> pd.DataFrame:
    return load_base_noise_file_once(baseline_noise_map)


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
