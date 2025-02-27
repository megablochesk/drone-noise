import matplotlib
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt

matplotlib.use('Qt5Agg')

COLORMAP = "viridis"


def get_color_map(dataset_types):
    cmap = plt.get_cmap('tab10')
    return {ds: cmap(i) for i, ds in enumerate(dataset_types)}


def annotate_barchart_data_points(ax, bar, value, decimal_places=2):
    ax.annotate(f'{value:.{decimal_places}f}' if isinstance(value, (float, int)) else f'{value}',
                xy=(bar[0].get_x() + bar[0].get_width() / 2, value),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=10)


def annotate_linegraph_data_points(ax, x, y):
    for xi, yi in zip(x, y):
        annotation = f'{yi:.2f}' if isinstance(yi, float) else f'{yi}'
        ax.annotate(annotation,
                    xy=(xi, yi),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=10)


def extract_x_y_values(results_df, dataset, value_column):
    df_ds = results_df[results_df['dataset_name'] == dataset].sort_values(by='num_drones')
    return df_ds['num_drones'].values, df_ds[value_column].values


def plot_multiple_datasets_linegraph(ax, results_df, dataset_types, color_map, value_column):
    for dataset in dataset_types:
        x, y = extract_x_y_values(results_df, dataset, value_column)
        ax.plot(x, y, marker='o', color=color_map[dataset], label=dataset)
        annotate_linegraph_data_points(ax, x, y)


def plot_heatmap(dataframe, index, columns, values, vmin=None, vmax=None, xlabel=None, ylabel=None,
                 filename='', invert_yaxis=True):
    heatmap_data = dataframe.pivot(index=index, columns=columns, values=values)

    fig = plt.figure(figsize=(10, 8))
    sns.heatmap(heatmap_data, cmap=COLORMAP, annot=False, cbar=True, vmin=vmin, vmax=vmax)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if invert_yaxis:
        plt.gca().invert_yaxis()

    fig.filename = filename


def plot_multiple_heatmaps(dataframe, axes, index, columns, values, titles,
                           vmin=None, vmax=None, xlabel=None, ylabel=None, invert_yaxis=True):
    for ax, value, title in zip(axes, values, titles):
        heatmap_data = dataframe.pivot(index=index, columns=columns, values=value)
        sns.heatmap(heatmap_data, cmap=COLORMAP, annot=False, cbar=True, vmin=vmin, vmax=vmax, ax=ax)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if invert_yaxis:
            ax.invert_yaxis()


def plot_figures():
    plt.show()


def save_figures():
    for i in plt.get_fignums():
        fig = plt.figure(i)

        filename = fig.filename if hasattr(fig, "filename") else f'figure_{i}'

        fig.savefig(f"figures/{filename}.eps", dpi=300, format="eps")
