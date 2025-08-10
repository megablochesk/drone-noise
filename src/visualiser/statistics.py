import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from common.coordinate import calculate_distance
from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from common.path_configs import PATH_CONFIGS
from common.simulation_configs import simulation_configs
from orders.order_generator import load_orders

matplotlib.use(PATH_CONFIGS.matplotlib_backend)

TOTAL_ORDER_NUMBER = simulation_configs.sim.orders


def prepare_noise_data(dataframe, noise_metric='noise_difference', bin_gap=0.5):
    min_level = int(np.floor(dataframe[noise_metric].min()))
    max_level = int(np.ceil(dataframe[noise_metric].max()))
    bins = np.arange(min_level, max_level, bin_gap)

    noise_counts = dataframe[noise_metric].value_counts(bins=bins, sort=False).sort_index()
    x_labels = [f"{interval.left:.1f} - {interval.right:.1f}" for interval in noise_counts.index]

    return x_labels, noise_counts


def plot_barchart(x_labels, counts, title, xlabel, ylabel, filename='barchart_default', figsize=(10, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.filename = filename

    bars = ax.bar(x_labels, counts, color='skyblue', edgecolor='black')

    ax.bar_label(bars, fmt='{:,.0f}')
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()


def plot_noise_difference_barchart(dataframe, bin_gap=0.5, file_name='noise_change_barchart'):
    x_labels, noise_counts = prepare_noise_data(dataframe, bin_gap=bin_gap)
    plot_barchart(x_labels, noise_counts,
                  title='Number of Cells by Noise Level Difference',
                  xlabel='Noise Difference, dBs',
                  ylabel='Number of Cells',
                  filename=file_name)


def _compute_distance_stats(delivery_dataset):
    distances_between_warehouse_and_client = [calculate_distance(order.start_location, order.end_location) for order in delivery_dataset]
    return {
        'min': min(distances_between_warehouse_and_client) * 2,
        'max': max(distances_between_warehouse_and_client) * 2,
        'mean': np.mean(distances_between_warehouse_and_client) * 2,
        'median': np.median(distances_between_warehouse_and_client) * 2
    }


def _compute_all_distance_stats():
    order_paths = {
        'worst': ORDER_BASE_PATH_FURTHEST,
        'random': ORDER_BASE_PATH_RANDOM,
        'best': ORDER_BASE_PATH_CLOSEST
    }

    return {label: _compute_distance_stats(load_orders(TOTAL_ORDER_NUMBER, path)) for label, path in
            order_paths.items()}


def plot_delivery_distance_barchart(ax, x, stats, width):
    bars = {}
    for i, (label, stat) in enumerate(stats.items()):
        vals = [stat['min'], stat['mean'], stat['median'], stat['max']]
        bars[label] = ax.bar(x + (i - 1) * width, vals, width, label=label)

    def add_value_labels(bar_set):
        for bar in bar_set:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.0f}', ha='center', va='bottom', fontsize=12)

    for bar_set in bars.values():
        add_value_labels(bar_set)

    ax.legend()


def plot_delivery_distance_statistics():
    stats = _compute_all_distance_stats()
    labels = ['Min', 'Mean', 'Median', 'Max']
    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.filename = f'delivery_distance'
    plot_delivery_distance_barchart(ax, x, stats, width)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Distance, meters')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
