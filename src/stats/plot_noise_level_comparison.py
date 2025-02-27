from stats.plot_utils import plot_multiple_heatmaps
import matplotlib.pyplot as plt

values = ['noise_level', 'average_noise', 'noise_difference']
titles = ['Base City Noise', 'Drone Noise', 'City Noise Increase']


def plot_noise_level_comparison(dataframe, vmin=None, vmax=None):
    plt.rcParams.update({
        "font.size": 14,
        "axes.titlesize": 14,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
    })

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    fig.filename = f'noise_level_comparison_{vmin}_{vmax}'

    plot_multiple_heatmaps(dataframe,
                           axes,
                           index='row',
                           columns='col',
                           values=values,
                           titles=titles,
                           vmin=vmin,
                           vmax=vmax,
                           xlabel='Column',
                           ylabel='Row')
