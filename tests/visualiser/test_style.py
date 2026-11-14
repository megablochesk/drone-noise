"""One set of styles for every figure. The submitted paper fixed them: reviewers have seen these colours."""
from matplotlib import pyplot as plt

from experiments.revision import plot_style
from visualiser import style


def test_stockings_keep_the_colours_and_marks_of_the_submitted_paper():
    """Worst-case blue solid circles, best-case orange dashed squares, random green dotted triangles."""
    tab10 = plt.get_cmap("tab10")

    assert style.STOCKING_COLOURS == {"furthest": tab10(0), "closest": tab10(1), "random": tab10(2)}
    assert style.STOCKING_LINE_STYLES == {"furthest": "-", "closest": "--", "random": ":"}
    assert style.STOCKING_MARKERS == {"furthest": "o", "closest": "s", "random": "^"}
    assert style.STOCKING_LEGEND["furthest"] == "worst-case stocking"


def test_routings_are_named_and_coloured_as_in_the_submitted_paper():
    tab10 = plt.get_cmap("tab10")

    assert style.describe_navigation("STRAIGHT") == "Straight"
    assert style.describe_navigation("NOISE_A025") == "Mixed (α=0.25)"
    assert style.describe_navigation("NOISE_A100") == "Mixed (α=1.00)"
    assert [style.NAVIGATION_COLOURS[navigation] for navigation in style.NAVIGATION_ORDER] == [tab10(i) for i in range(5)]


def test_revision_figures_use_the_same_stocking_colours():
    assert plot_style.STOCKING_COLOURS == style.STOCKING_COLOURS
