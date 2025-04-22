from stats.plot_utils import plot_multiple_heatmaps_from_same_df, plot_multiple_heatmaps_from_different_dfs
import matplotlib.pyplot as plt

METRICS = ['noise_level', 'average_noise', 'noise_difference']
TITLES = ['Base City Noise', 'Drone Noise', 'City Noise Increase']


def plot_noise_level_comparison(dataframe, file_name='noise_level_comparison', metrics=None, titles=None, vmin=None, vmax=None):

    if titles is None:
        titles = TITLES

    if metrics is None:
        metrics = METRICS

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    fig.filename = f'{file_name}_{vmin}_{vmax}'

    plot_multiple_heatmaps_from_same_df(dataframe,
                                        axes,
                                        index='row',
                                        columns='col',
                                        values=metrics,
                                        titles=titles,
                                        vmin=vmin,
                                        vmax=vmax,
                                        xlabel='Column',
                                        ylabel='Row')


def plot_noise_level_comparison_from_different_dfs(dataframes, file_name='noise_level_comparison',
                                            metrics=None, titles=None, vmin=None, vmax=None):

    if titles is None:
        titles = TITLES

    if metrics is None:
        metrics = METRICS

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    fig.filename = f'{file_name}_{vmin}_{vmax}'

    plot_multiple_heatmaps_from_different_dfs(dataframes,
                                        axes,
                                        index='row',
                                        columns='col',
                                        values=metrics,
                                        titles=titles,
                                        vmin=vmin,
                                        vmax=vmax,
                                        xlabel='Column',
                                        ylabel='Row')
