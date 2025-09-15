import matplotlib
import matplotlib.pyplot as plt

from common.path_configs import PATH_CONFIGS
from visualiser.plot_utils import plot_multiple_heatmaps

matplotlib.use(PATH_CONFIGS.matplotlib_backend)


def _make_filename(base, code, vmin, vmax):
    return f"{base}_{code}_{vmin if vmin is not None else 'min'}_{vmax if vmax is not None else 'max'}"


def plot_census_data_heatmap_by_code(df, code: int, data_category: str, vmin: float, vmax: float):
    fig, ax = plt.subplots(1, 1, figsize=(6, 6), constrained_layout=True)
    fig.filename = _make_filename(data_category, code, vmin, vmax)

    plot_multiple_heatmaps(
        df,
        [ax],
        index="row",
        columns="col",
        values=[code],
        titles=[df.attrs[f"{data_category}_code_to_name"][code]],
        vmin=[vmin],
        vmax=[vmax],
        xlabel="Column",
        ylabel="Row",
    )


def plot_heatmaps_for_census_data(df, data_category, vmin, vmax):
    codes = sorted(df.attrs[f"{data_category}_code_to_name"])

    for code in codes:
        plot_census_data_heatmap_by_code(df, code, data_category=data_category, vmin=vmin, vmax=vmax)
