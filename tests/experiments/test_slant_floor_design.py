"""The largest-fleet terminal-phase runs of the fine-grid design repeated with a 10 m floor on the slant distance."""
from dataclasses import replace

from experiments.revision.fine_grid_design import (
    SLANT_FLOOR_FLEET,
    SLANT_FLOOR_M,
    build_fine_grid_specifications,
    build_slant_floor_specifications,
)


def test_slant_floor_runs_are_the_largest_fleet_terminal_runs_with_the_floor_set():
    """One fleet x three stockings x one terminal mode = 3 runs per seed."""
    floored = build_slant_floor_specifications(seeds=[1, 2])
    unfloored = [
        specification for specification in build_fine_grid_specifications(seeds=[1, 2])
        if specification.terminal_phases and specification.number_of_drones == SLANT_FLOOR_FLEET
    ]

    assert (SLANT_FLOOR_FLEET, SLANT_FLOOR_M) == (1250, 10.0)
    assert len(floored) == 6
    assert all(specification.minimum_slant_distance_m == 10.0 for specification in floored)
    assert [replace(specification, minimum_slant_distance_m=0.0) for specification in floored] == unfloored
