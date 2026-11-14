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

pytestmark = pytest.mark.slow
LEGACY_PLANNER_MODULE = load_legacy_module("route_planner/noise_based_planner.py")
NUMBER_OF_ROUTES = 300


def test_routes_to_three_hundred_customers_match_the_published_planner():
    """alpha = 0.5 with the stored route trees; every warehouse serves some of the customers."""
    destinations = generate_destinations(seed=1, number_of_orders=NUMBER_OF_ROUTES, zones=load_population_zones())
    warehouses = list(model_config.warehouses.bng_coordinates.values())
    with use_simulation_config(SimulationConfig(navigator_type=NavigationType.NOISE_A050, print_model_stats=False)):
        current = NoiseBasedPlanner("unused.csv")
    legacy = object.__new__(LEGACY_PLANNER_MODULE.NoiseBasedPlanner)
    legacy.navigator = current.navigator

    for order, (northing, easting) in enumerate(zip(destinations["end_northing"], destinations["end_easting"])):
        warehouse, customer = warehouses[order % len(warehouses)], Coordinate(northing=northing, easting=easting)
        assert current.plan_route(warehouse, customer) == legacy.plan_route(warehouse, customer)
        assert current.plan_route(customer, warehouse) == legacy.plan_route(customer, warehouse)
