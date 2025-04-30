import matplotlib
import seaborn as sns
from matplotlib import pyplot as plt

matplotlib.use('Qt5Agg')

COLORMAP = "viridis"


def get_color_map(dataset_types):
    cmap = plt.get_cmap('tab10')
    return {ds: cmap(i) for i, ds in enumerate(dataset_types)}


def annotate_barchart_data_points(ax, bar, value, decimal_places=2, offset=2):
    ax.annotate(f'{value:.{decimal_places}f}' if isinstance(value, (float, int)) else f'{value}',
                xy=(bar[0].get_x() + bar[0].get_width() / 2, value),
                xytext=(0, offset), textcoords="offset points",
                ha='center', va='bottom', fontsize=14)


def annotate_linegraph_data_points(ax, x, y):
    for xi, yi in zip(x, y):
        annotation = f'{yi:.2f}' if isinstance(yi, float) else f'{yi}'
        ax.annotate(annotation,
                    xy=(xi, yi),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=12)


def extract_x_y_values(results_df, dataset, value_column):
    df_ds = results_df[results_df['dataset_name'] == dataset].sort_values(by='num_drones')
    return df_ds['num_drones'].values, df_ds[value_column].values


def plot_multiple_datasets_linegraph(ax, results_df, dataset_types, color_map, value_column):
    for dataset in dataset_types:
        x, y = extract_x_y_values(results_df, dataset, value_column)
        ax.plot(x, y, marker='o', color=color_map[dataset], label=dataset)
        annotate_linegraph_data_points(ax, x, y)


def prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis):
    heatmap_data = dataframe.pivot(index=index, columns=columns, values=values)
    sns.heatmap(heatmap_data, cmap=COLORMAP, annot=False, cbar=True, vmin=vmin, vmax=vmax)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if invert_yaxis:
        plt.gca().invert_yaxis()


def plot_standalone_heatmap(dataframe, index, columns, values, vmin=None, vmax=None, xlabel=None, ylabel=None,
                            filename='', invert_yaxis=True):
    fig = plt.figure(figsize=(10, 8))
    prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis)
    fig.filename = filename


def plot_multiple_heatmaps(dataframes, axes, index, columns, values, titles,
                           vmin=None, vmax=None, xlabel=None, ylabel=None, invert_yaxis=True):
    dataframes = ensure_list_length(dataframes, len(values))
    vmin = ensure_list_length(vmin, len(values))
    vmax = ensure_list_length(vmax, len(values))

    for i in range(len(values)):
        plt.sca(axes[i])
        prepare_heatmap(
            dataframes[i], index, columns, values[i],
            vmin[i], vmax[i], xlabel, ylabel, invert_yaxis
        )
        axes[i].set_title(titles[i])


def plot_figures():
    plt.show()


def save_figures():
    for i in plt.get_fignums():
        fig = plt.figure(i)

        filename = fig.filename if hasattr(fig, "filename") else f'figure_{i}'

        fig.savefig(f"figures/{filename}.eps", dpi=300, format="eps", bbox_inches='tight')


def add_font_style():
    plt.rcParams.update({
        "font.size": 15,
        "axes.titlesize": 15,
        "axes.labelsize": 15,
        "xtick.labelsize": 15,
        "ytick.labelsize": 15,
    })

def ensure_list_length(input_value, reference_list_length):
    if not isinstance(input_value, list):
        return [input_value] * reference_list_length
    return input_value
