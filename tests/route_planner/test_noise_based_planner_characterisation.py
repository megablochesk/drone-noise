"""Characterisation of noise-aware route planning against the planner source at the published baseline commit.

The navigation graph is replaced by a small grid with the same layout (8 neighbours, 100 m spacing, easting
and northing on every node), so no data file is needed. Both planners use the same navigator; what is
compared is everything the planner does with a route: node coordinates, resampling by flight time, end points.
"""
import random

import networkx as nx
import pytest

from common.coordinate import Coordinate
from noise.navigator.warehouse_route_cache_generator import WarehouseRouteCacheGenerator
from route_planner.noise_based_planner import NoiseBasedPlanner, resample_polyline_by_time
from tests.legacy_reference import load_legacy_module

LEGACY_PLANNER_MODULE = load_legacy_module("route_planner/noise_based_planner.py")
GRID_ROWS, GRID_COLUMNS = 40, 50
CELL_SPACING_M = 100.0
GRID_WEST_M, GRID_SOUTH_M = 530_000.0, 178_000.0
NEIGHBOUR_SHIFTS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
PUBLISHED_SPEED_MPS, PUBLISHED_TIME_STEP_S = 27.0, 30.0


def build_navigation_grid(seed: int) -> nx.Graph:
    generator = random.Random(seed)
    graph = nx.Graph()
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            graph.add_node(
                (row, column), easting=GRID_WEST_M + column * CELL_SPACING_M, northing=GRID_SOUTH_M + row * CELL_SPACING_M,
            )
    for row, column in list(graph.nodes):
        for row_shift, column_shift in NEIGHBOUR_SHIFTS:
            neighbour = (row + row_shift, column + column_shift)
            if neighbour in graph and not graph.has_edge((row, column), neighbour):
                graph.add_edge((row, column), neighbour, cost=generator.uniform(0.5, 3.0))
    return graph


def read_cost(_start, _end, edge_data) -> float:
    return edge_data["cost"]


def build_planners(seed: int):
    """A navigator on the small grid, shared by a current and a published planner."""
    navigator = WarehouseRouteCacheGenerator(weight=read_cost, weight_id=None, graph=build_navigation_grid(seed))
    current, legacy = NoiseBasedPlanner.__new__(NoiseBasedPlanner), object.__new__(LEGACY_PLANNER_MODULE.NoiseBasedPlanner)
    current.navigator = legacy.navigator = navigator
    return current, legacy, navigator


def random_location(generator: random.Random) -> Coordinate:
    return Coordinate(
        northing=round(generator.uniform(GRID_SOUTH_M, GRID_SOUTH_M + (GRID_ROWS - 1) * CELL_SPACING_M), 2),
        easting=round(generator.uniform(GRID_WEST_M, GRID_WEST_M + (GRID_COLUMNS - 1) * CELL_SPACING_M), 2),
    )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_planned_routes_match_the_published_planner(seed):
    """Routes out of a warehouse node, back into it, and between arbitrary points; long, short and zero length."""
    current, legacy, navigator = build_planners(seed)
    generator = random.Random(seed)
    warehouse = Coordinate(northing=GRID_SOUTH_M + 2_000.0, easting=GRID_WEST_M + 2_500.0)
    customers = [random_location(generator) for _ in range(60)]
    near_customer = Coordinate(northing=warehouse.northing + 40.0, easting=warehouse.easting + 30.0)
    pairs = [(warehouse, customer) for customer in customers] + [(customer, warehouse) for customer in customers[:20]]
    pairs += [(customers[0], customers[1]), (warehouse, near_customer), (warehouse, warehouse)]

    for start, end in pairs:
        assert current.plan_route(start, end) == legacy.plan_route(start, end)


def random_polyline(generator: random.Random, number_of_points: int) -> list[Coordinate]:
    points = [random_location(generator)]
    for _ in range(number_of_points - 1):
        step_m = generator.choice([0.0, 100.0, 141.42, 100.0])
        points.append(Coordinate(northing=points[-1].northing + step_m * generator.uniform(-1, 1), easting=points[-1].easting + step_m))
    return points


@pytest.mark.parametrize("number_of_points", [1, 2, 3, 10, 200])
@pytest.mark.parametrize("time_step_s", [10.0, 30.0, 600.0])
def test_resampling_by_flight_time_matches_the_published_function(number_of_points, time_step_s):
    """Polylines with repeated points (zero-length segments), fewer points than a segment needs, and a time
    step longer than the whole flight."""
    generator = random.Random(number_of_points)
    for _ in range(20):
        polyline = random_polyline(generator, number_of_points)
        assert resample_polyline_by_time(list(polyline), PUBLISHED_SPEED_MPS, time_step_s) == \
               LEGACY_PLANNER_MODULE.resample_polyline_by_time(list(polyline), PUBLISHED_SPEED_MPS, time_step_s)
