"""Routes on the array grid must be the routes of the published router with the published mixed weight."""
import random

import numpy as np
import pytest

from common.coordinate import Coordinate
from noise.navigator.cost_function_generator import make_mixed_distance_noise_weight
from noise.navigator.grid_route_navigator import GridRouteNavigator
from noise.navigator.navigation_grid import calculate_mixed_edge_costs, read_navigation_grid_from_graph
from noise.navigator.warehouse_route_cache_generator import LONDON_WAREHOUSES, WarehouseRouteCacheGenerator
from tests.noise.test_navigation_grid import CELL_SIZE_M, build_published_graph

NUMBER_OF_ROWS, NUMBER_OF_COLUMNS = 30, 40
WAREHOUSE_LOCATIONS = [location for _, location in LONDON_WAREHOUSES]


def build_navigators(alpha: float, seed: int):
    graph = build_published_graph(NUMBER_OF_ROWS, NUMBER_OF_COLUMNS, seed)
    published = WarehouseRouteCacheGenerator(
        weight_builder=lambda g: make_mixed_distance_noise_weight(g, alpha, higher_noise_is_better=False),
        weight_id=None, graph=graph,
    )
    grid = read_navigation_grid_from_graph(graph, CELL_SIZE_M)
    return GridRouteNavigator(grid, calculate_mixed_edge_costs(grid, alpha), WAREHOUSE_LOCATIONS), published, graph


def list_trips_between_cells(navigator) -> list[tuple[Coordinate, Coordinate]]:
    """Out and back between every warehouse and 25 customers, leaving out customers in the warehouse's own
    cell: there the published router returns one point and the grid navigator none (tested below)."""
    return [
        trip
        for warehouse in WAREHOUSE_LOCATIONS
        for customer in random_customers(seed=11, number_of_customers=25)
        if navigator.find_nearest_cell(warehouse) != navigator.find_nearest_cell(customer)
        for trip in [(warehouse, customer), (customer, warehouse)]
    ]


def random_customers(seed: int, number_of_customers: int) -> list[Coordinate]:
    generator = random.Random(seed)
    return [
        Coordinate(
            northing=178_000.0 + generator.uniform(0.0, 100.0 * (NUMBER_OF_ROWS - 1)),
            easting=530_000.0 + generator.uniform(0.0, 100.0 * (NUMBER_OF_COLUMNS - 1)),
        )
        for _ in range(number_of_customers)
    ]


@pytest.mark.parametrize("alpha", [0.25, 0.5, 0.75])
def test_routes_to_and_from_every_warehouse_equal_the_published_router(alpha):
    navigator, published, _ = build_navigators(alpha, seed=5)

    trips = list_trips_between_cells(navigator)
    assert len(trips) > 600
    for start, end in trips:
        eastings, northings = navigator.get_optimal_route_coordinates(start, end)
        published_eastings, published_northings = published.get_optimal_route_coordinates(start, end)
        assert np.array_equal(eastings, published_eastings) and np.array_equal(northings, published_northings)


def sum_route_cost(graph, weight, eastings: np.ndarray, northings: np.ndarray) -> float:
    """Cost of a route given as cell centres; fails if two consecutive centres are not joined by an edge."""
    node_by_centre = {(attributes["easting"], attributes["northing"]): node for node, attributes in graph.nodes(data=True)}
    nodes = [node_by_centre[centre] for centre in zip(eastings.tolist(), northings.tolist())]
    return sum(weight(start, end, graph.edges[start, end]) for start, end in zip(nodes[:-1], nodes[1:]))


def test_with_edges_of_zero_cost_routes_are_still_as_cheap_as_the_published_ones():
    """alpha = 1: an edge between two cells of the lowest level costs nothing, so many routes are equally cheap.

    The published rule for choosing among them can loop, and the published router then searches the graph again
    for that route. The routes need not be the same cells, but they must cost the same and join the same ends.
    """
    navigator, published, graph = build_navigators(alpha=1.0, seed=5)
    weight = make_mixed_distance_noise_weight(graph, 1.0, higher_noise_is_better=False)

    for start, end in list_trips_between_cells(navigator):
        eastings, northings = navigator.get_optimal_route_coordinates(start, end)
        published_eastings, published_northings = published.get_optimal_route_coordinates(start, end)
        assert (eastings[0], northings[0]) == (published_eastings[0], published_northings[0])
        assert (eastings[-1], northings[-1]) == (published_eastings[-1], published_northings[-1])
        assert sum_route_cost(graph, weight, eastings, northings) == pytest.approx(
            sum_route_cost(graph, weight, published_eastings, published_northings), abs=1e-9
        )


def test_any_start_can_be_a_depot():
    """Depots are not known in advance (the revision has other depot layouts): a route from a place that is
    not yet a depot grows a tree there, and the way back is the reverse of the way out."""
    navigator, _, graph = build_navigators(alpha=0.25, seed=5)
    weight = make_mixed_distance_noise_weight(graph, 0.25, higher_noise_is_better=False)
    new_depot, customer = random_customers(seed=11, number_of_customers=2)

    eastings, northings = navigator.get_optimal_route_coordinates(new_depot, customer)
    back_eastings, back_northings = navigator.get_optimal_route_coordinates(customer, new_depot)

    assert sum_route_cost(graph, weight, eastings, northings) > 0.0
    assert np.array_equal(back_eastings, eastings[::-1]) and np.array_equal(back_northings, northings[::-1])


def test_a_customer_in_the_cell_of_its_depot_has_no_grid_route():
    """Both ends snap to the same cell, so the grid offers one point; the planner then flies straight
    instead of treating the delivery as a trip of zero length."""
    navigator, _, _ = build_navigators(alpha=0.25, seed=5)
    depot = WAREHOUSE_LOCATIONS[0]
    depot_cell = navigator.find_nearest_cell(depot)
    neighbour = Coordinate(
        northing=float(navigator.grid.northings[depot_cell]) + 20.0, easting=float(navigator.grid.eastings[depot_cell]) + 28.0
    )
    centre = Coordinate(northing=float(navigator.grid.northings[depot_cell]), easting=float(navigator.grid.eastings[depot_cell]))

    assert navigator.find_nearest_cell(neighbour) == depot_cell
    assert navigator.get_optimal_route_coordinates(centre, neighbour) is None
    assert navigator.get_optimal_route_coordinates(neighbour, centre) is None
