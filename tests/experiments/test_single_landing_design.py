"""The fine-grid design repeated with one landing per delivery, for the configurations that have terminal phases."""
from dataclasses import replace

from experiments.revision.fine_grid_design import build_fine_grid_specifications, build_single_landing_specifications


def test_single_landing_runs_are_the_terminal_phase_runs_of_the_design_with_the_switch_on():
    """9 of the 18 configurations of a seed have terminal phases."""
    single_landing = build_single_landing_specifications(seeds=[1, 2, 3])
    with_terminal_phases = [s for s in build_fine_grid_specifications(seeds=[1, 2, 3]) if s.terminal_phases]

    assert len(single_landing) == 27
    assert all(specification.land_once_at_customer and specification.terminal_phases for specification in single_landing)
    assert [replace(specification, land_once_at_customer=False) for specification in single_landing] == with_terminal_phases
