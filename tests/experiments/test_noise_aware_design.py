"""The largest-fleet terminal-phase runs of the fine-grid design repeated with noise-aware routing."""
from dataclasses import replace

from common.enum import NavigationType
from experiments.revision.fine_grid_design import (
    NOISE_AWARE_NAVIGATIONS,
    SLANT_FLOOR_FLEET,
    build_fine_grid_specifications,
    build_noise_aware_specifications,
)


def test_noise_aware_runs_are_the_largest_fleet_terminal_runs_at_every_alpha():
    """Three stockings x four alphas = 12 runs per seed, each the same run as its straight-line counterpart."""
    noise_aware = build_noise_aware_specifications(seeds=[1, 2])
    straight = [
        specification for specification in build_fine_grid_specifications(seeds=[1, 2])
        if specification.terminal_phases and specification.number_of_drones == SLANT_FLOOR_FLEET
    ]

    assert NOISE_AWARE_NAVIGATIONS == (
        NavigationType.NOISE_A025, NavigationType.NOISE_A050, NavigationType.NOISE_A075, NavigationType.NOISE_A100,
    )
    assert len(noise_aware) == 24
    for navigation in NOISE_AWARE_NAVIGATIONS:
        of_this_alpha = [specification for specification in noise_aware if specification.navigation is navigation]
        assert [replace(specification, navigation=NavigationType.STRAIGHT) for specification in of_this_alpha] == straight
