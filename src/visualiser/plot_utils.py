import os

import matplotlib
import seaborn as sns
from matplotlib import pyplot as plt

from common.path_configs import PATH_CONFIGS

matplotlib.use(PATH_CONFIGS.matplotlib_backend)

COLORMAP = "viridis"


def add_font_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 15,
        "axes.titlesize": 15,
        "axes.labelsize": 15,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 15,
        "legend.title_fontsize": 15,
        "figure.titlesize": 15,
    })

add_font_style()


def get_color_map(dataset_types):
    cmap = plt.get_cmap('tab10')
    return {ds: cmap(i) for i, ds in enumerate(dataset_types)}


def plot_standalone_heatmap(
        dataframe, index, columns, values,
        vmin=None, vmax=None, xlabel=None, ylabel=None,
        filename='', invert_yaxis=True, cbar_label=None   # ← add this
):
    fig = plt.figure(figsize=(10, 8))
    fig.filename = filename
    _prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis, cbar_label)


def plot_multiple_heatmaps(
        dataframes, axes, index, columns, values, titles,
        vmin=None, vmax=None, xlabel=None, ylabel=None, invert_yaxis=True, cbar_labels=None
):
    dataframes = _ensure_list_length(dataframes, len(values))
    vmin = _ensure_list_length(vmin, len(values))
    vmax = _ensure_list_length(vmax, len(values))
    cbar_labels = _ensure_list_length(cbar_labels, len(values))

    for i in range(len(values)):
        plt.sca(axes[i])
        _prepare_heatmap(
            dataframes[i], index, columns, values[i],
            vmin[i], vmax[i], xlabel, ylabel, invert_yaxis, cbar_label=cbar_labels[i]
        )
        axes[i].set_title(titles[i])


def _prepare_heatmap(dataframe, index, columns, values, vmin, vmax, xlabel, ylabel, invert_yaxis, cbar_label=None):
    heatmap_data = dataframe.pivot(index=index, columns=columns, values=values)

    cbar_kws = {"label": cbar_label} if cbar_label else {}
    sns.heatmap(heatmap_data, cmap=COLORMAP, annot=False, cbar=True, vmin=vmin, vmax=vmax, cbar_kws=cbar_kws)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if invert_yaxis:
        plt.gca().invert_yaxis()


def plot_figures():
    plt.show()


def save_figures(output_directory: str = "figures"):
    for i in plt.get_fignums():
        fig = plt.figure(i)

        filename = fig.filename if hasattr(fig, "filename") else f"figure_{i}"
        out_path = os.path.join(output_directory, f"{filename}.eps")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        fig.savefig(out_path, dpi=1000, format="eps", bbox_inches="tight")


def finalise_visualisation(output_directory: str = "figures"):
    save_figures(output_directory=output_directory)
    plot_figures()


def _ensure_list_length(input_value, reference_list_length):
    if not isinstance(input_value, list):
        return [input_value] * reference_list_length
    return input_value
