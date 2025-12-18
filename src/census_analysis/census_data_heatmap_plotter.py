from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import matplotlib

from common.path_configs import PATH_CONFIGS

matplotlib.use(PATH_CONFIGS.matplotlib_backend)

import matplotlib.pyplot as plt

from visualiser.plot_utils import plot_multiple_heatmaps


class CensusHeatmapPlotter:
    def __init__(
        self,
        dataframe,
        *,
        data_category: str,
        vmin: Optional[float],
        vmax: Optional[float],
        output_dir: Optional[str] = None,
        figsize: Tuple[float, float] = (6, 6),
        index: str = "row",
        columns: str = "col",
        xlabel: str = "Column",
        ylabel: str = "Row",
    ) -> None:
        self.df = dataframe
        self.data_category = data_category
        self.vmin = vmin
        self.vmax = vmax
        self.output_dir = Path(output_dir) if output_dir else None
        self.figsize = figsize
        self.index = index
        self.columns = columns
        self.xlabel = xlabel
        self.ylabel = ylabel

        self._code_to_name: Dict[int, str] = self.df.attrs.get(
            f"{self.data_category}_code_to_name", {}
        )

    def plot_code(self, data_code: int) -> Tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots(1, 1, figsize=self.figsize, constrained_layout=True)
        fig.filename = self._make_filename(data_code)

        plot_multiple_heatmaps(
            self.df,
            [ax],
            index=self.index,
            columns=self.columns,
            values=[data_code],
            titles=[self._title_for_code(data_code)],
            vmin=[self.vmin],
            vmax=[self.vmax],
            xlabel=self.xlabel,
            ylabel=self.ylabel,
        )

        self._apply_y_tick_style(ax)
        return fig, ax

    def plot_all(self, *, codes: Optional[Iterable[int]] = None) -> None:
        if codes is None:
            codes = sorted(self._code_to_name)
        for code in codes:
            self.plot_code(int(code))

    def _title_for_code(self, data_code: int) -> str:
        return self._code_to_name.get(data_code, str(data_code))

    def _make_filename(self, data_code: int) -> str:
        vmin_s = "min" if self.vmin is None else str(self.vmin)
        vmax_s = "max" if self.vmax is None else str(self.vmax)
        name = f"{self.data_category}_{data_code}_{vmin_s}_{vmax_s}"

        if self.output_dir is None:
            return name
        return str(self.output_dir / name)

    @staticmethod
    def _apply_y_tick_style(ax: plt.Axes) -> None:
        ax.tick_params(axis="y", labelrotation=0)
        for lbl in ax.get_yticklabels():
            lbl.set_va("center")
            lbl.set_ha("right")


def plot_heatmaps_for_census_data(
    df,
    *,
    data_category: str,
    vmin: Optional[float],
    vmax: Optional[float],
    folder: Optional[str] = None,
) -> None:
    CensusHeatmapPlotter(
        df,
        data_category=data_category,
        vmin=vmin,
        vmax=vmax,
        output_dir=folder,
    ).plot_all()
