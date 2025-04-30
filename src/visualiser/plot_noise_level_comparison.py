import math

import matplotlib
import matplotlib.pyplot as plt

from visualiser.plot_utils import plot_multiple_heatmaps

matplotlib.use('Qt5Agg')

METRICS = ['noise_level', 'average_noise', 'noise_difference']
TITLES = ['Base City Noise', 'Drone Noise', 'City Noise Increase']


def plot_noise_level_comparison(dataframe, file_name='noise_level_comparison',
                                metrics=None, titles=None, vmin=None, vmax=None):
    if titles is None:
        titles = TITLES

    if metrics is None:
        metrics = METRICS

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    fig.filename = f'{file_name}_{vmin[0] or "min"}_{vmax[0] or "max"}'

    plot_multiple_heatmaps(
        dataframe,
        axes,
        index='row',
        columns='col',
        values=metrics,
        titles=titles,
        vmin=vmin,
        vmax=vmax,
        xlabel='Column',
        ylabel='Row')


def create_heatmap_figure(num_dfs, file_name, vmin, vmax):
    cols = math.ceil(math.sqrt(num_dfs))
    rows = math.ceil(num_dfs / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 4), constrained_layout=True)
    fig.filename = f'{file_name}_{vmin or "min"}_{vmax or "max"}'

    if not (rows == cols == 1):
        axes = axes.flatten()

    return fig, axes


def plot_single_noise_metric_from_different_dfs(dataframes, metric='average_noise', vmin=None, vmax=None,
                                                filename='single_noise_metric_comparison'):
    num_dfs = len(dataframes)

    fig, axes = create_heatmap_figure(num_dfs, filename, vmin, vmax)

    plot_multiple_heatmaps(
        dataframes,
        axes,
        index='row',
        columns='col',
        values=[metric] * num_dfs,
        titles=[''] * num_dfs,
        vmin=vmin,
        vmax=vmax,
        xlabel='Column',
        ylabel='Row')
