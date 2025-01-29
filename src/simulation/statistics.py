import matplotlib
import numpy as np
from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST, TOTAL_ORDER_NUMBER
)
from common.coordinate import calculate_distance
from matplotlib import pyplot as plt
from orders.order_generator import load_orders

matplotlib.use('Qt5Agg')


def plot_noise_difference_colormap(dataframe):
    min_level = int(np.floor(dataframe['noise_difference'].min()))
    max_level = int(np.ceil(dataframe['noise_difference'].max()))

    heatmap_data = dataframe.pivot(index='row', columns='col', values='noise_difference')

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_title('Noise Difference Colormap (dBs)', fontsize=16)

    img = ax.imshow(heatmap_data, cmap='coolwarm', aspect='auto', origin='lower',
                    vmin=min_level, vmax=max_level)

    fig.colorbar(img, ax=ax, label=f'Noise Difference ({min_level} to {max_level} dBs)')

    ax.set_xlabel('Column')
    ax.set_ylabel('Row')

    plt.tight_layout()


def plot_noise_change_barchart(dataframe, bin_gap=0.5):
    min_level = int(np.floor(dataframe['noise_difference'].min()))
    max_level = int(np.ceil(dataframe['noise_difference'].max()))

    bins = np.arange(min_level, max_level, bin_gap)

    noise_counts = dataframe['noise_difference'].value_counts(bins=bins, sort=False).sort_index()

    x_labels = [f"{interval.left:.1f} - {interval.right:.1f}" for interval in noise_counts.index]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(x_labels, noise_counts, color='skyblue', edgecolor='black')
    ax.bar_label(bars, fmt='{:,.0f}')
    ax.set_title('Number of Cells by Noise Difference Level (dBs)', fontsize=16)
    ax.set_xlabel('Noise Difference (dBs)', fontsize=12)
    ax.set_ylabel('Number of Cells', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()


def _compute_distance_stats(delivery_dataset):
    distances = [calculate_distance(order.start_location, order.end_location) for order in delivery_dataset]
    return {
        'min': min(distances),
        'max': max(distances),
        'mean': np.mean(distances),
        'median': np.median(distances)
    }


def calculate_delivery_distance_statistics():
    furthest_stats = _compute_distance_stats(load_orders(TOTAL_ORDER_NUMBER, ORDER_BASE_PATH_FURTHEST))
    random_stats = _compute_distance_stats(load_orders(TOTAL_ORDER_NUMBER, ORDER_BASE_PATH_RANDOM))
    closest_stats = _compute_distance_stats(load_orders(TOTAL_ORDER_NUMBER, ORDER_BASE_PATH_CLOSEST))

    labels = ['Min', 'Mean', 'Median', 'Max']
    furthest_vals = [furthest_stats['min'], furthest_stats['mean'], furthest_stats['median'], furthest_stats['max']]
    random_vals = [random_stats['min'], random_stats['mean'], random_stats['median'], random_stats['max']]
    closest_vals = [closest_stats['min'], closest_stats['mean'], closest_stats['median'], closest_stats['max']]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(x - width, furthest_vals, width, label='Furthest')
    ax.bar(x, random_vals, width, label='Random')
    ax.bar(x + width, closest_vals, width, label='Closest')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Distance, meters')
    ax.set_title('Delivery Distance Statistics')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend()

    plt.tight_layout()
    plt.show()


def plot_graphs():
    plt.show()
