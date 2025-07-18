import csv
import os
import pickle

import osmnx as ox
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


def save_graph_as_pickle(graph_to_save, file_path):
    with open(file_path, 'wb') as file:
        pickle.dump(graph_to_save, file, protocol=pickle.HIGHEST_PROTOCOL)


def save_graph_as_graphml(graph_to_save, file_path):
    ox.save_graphml(graph_to_save, file_path)


def save_graph(graph, file_path):
    graphml_file = f'{file_path}.graphml'
    pickle_file = f'{file_path}.pkl'

    try:
        save_graph_as_graphml(graph, graphml_file)
        save_graph_as_pickle(graph, pickle_file)
    except Exception as e:
        print(f"Error saving graph to '{file_path}': {e}")

    print(f"Graph saved to '{file_path}' successfully.")


def load_graphml_graph(file_path):
    try:
        graph_from_graphml = ox.load_graphml(file_path)
        print(f"Graph loaded from '{file_path}' successfully.")
        return graph_from_graphml
    except Exception as e:
        print(f"Error loading graph from '{file_path}': {e}")
        return None


def load_pickle_graph(file_path):
    try:
        with open(file_path, 'rb') as f:
            graph_from_pickle = pickle.load(f)
        print(f"Graph loaded from '{file_path}' successfully.")
        return graph_from_pickle
    except Exception as e:
        print(f"Error loading graph from '{file_path}': {e}")
        return None


def load_graph_from_pickle_or_graphml(file_path):
    pickle_path = f'{file_path}.pkl'

    if os.path.exists(pickle_path):
        return load_pickle_graph(pickle_path)

    graphml_path = f'{file_path}.graphml'
    graph = load_graphml_graph(graphml_path)

    if graph is not None:
        save_graph_as_pickle(graph, pickle_path)

    return graph


def load_graph(graph_file_path):
    return load_graph_from_pickle_or_graphml(graph_file_path)
