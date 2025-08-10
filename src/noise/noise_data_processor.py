import json

import pandas as pd

from common.path_configs import BASE_NOISE_PATH
from noise.noise_math_utils import add_two_decibel_levels


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

BASE_NOISE_DATA = read_base_noise_data()

def generate_drone_noise_df(drone_noise_data, iteration_number) -> pd.DataFrame:
    records = [
        {
            "row": cell.row,
            "col": cell.column,
            "average_noise": cell.total_noise / iteration_number,
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


def combine_base_and_drone_noise(drone_noise_data, iteration_number) -> pd.DataFrame:
    drone_noise_df = generate_drone_noise_df(drone_noise_data, iteration_number)

    return combine_noise_levels(drone_noise_df, BASE_NOISE_DATA)
