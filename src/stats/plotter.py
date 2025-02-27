import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.configuration import NUMBER_OF_HOURS
from stats.cell_population_calculator import (
    calculate_population_impacted_by_noise, CELL_POPULATION, get_cells_impacted_by_noise
)
from stats.plot_utils import (
    plot_heatmap, plot_multiple_datasets_linegraph, get_color_map, annotate_barchart_data_points
)

matplotlib.use('Qt5Agg')


DATASET_TYPE_BAR_ORDER = ['closest', 'furthest', 'random']


def prepare_barchart_data(results_df):
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df['dataset_name'].unique()]
    num_drones_list = sorted(results_df['num_drones'].unique())
    color_map = get_color_map(dataset_types)

    return dataset_types, num_drones_list, color_map


def plot_barchart_stats(results_df, value_column, xlabel, ylabel, title=None, decimal_places=2, filename=None):
    dataset_types, num_drones_list, color_map = prepare_barchart_data(results_df)

    x = np.arange(len(num_drones_list))

    plot_multiple_datasets_barchart(x, num_drones_list, dataset_types, results_df, value_column, xlabel, ylabel,
                                    color_map, title, decimal_places, filename)


def extract_sorted_values(results_df, dataset_types, num_drones, value_column):
    ds_values = []

    for ds in DATASET_TYPE_BAR_ORDER:
        if ds in dataset_types:
            row = results_df[(results_df['dataset_name'] == ds) & (results_df['num_drones'] == num_drones)]
            value = row.iloc[0][value_column] if not row.empty else 0
            ds_values.append((ds, value))

    return ds_values


def plot_multiple_datasets_barchart(x, num_drones_list, dataset_types, results_df, value_column, xlabel, ylabel, color_map,
                                    title=None, decimal_places=2, filename=None):
    width = 0.2
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.filename = filename
    added_labels = set()

    for i, num_drones in enumerate(num_drones_list):
        ds_values = extract_sorted_values(results_df, dataset_types, num_drones, value_column)
        num_datasets = len(ds_values)

        for j, (ds, value) in enumerate(ds_values):
            bar_position = x[i] - width * (num_datasets - 1) / 2 + j * width
            label = ds if ds not in added_labels else ""
            if ds not in added_labels:
                added_labels.add(ds)

            bar = ax.bar(bar_position, value, width, color=color_map[ds], label=label)
            annotate_barchart_data_points(ax, bar, value, decimal_places)

    ax.set_xticks(x)
    ax.set_xticklabels(num_drones_list)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


def prepare_linegraph_data(results_df):
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df['dataset_name'].unique()]
    color_map = get_color_map(dataset_types)
    return dataset_types, color_map


def plot_linegraph(results_df, value_column, xlabel, ylabel, title=''):
    dataset_types, color_map = prepare_linegraph_data(results_df)
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_multiple_datasets_linegraph(ax, results_df, dataset_types, color_map, value_column)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title='Dataset Type')
    fig.tight_layout()
    return fig


def plot_avg_noise_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column='avg_noise_diff',
        xlabel='Number of Drones',
        ylabel='Average Noise Difference, dBs',
        title='Average Noise Difference by Drone Number and Dataset',
        filename='del_noise'
    )


def plot_avg_noise_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column='avg_noise_diff',
        xlabel='Number of Drones',
        ylabel='Average Noise Difference, dBs',
        title='Average Noise Difference by Drone Number and Dataset'
    )


def plot_delivered_orders_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column='delivered_orders_number',
        xlabel='Number of Drones',
        ylabel=f'Number of Delivered Orders over Period of {NUMBER_OF_HOURS} Hours',
        # title='Delivered Orders by Drone Number and Dataset',
        filename='del_orders'
    )


def plot_delivered_orders_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column='delivered_orders_number',
        xlabel='Number of Drones',
        ylabel=f'Number of Delivered Orders over Period of {NUMBER_OF_HOURS} Hours',
        # title='Delivered Orders by Drone Number and Dataset'
    )


def calculate_noise_increase_cells(main_df, threshold=55):
    rows = []
    for _, row in main_df.iterrows():
        noise_impact = row['noise_impact_df']

        count = ((noise_impact['combined_noise'] > threshold) & (noise_impact['noise_level'] < threshold)).sum()
        rows.append({
            'dataset_name': row['dataset_name'],
            'num_drones': row['num_drones'],
            'cells_exceeding_threshold': count
        })
    return pd.DataFrame(rows)


def analyze_and_plot_noise_increase(main_df, threshold=55):
    summary_df = calculate_noise_increase_cells(main_df, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column='cells_exceeding_threshold',
        xlabel='Number of Drones',
        ylabel='Number of Cells',
        # title=f'Cells with Combined Noise > {threshold} dB',
        decimal_places=0,
        filename='del_cel_imp'
    )


def analyze_and_plot_population_impact(main_df, threshold=55):
    summary_df = calculate_population_impacted_by_noise(main_df, threshold)
    return plot_barchart_stats(
        summary_df,
        value_column='impacted_population',
        xlabel='Number of Drones',
        ylabel=f'Population Impacted by Noise over {threshold} dB',
        # title=f'Population Affected by Combined Noise > {threshold} dB',
        decimal_places=0,
        filename='del_pop_imp'
    )


def plot_cell_population():
    population_df = CELL_POPULATION

    metric = 'population'

    plot_heatmap(population_df,
                 index='row',
                 columns='col',
                 values=metric,
                 vmin=None,
                 vmax=None,
                 xlabel='Column',
                 ylabel='Row',
                 filename=metric)


def plot_cells_impacted_by_noise(main_df, threshold=55):
    df = get_cells_impacted_by_noise(main_df, threshold)

    metric = 'population'

    for (dataset_name, num_drones), group_df in df.groupby(['dataset_name', 'num_drones']):
        plot_heatmap(group_df,
                     index='row',
                     columns='col',
                     values=metric,
                     vmin=None,
                     vmax=None,
                     xlabel='Column',
                     ylabel='Row',
                     filename=f'{metric}_{dataset_name}_{num_drones}')
