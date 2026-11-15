"""Noise-aware routes on the real navigation graph are those of the planner at the published baseline commit."""
import pytest

from common.coordinate import Coordinate
from common.enum import NavigationType
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import generate_destinations
from route_planner.noise_based_planner import NoiseBasedPlanner
from tests.legacy_reference import load_legacy_module

LEGACY_PLANNER_MODULE = load_legacy_module("route_planner/noise_based_planner.py")
DESTINATION_SEED = 1
SAMPLED_NUMBER_OF_ROUTES = 20


def assert_routes_match_the_published_planner(number_of_routes: int):
    """alpha = 0.5 with the stored route trees; warehouses take the customers in turn, so all of them serve some."""
    destinations = generate_destinations(
        seed=DESTINATION_SEED, number_of_orders=number_of_routes, zones=load_population_zones()
    )
    warehouses = list(model_config.warehouses.bng_coordinates.values())
    with use_simulation_config(SimulationConfig(navigator_type=NavigationType.NOISE_A050, print_model_stats=False)):
        current = NoiseBasedPlanner("unused.csv")
    legacy = object.__new__(LEGACY_PLANNER_MODULE.NoiseBasedPlanner)
    legacy.navigator = current.navigator

    assert number_of_routes >= len(warehouses)
    for order, (northing, easting) in enumerate(zip(destinations["end_northing"], destinations["end_easting"])):
        warehouse, customer = warehouses[order % len(warehouses)], Coordinate(northing=northing, easting=easting)
        assert current.plan_route(warehouse, customer) == legacy.plan_route(warehouse, customer)
        assert current.plan_route(customer, warehouse) == legacy.plan_route(customer, warehouse)


def test_routes_to_twenty_seeded_customers_match_the_published_planner():
    assert_routes_match_the_published_planner(SAMPLED_NUMBER_OF_ROUTES)
