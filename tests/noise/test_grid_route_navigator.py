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
    return GridRouteNavigator(grid, calculate_mixed_edge_costs(grid, alpha), WAREHOUSE_LOCATIONS), published


def random_customers(seed: int, number_of_customers: int) -> list[Coordinate]:
    generator = random.Random(seed)
    return [
        Coordinate(
            northing=178_000.0 + generator.uniform(0.0, 100.0 * (NUMBER_OF_ROWS - 1)),
            easting=530_000.0 + generator.uniform(0.0, 100.0 * (NUMBER_OF_COLUMNS - 1)),
        )
        for _ in range(number_of_customers)
    ]


@pytest.mark.parametrize("alpha", [0.25, 0.5, 0.75, 1.0])
def test_routes_to_and_from_every_warehouse_equal_the_published_router(alpha):
    navigator, published = build_navigators(alpha, seed=5)

    for warehouse in WAREHOUSE_LOCATIONS:
        for customer in random_customers(seed=11, number_of_customers=25):
            for start, end in [(warehouse, customer), (customer, warehouse)]:
                eastings, northings = navigator.get_optimal_route_coordinates(start, end)
                published_eastings, published_northings = published.get_optimal_route_coordinates(start, end)
                assert np.array_equal(eastings, published_eastings) and np.array_equal(northings, published_northings)


def test_a_route_between_two_customers_is_refused():
    """Trees exist for warehouses only; the simulation never asks for another kind of route."""
    navigator, _ = build_navigators(alpha=0.25, seed=5)
    first, second = random_customers(seed=11, number_of_customers=2)

    with pytest.raises(ValueError):
        navigator.get_optimal_route_coordinates(first, second)
