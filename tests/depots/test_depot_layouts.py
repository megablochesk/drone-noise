"""Depot layouts: geometry on hand-built shapes first, then the invariants of the layouts used in Phase 9."""
import math
from collections import Counter

import numpy as np
import pytest
from shapely.geometry import Point, box

from common.coordinate import Coordinate, calculate_distance
from common.model_configs import model_config
from depots.depot_layouts import (
    ACTUAL_LAYOUT,
    NUMBER_OF_STYLISED_DEPOTS,
    POPULATION_KMEANS_LAYOUT,
    RANDOM_DRAW_LAYOUTS,
    RING_LAYOUT,
    RING_RADIUS_M,
    SINGLE_HUB_LAYOUT,
    calculate_population_weighted_centre,
    cluster_population_weighted_centres,
    load_study_boundary,
    place_depots_on_ring,
    resolve_depot_layout,
    sample_uniform_depots,
    snap_inside_boundary,
)
from simulation.fleet_allocation import allocate_fleet_equally

STYLISED_LAYOUTS = [RING_LAYOUT, POPULATION_KMEANS_LAYOUT, *RANDOM_DRAW_LAYOUTS]
SQUARE_BOUNDARY = box(-5_000.0, -5_000.0, 5_000.0, 5_000.0)
ORIGIN = Coordinate(northing=0.0, easting=0.0)


def test_population_weighted_centre_of_two_cells():
    """Populations 1 and 3 at eastings 0 and 4 (northings 10 and 20): centre (1*0 + 3*4)/4 = 3 E,
    (1*10 + 3*20)/4 = 17.5 N."""
    centre = calculate_population_weighted_centre(
        eastings=np.array([0.0, 4.0]), northings=np.array([10.0, 20.0]), population=np.array([1.0, 3.0])
    )
    assert (centre.easting, centre.northing) == pytest.approx((3.0, 17.5))


def test_four_ring_depots_sit_on_the_axes():
    """Four depots on a 10 m ring around the origin: east, north, west, south."""
    depots = place_depots_on_ring(ORIGIN, radius_m=10.0, number_of_depots=4)
    positions = [(depot.easting, depot.northing) for depot in depots]
    np.testing.assert_allclose(positions, [(10.0, 0.0), (0.0, 10.0), (-10.0, 0.0), (0.0, -10.0)], atol=1e-9)


def test_ring_depots_are_evenly_spaced_at_the_stated_radius():
    """Invariant: all 14 at the radius; neighbouring depots a chord 2*r*sin(pi/14) apart."""
    depots = place_depots_on_ring(ORIGIN, radius_m=18_000.0, number_of_depots=14)
    assert [calculate_distance(ORIGIN, depot) for depot in depots] == pytest.approx([18_000.0] * 14)
    chord_m = 2 * 18_000.0 * math.sin(math.pi / 14)
    neighbour_distances = [calculate_distance(depots[index], depots[(index + 1) % 14]) for index in range(14)]
    assert neighbour_distances == pytest.approx([chord_m] * 14)


def test_point_outside_the_boundary_is_pulled_towards_the_centre():
    """A point 9 km east of the centre of a 10 km square leaves it at 5 km; with a 250 m inset it ends at
    4,750 m east, on the same bearing."""
    snapped = snap_inside_boundary(Coordinate(northing=0.0, easting=9_000.0), ORIGIN, SQUARE_BOUNDARY, inset_m=250.0)
    assert (snapped.easting, snapped.northing) == pytest.approx((4_750.0, 0.0))


def test_point_inside_the_boundary_is_left_alone():
    """Invariant: snapping never moves a point that is already inside."""
    inside = Coordinate(northing=1_000.0, easting=-2_000.0)
    assert snap_inside_boundary(inside, ORIGIN, SQUARE_BOUNDARY, inset_m=250.0) == inside


