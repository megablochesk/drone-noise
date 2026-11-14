"""The runs behind the paper's figures, on the fine-grid design: six fleets, three stockings, five routings."""
from common.enum import NavigationType
from experiments.revision.fine_grid_design import (
    FINE_BASELINE_NOISE_MAP,
    NOISE_AWARE_NAVIGATIONS,
    PAPER_FLEETS,
    build_fine_grid_specifications,
    build_noise_aware_specifications,
    build_paper_figure_specifications,
)


def test_paper_figure_runs_cover_the_fleets_of_the_paper_with_every_routing():
    """Straight: 6 fleets x 3 stockings x 2 terminal modes = 36. Noise-aware (terminal phases only, as in the
    paper): 6 x 3 x 4 alphas = 72."""
    specifications = build_paper_figure_specifications(seeds=[1])
    straight = [specification for specification in specifications if specification.navigation is NavigationType.STRAIGHT]
    noise_aware = [specification for specification in specifications if specification.navigation is not NavigationType.STRAIGHT]

    assert PAPER_FLEETS == (1250, 1000, 750, 500, 250, 100)
    assert (len(straight), len(noise_aware)) == (36, 72)
    assert len(set(specifications)) == 108
    assert {specification.number_of_drones for specification in specifications} == set(PAPER_FLEETS)
    assert all(specification.terminal_phases for specification in noise_aware)
    assert {specification.navigation for specification in noise_aware} == set(NOISE_AWARE_NAVIGATIONS)
    assert all(
        (specification.noise_cell_m, specification.time_step_s, specification.baseline_noise_map)
        == (100, 10, FINE_BASELINE_NOISE_MAP) for specification in specifications
    )


def test_paper_figure_runs_reuse_the_runs_already_stored():
    """Every pilot run and every noise-aware run of the same seed is one of the paper-figure runs."""
    specifications = set(build_paper_figure_specifications(seeds=[1]))

    assert set(build_fine_grid_specifications(seeds=[1])) <= specifications
    assert set(build_noise_aware_specifications(seeds=[1])) <= specifications
