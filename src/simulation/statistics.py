import matplotlib
from matplotlib import pyplot as plt
import numpy as np

matplotlib.use('Qt5Agg')

MIN_NOISE_LEVEL = 0
MAX_NOISE_LEVEL = 3


def plot_noise_difference_colormap(dataframe):
    heatmap_data = dataframe.pivot(index='row', columns='col', values='noise_difference')

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_title('Noise Difference Colormap (dBs)', fontsize=16)

    img = ax.imshow(heatmap_data, cmap='coolwarm', aspect='auto', origin='lower',
                    vmin=MIN_NOISE_LEVEL, vmax=MAX_NOISE_LEVEL)

    cbar = fig.colorbar(img, ax=ax, label=f'Noise Difference ({MIN_NOISE_LEVEL} to {MAX_NOISE_LEVEL} dBs)')

    ax.set_xlabel('Column')
    ax.set_ylabel('Row')

    plt.tight_layout()


def plot_noise_change_barchart(dataframe, bin_gap=0.5):
    min_level = int(np.floor(dataframe['noise_difference'].min()))
    max_level = int(np.ceil(dataframe['noise_difference'].max()))
    bins = np.arange(min_level, max_level + 1, bin_gap)

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


def plot_graphs():
    plt.show()
