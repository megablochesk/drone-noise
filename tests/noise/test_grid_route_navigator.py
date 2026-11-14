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

    for warehouse in WAREHOUSE_LOCATIONS:
        for customer in random_customers(seed=11, number_of_customers=25):
            for start, end in [(warehouse, customer), (customer, warehouse)]:
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

    for warehouse in WAREHOUSE_LOCATIONS:
        for customer in random_customers(seed=11, number_of_customers=25):
            for start, end in [(warehouse, customer), (customer, warehouse)]:
                eastings, northings = navigator.get_optimal_route_coordinates(start, end)
                published_eastings, published_northings = published.get_optimal_route_coordinates(start, end)
                assert (eastings[0], northings[0]) == (published_eastings[0], published_northings[0])
                assert (eastings[-1], northings[-1]) == (published_eastings[-1], published_northings[-1])
                assert sum_route_cost(graph, weight, eastings, northings) == pytest.approx(
                    sum_route_cost(graph, weight, published_eastings, published_northings), abs=1e-9
                )


def test_a_route_between_two_customers_is_refused():
    """Trees exist for warehouses only; the simulation never asks for another kind of route."""
    navigator, _, _ = build_navigators(alpha=0.25, seed=5)
    first, second = random_customers(seed=11, number_of_customers=2)

    with pytest.raises(ValueError):
        navigator.get_optimal_route_coordinates(first, second)
