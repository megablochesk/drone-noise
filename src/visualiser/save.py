"""The one way a figure reaches a file."""
from pathlib import Path

from matplotlib import pyplot as plt

DEFAULT_FORMATS = ("eps",)
DEFAULT_DPI = 300


def save_figure(figure, directory: Path, name: str, formats: tuple[str, ...] = DEFAULT_FORMATS, dpi: int = DEFAULT_DPI) -> list[Path]:
    """Writes the figure once per format, closes it, and returns the files written."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"{name}.{file_format}" for file_format in formats]
    for path, file_format in zip(paths, formats):
        figure.savefig(path, format=file_format, dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return paths
