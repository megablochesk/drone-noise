import matplotlib
import seaborn as sns
from matplotlib import pyplot as plt

from common.path_configs import PATH_CONFIGS

matplotlib.use(PATH_CONFIGS.matplotlib_backend)

COLORMAP = "viridis"


def get_color_map(dataset_types):
    cmap = plt.get_cmap('tab10')
    return {ds: cmap(i) for i, ds in enumerate(dataset_types)}


def plot_standalone_heatmap(
        dataframe,
        index,
        columns,
        values,
        vmin=None,
        vmax=None,
        xlabel=None,
        ylabel=None,
        filename='',
        invert_yaxis=True
):
    fig = plt.figure(figsize=(10, 8))
    fig.filename = filename

    _prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis)


def plot_multiple_heatmaps(
        dataframes,
        axes,
        index,
        columns,
        values,
        titles,
        vmin=None,
        vmax=None,
        xlabel=None,
        ylabel=None,
        invert_yaxis=True
):
    dataframes = _ensure_list_length(dataframes, len(values))
    vmin = _ensure_list_length(vmin, len(values))
    vmax = _ensure_list_length(vmax, len(values))

    for i in range(len(values)):
        plt.sca(axes[i])
        _prepare_heatmap(
            dataframes[i], index, columns, values[i],
            vmin[i], vmax[i], xlabel, ylabel, invert_yaxis
        )
        axes[i].set_title(titles[i])


def _prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis):
    heatmap_data = dataframe.pivot(index=index, columns=columns, values=values)
    sns.heatmap(heatmap_data, cmap=COLORMAP, annot=False, cbar=True, vmin=vmin, vmax=vmax)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if invert_yaxis:
        plt.gca().invert_yaxis()


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


def finalise_visualisation():
    add_font_style()
    save_figures()
    plot_figures()


def _ensure_list_length(input_value, reference_list_length):
    if not isinstance(input_value, list):
        return [input_value] * reference_list_length
    return input_value
