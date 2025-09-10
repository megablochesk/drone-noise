import json
import os
import pickle

import networkx as nx
import osmnx as ox
import pandas as pd


def save_dataframe_to_pickle(dataframe, path):
    dataframe.to_pickle(path)
    print(f"Results saved to {path}")


def load_dataframe_from_pickle(path):
    return pd.read_pickle(path)

def load_data_from_pickle(file_path):
    with open(file_path, 'rb') as file:
        return pickle.load(file)


def save_data_as_pickle_highest_protocol(data, file_path):
    save_data_as_pickle(data, file_path, pickle.HIGHEST_PROTOCOL)


def save_data_as_pickle(data, file_path, protocol=None):
    with open(file_path, 'wb') as file:
        pickle.dump(data, file=file, protocol=protocol)


def save_graph_as_graphml(graph_to_save, file_path):
    nx.write_graphml(graph_to_save, file_path)


def save_graph(graph, file_path):
    graphml_file = ensure_suffix(file_path, '.graphml')
    pickle_file = ensure_suffix(file_path, '.pkl')

    try:
        save_graph_as_graphml(graph, graphml_file)
        save_data_as_pickle_highest_protocol(graph, pickle_file)

        print(f"Graph saved to '{file_path}' successfully.")
    except Exception as e:
        print(f"Error saving graph to '{file_path}': {e}")


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


def _load_graph_from_pickle_or_graphml(file_path):
    pickle_path = ensure_suffix(file_path, '.pkl')

    if path_exists(pickle_path):
        return load_pickle_graph(pickle_path)

    graphml_path = ensure_suffix(file_path, '.graphml')
    graph = load_graphml_graph(graphml_path)

    if graph is not None:
        save_data_as_pickle_highest_protocol(graph, pickle_path)

    return graph


def load_graph(graph_file_path):
    return _load_graph_from_pickle_or_graphml(graph_file_path)


def path_exists(path, suffixes=None):
    if os.path.exists(path):
        return True

    return any(os.path.exists(path + suffix) for suffix in suffixes)


def ensure_suffix(line, suffix):
    if not line.endswith(suffix):
        return line + suffix
    return line


def load_df_from_csv(path):
    return pd.read_csv(path)


def save_df_to_csv(data, path):
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    
    data.to_csv(path, index=False)


def load_json(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
