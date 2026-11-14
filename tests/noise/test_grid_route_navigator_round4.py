"""The array navigator on the real Round 4 grid at 100 m: routes are connected and end where they should."""
import math

import numpy as np
import pytest

import noise.navigator as navigator_factory
from common.coordinate import Coordinate
from common.enum import BaselineNoiseMap, NavigationType
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from noise.noise_data_processor import load_base_noise_data

pytestmark = pytest.mark.slow
CELL_SIZE_M = 100
LONGEST_STEP_M = CELL_SIZE_M * math.sqrt(2.0) + 1e-6
CUSTOMERS = [
    Coordinate(northing=181_250.0, easting=532_480.0), Coordinate(northing=165_930.0, easting=511_020.0),
    Coordinate(northing=196_410.0, easting=552_770.0),
]


@pytest.mark.parametrize("navigation", [NavigationType.NOISE_A025, NavigationType.NOISE_A100])
def test_routes_from_every_warehouse_are_chains_of_neighbouring_cells(navigation):
    with use_simulation_config(SimulationConfig(baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD)):
        navigator = navigator_factory.get_navigator(navigation)

    assert len(navigator.grid.rows) == len(load_base_noise_data(BaselineNoiseMap.ROUND_4_ROAD, CELL_SIZE_M))
    for warehouse in model_config.warehouses.bng_coordinates.values():
        for customer in CUSTOMERS:
            eastings, northings = navigator.get_optimal_route_coordinates(warehouse, customer)
            steps_m = np.hypot(np.diff(eastings), np.diff(northings))
            assert steps_m.max() <= LONGEST_STEP_M and steps_m.min() >= CELL_SIZE_M - 1e-6
            assert math.hypot(eastings[0] - warehouse.easting, northings[0] - warehouse.northing) <= CELL_SIZE_M
            assert math.hypot(eastings[-1] - customer.easting, northings[-1] - customer.northing) <= CELL_SIZE_M
            back_eastings, back_northings = navigator.get_optimal_route_coordinates(customer, warehouse)
            assert np.array_equal(back_eastings, eastings[::-1]) and np.array_equal(back_northings, northings[::-1])
