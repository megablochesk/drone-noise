import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from common.coordinate import calculate_distance
from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from common.path_configs import PATH_CONFIGS
from common.runtime_configs import get_simulation_config
from orders.order_generator import load_orders

matplotlib.use(PATH_CONFIGS.matplotlib_backend)

DATASET_TYPE_TO_LEGEND = {
    "furthest": "worst",
    "closest": "best",
    "random": "random"
}


def plot_delivery_distance_statistics():
    stats = _compute_all_distance_stats()
    labels = ['Min', 'Mean', 'Median', 'Max']
    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.filename = f'delivery_distance'
    _plot_delivery_distance_barchart(ax, x, stats, width)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Distance, meters')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()


def plot_noise_difference_barchart(dataframe, bin_gap=0.5, file_name='noise_change_barchart'):
    x_labels, noise_counts = _prepare_noise_data(dataframe, bin_gap=bin_gap)
    _plot_barchart(x_labels, noise_counts,
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

    orders_to_process = get_simulation_config().orders_to_process

    return {label: _compute_distance_stats(load_orders(orders_to_process, path)) for label, path in
            order_paths.items()}


def _plot_delivery_distance_barchart(ax, x, stats, width):
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


def _prepare_noise_data(dataframe, noise_metric='noise_difference', bin_gap=0.5):
    min_level = int(np.floor(dataframe[noise_metric].min()))
    max_level = int(np.ceil(dataframe[noise_metric].max()))
    bins = np.arange(min_level, max_level, bin_gap)

    noise_counts = dataframe[noise_metric].value_counts(bins=bins, sort=False).sort_index()
    x_labels = [f"{interval.left:.1f} - {interval.right:.1f}" for interval in noise_counts.index]

    return x_labels, noise_counts


def _plot_barchart(x_labels, counts, title, xlabel, ylabel, filename='barchart_default', figsize=(10, 6)):
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


def plot_dataset_stat_difference(
        df,
        value_col,
        dataset_col="dataset",
        group_col="num_drones",
        nav_col="navigation_type",
        nav_map=None,
        ylabel=None,
        title=None,
        filename : str = None
):
    if nav_map is None:
        nav_map = {"STRAIGHT": "Normal", "LIGHT_NOISE": "Routed"}

    datasets = sorted(df[dataset_col].unique())
    ratios = []

    for ds in datasets:
        sub = df[df[dataset_col] == ds]

        merged = sub.pivot(index=group_col, columns=nav_col, values=value_col)
        merged = merged.rename(columns=nav_map)
        merged = merged.dropna()

        percentage_gain = (merged["Normal"] - merged["Routed"]) / merged["Routed"] * 100
        ratios.append((percentage_gain.mean(), percentage_gain.std()))

    x = np.arange(len(datasets))
    y = [m for m, s in ratios]
    err = [s for m, s in ratios]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.filename = filename
    ax.bar(x, y, yerr=err, capsize=5, color="tab:blue", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([DATASET_TYPE_TO_LEGEND.get(ds, ds) for ds in datasets])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    for i, val in enumerate(y):
        ax.text(i, val, f"{val:.1f}%", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    return fig, ax
