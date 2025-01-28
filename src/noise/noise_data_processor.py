import json
import os

import pandas as pd
from common.configuration import BASE_NOISE_PATH
from noise.noise_math_utils import add_two_decibel_levels


def read_drone_noise_data(result_path: str):
    return pd.read_csv(os.path.join(result_path, 'noise.csv'))


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

    base_noise_df = pd.DataFrame(records)
    return base_noise_df


def generate_drone_noise_df(matrix_df: pd.DataFrame) -> pd.DataFrame:
    renamed_df = matrix_df.rename(columns={
        'avg_noise': 'average_noise',
        'max_noise': 'maximum_noise'
    })

    return renamed_df.set_index(['row', 'col'])


def combine_noise_levels(drone_df: pd.DataFrame, base_noise_df: pd.DataFrame) -> pd.DataFrame:
    merged_df = pd.merge(
        drone_df,
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


def calculate_combined_noise_data(result_path: str):
    matrix_df = read_drone_noise_data(result_path)
    drone_noise_df = generate_drone_noise_df(matrix_df)

    base_noise_df = read_base_noise_data()

    combined_noise_df = combine_noise_levels(drone_noise_df, base_noise_df)

    return combined_noise_df
