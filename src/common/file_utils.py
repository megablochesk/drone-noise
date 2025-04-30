import csv
import os

import pandas as pd
from common.configuration import RESULT_BASE_PATH


def define_results_path(order_number, drone_number):
    path = RESULT_BASE_PATH + '/' + f"stat_o{order_number}_d{drone_number}"

    if not os.path.exists(path):
        os.makedirs(path)

    return path


def get_experiment_results_full_file_path(file_name):
    return f'recourses/experiment_results/{file_name}.pkl'


def save_drone_noise_data(noise_tracker, iteration_count, path):
    matrix_path = f"{path}/noise.csv"

    matrix_fields = ['row', 'col', 'avg_noise', 'max_noise']

    matrix_data = [
        [
            cell.row,
            cell.column,
            cell.total_noise / iteration_count,
            cell.max_noise
        ]
        for cell in noise_tracker.noise_cells
    ]

    write_csv(matrix_path, matrix_fields, matrix_data, 'noise data')


def write_csv(file_path, headers, data, data_type):
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        print(f"Done writing {data_type}!")
        f.flush()


def save_dataframe_to_pickle(dataframe, path):
    dataframe.to_pickle(path)
    print(f"Results saved to {path}")


def load_dataframe_from_pickle(path):
    return pd.read_pickle(path)