def test_weighted_clustering_finds_the_weighted_means_of_two_separate_groups():
    """Group one: eastings 0 and 2 with populations 1 and 3 -> 1.5. Group two: eastings 100 and 104 with
    populations 2 and 2 -> 102. All northings are 0."""
    centres = cluster_population_weighted_centres(
        eastings=np.array([0.0, 2.0, 100.0, 104.0]), northings=np.zeros(4),
        population=np.array([1.0, 3.0, 2.0, 2.0]), number_of_depots=2, seed=0,
    )
    assert sorted(centre.easting for centre in centres) == pytest.approx([1.5, 102.0])


def test_uniform_depots_are_seeded_and_inside():
    """Invariants: requested count, inside the boundary, pure function of the seed."""
    first = sample_uniform_depots(SQUARE_BOUNDARY, number_of_depots=14, seed=3)
    assert len(first) == 14
    assert all(SQUARE_BOUNDARY.contains(Point(depot.easting, depot.northing)) for depot in first)
    assert first == sample_uniform_depots(SQUARE_BOUNDARY, number_of_depots=14, seed=3)
    assert first != sample_uniform_depots(SQUARE_BOUNDARY, number_of_depots=14, seed=4)


def test_actual_layout_is_the_published_set_of_fourteen_sites():
    """Published configuration: the 14 named sites of `Warehouses.london_default`."""
    depots = resolve_depot_layout(ACTUAL_LAYOUT)
    assert len(depots) == 14
    assert depots == model_config.warehouses.bng_coordinates


def test_single_hub_is_one_depot_at_the_population_weighted_centre():
    """The brief asks for one hub; central London lies near 530 km E, 180 km N on the national grid, and a
    population-weighted centre must fall within a few kilometres of it."""
    depots = resolve_depot_layout(SINGLE_HUB_LAYOUT)
    assert len(depots) == 1
    hub = next(iter(depots.values()))
    assert calculate_distance(hub, Coordinate(northing=180_000.0, easting=530_000.0)) < 5_000.0


@pytest.mark.parametrize("layout_name", STYLISED_LAYOUTS)
def test_stylised_layouts_have_fourteen_distinct_depots_inside_the_boundary(layout_name):
    """Brief: 14 depots per stylised layout, all inside the Greater London boundary."""
    depots = resolve_depot_layout(layout_name)
    boundary = load_study_boundary()
    assert len(depots) == NUMBER_OF_STYLISED_DEPOTS == 14
    assert len(set(depots.values())) == 14
    assert all(boundary.contains(Point(depot.easting, depot.northing)) for depot in depots.values())


def test_five_random_draws_are_all_different():
    """Brief: five draws; different seeds must give different layouts."""
    assert len(RANDOM_DRAW_LAYOUTS) == 5
    layouts = [tuple(resolve_depot_layout(layout_name).values()) for layout_name in RANDOM_DRAW_LAYOUTS]
    assert len(set(layouts)) == 5


def test_ring_depots_are_at_eighteen_kilometres_unless_snapped_inwards():
    """Brief: ring at 18 km from the hub. A depot is either on the ring (to the 1 cm coordinate rounding)
    or was pulled inside the boundary and is therefore closer."""
    hub = next(iter(resolve_depot_layout(SINGLE_HUB_LAYOUT).values()))
    distances_m = [calculate_distance(hub, depot) for depot in resolve_depot_layout(RING_LAYOUT).values()]
    assert RING_RADIUS_M == 18_000.0
    assert all(distance_m <= RING_RADIUS_M + 0.02 for distance_m in distances_m)
    assert any(distance_m == pytest.approx(RING_RADIUS_M, abs=0.02) for distance_m in distances_m)


@pytest.mark.parametrize("layout_name", [ACTUAL_LAYOUT, SINGLE_HUB_LAYOUT, *STYLISED_LAYOUTS])
@pytest.mark.parametrize("number_of_drones", [500, 1250])
def test_fleet_split_over_a_layout_sums_to_the_total_fleet(layout_name, number_of_drones):
    """Brief: total fleet unchanged, split equally (shares differ by at most one drone)."""
    homes = allocate_fleet_equally(resolve_depot_layout(layout_name).values(), number_of_drones)
    drones_per_depot = Counter(homes).values()
    assert sum(drones_per_depot) == number_of_drones
    assert max(drones_per_depot) - min(drones_per_depot) <= 1
