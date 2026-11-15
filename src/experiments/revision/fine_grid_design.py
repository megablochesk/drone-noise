"""The design of the revision: Round 4 baseline, 100 m noise cells and a 10 s time step on the pilot factorial,
with the study boundary read on the datum its file is written on."""
from dataclasses import replace

from common.enum import BaselineNoiseMap, BoundaryDatum, NavigationType
from experiments.revision.revision_design import ALL_STOCKINGS, PILOT_FLEETS, TERMINAL_MODES, build_factorial_specifications
from experiments.revision.run_specification import RunSpecification

FINE_CELL_SIZE_M = 100
FINE_TIME_STEP_S = 10
# The cell average that is closer to the pixel-level reference at 100 m (REPORT.md, "Fine grid").
FINE_BASELINE_NOISE_MAP = BaselineNoiseMap.ROUND_4_ROAD
# The boundary file holds OSGB36 latitudes and longitudes; read so, it meets the census extent within metres.
FINE_BOUNDARY_DATUM = BoundaryDatum.OSGB36
PHASE_NAME = "fine_grid"
PAPER_FLEETS = (1250, 1000, 750, 500, 250, 100)
SLANT_FLOOR_FLEET = 1250
SLANT_FLOOR_M = 10.0
NOISE_AWARE_NAVIGATIONS = (
    NavigationType.NOISE_A025, NavigationType.NOISE_A050, NavigationType.NOISE_A075, NavigationType.NOISE_A100,
)


def build_fine_grid_specifications(seeds: list[int], fleets: tuple[int, ...] = PILOT_FLEETS) -> list[RunSpecification]:
    """Fleet x stocking x terminal mode for every seed, largest fleet first."""
    factorial = build_factorial_specifications(seeds, list(fleets), list(ALL_STOCKINGS), list(TERMINAL_MODES))
    return [
        replace(
            specification, noise_cell_m=FINE_CELL_SIZE_M, time_step_s=FINE_TIME_STEP_S,
            baseline_noise_map=FINE_BASELINE_NOISE_MAP, boundary_datum=FINE_BOUNDARY_DATUM,
        )
        for specification in factorial
    ]


def build_single_landing_specifications(seeds: list[int]) -> list[RunSpecification]:
    """The runs of the design that have terminal phases, with one landing per delivery instead of two."""
    return [
        replace(specification, land_once_at_customer=True)
        for specification in build_fine_grid_specifications(seeds) if specification.terminal_phases
    ]


def select_largest_fleet_terminal_runs(seeds: list[int]) -> list[RunSpecification]:
    return [
        specification for specification in build_fine_grid_specifications(seeds)
        if specification.terminal_phases and specification.number_of_drones == SLANT_FLOOR_FLEET
    ]


def build_slant_floor_specifications(seeds: list[int]) -> list[RunSpecification]:
    """The largest-fleet runs with terminal phases, with the slant distance to a cell centre floored."""
    return [
        replace(specification, minimum_slant_distance_m=SLANT_FLOOR_M)
        for specification in select_largest_fleet_terminal_runs(seeds)
    ]


def build_noise_aware_specifications(seeds: list[int]) -> list[RunSpecification]:
    """The largest-fleet runs with terminal phases, routed around the noise of the baseline map at every alpha."""
    return [
        replace(specification, navigation=navigation)
        for navigation in NOISE_AWARE_NAVIGATIONS
        for specification in select_largest_fleet_terminal_runs(seeds)
    ]


def build_paper_figure_specifications(seeds: list[int]) -> list[RunSpecification]:
    """The paper's fleets with straight routing (both terminal modes) and noise-aware routing (terminal phases)."""
    straight = build_fine_grid_specifications(seeds, PAPER_FLEETS)
    return straight + [
        replace(specification, navigation=navigation)
        for navigation in NOISE_AWARE_NAVIGATIONS
        for specification in straight if specification.terminal_phases
    ]


DESIGN_BUILDERS = {
    "pilot": build_fine_grid_specifications,
    "single-landing": build_single_landing_specifications,
    "slant-floor": build_slant_floor_specifications,
    "noise-aware": build_noise_aware_specifications,
    "paper-figures": build_paper_figure_specifications,
}


def build_design_specifications(design_name: str, seeds: list[int]) -> list[RunSpecification]:
    """The specifications of a named design: the same names select it on one machine and in a job array."""
    if design_name not in DESIGN_BUILDERS:
        raise ValueError(f"Unknown design {design_name}; the designs are {', '.join(DESIGN_BUILDERS)}")
    return DESIGN_BUILDERS[design_name](seeds)


def select_task_specification(specifications: list[RunSpecification], task_index: int) -> RunSpecification:
    """The specification of one task of a job array; tasks are numbered from zero in design order."""
    if not 0 <= task_index < len(specifications):
        raise IndexError(f"Task {task_index} is outside the design of {len(specifications)} specifications")
    return specifications[task_index]
