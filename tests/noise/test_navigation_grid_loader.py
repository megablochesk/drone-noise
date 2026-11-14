"""Noise-aware routes avoid the noise of the run's own baseline map."""
import numpy as np
import pandas as pd
import pytest

import noise.navigator as navigator_factory
from common.enum import BaselineNoiseMap, NavigationType
from common.model_configs import MapBoundaries
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from noise.navigator.grid_route_navigator import GridRouteNavigator
from noise.navigator.navigation_grid import calculate_mixed_edge_costs
from noise.navigator.navigation_grid_loader import build_navigation_grid_from_baseline

CELL_SIZE_M = 100
BOUNDARIES = MapBoundaries(left=1_000.0, right=1_300.0, top=5_200.0, bottom=5_000.0)


def build_small_baseline() -> pd.DataFrame:
    """Two rows of three cells, listed column by column."""
    return pd.DataFrame({
        "row": [0, 1, 0, 1, 0, 1], "col": [0, 0, 1, 1, 2, 2], "noise_level": [40.0, 45.0, 50.0, 55.0, 60.0, 80.0],
    })


def test_grid_from_a_baseline_table_puts_each_node_at_its_cell_centre():
    """Cell (row 1, column 2) of a grid with its corner at (1000, 5000): centre at (1250, 5150)."""
    grid = build_navigation_grid_from_baseline(build_small_baseline(), CELL_SIZE_M, BOUNDARIES)

    assert list(zip(grid.rows.tolist(), grid.columns.tolist())) == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
    assert grid.noise_levels_db.tolist() == [40.0, 50.0, 60.0, 45.0, 55.0, 80.0]
    assert (grid.eastings[5], grid.northings[5]) == (1_250.0, 5_150.0)
    assert (grid.eastings[0], grid.northings[0]) == (1_050.0, 5_050.0)
    assert grid.cell_size_m == CELL_SIZE_M and len(grid.edge_starts) == 11


@pytest.fixture
def small_grid_for_every_map(monkeypatch):
    grid = build_navigation_grid_from_baseline(build_small_baseline(), CELL_SIZE_M, BOUNDARIES)
    requested_maps = []

    def load_small_grid(baseline_noise_map):
        requested_maps.append(baseline_noise_map)
        return grid

    monkeypatch.setattr(navigator_factory, "load_navigation_grid", load_small_grid)
    navigator_factory.clear_navigator_cache()
    yield grid, requested_maps
    navigator_factory.clear_navigator_cache()


def test_a_run_on_another_baseline_map_routes_on_the_grid_of_that_map(small_grid_for_every_map):
    grid, requested_maps = small_grid_for_every_map
    config = SimulationConfig(baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD, navigator_type=NavigationType.NOISE_A050)

    with use_simulation_config(config):
        navigator = navigator_factory.get_navigator(NavigationType.NOISE_A050)
        same_navigator = navigator_factory.get_navigator(NavigationType.NOISE_A050)
        other_alpha = navigator_factory.get_navigator(NavigationType.NOISE_A025)

    assert isinstance(navigator, GridRouteNavigator) and same_navigator is navigator
    assert requested_maps == [BaselineNoiseMap.ROUND_4_ROAD, BaselineNoiseMap.ROUND_4_ROAD]
    np.testing.assert_array_equal(navigator.edge_costs, calculate_mixed_edge_costs(grid, 0.5))
    np.testing.assert_array_equal(other_alpha.edge_costs, calculate_mixed_edge_costs(grid, 0.25))


def test_navigators_of_two_maps_are_kept_apart(small_grid_for_every_map):
    with use_simulation_config(SimulationConfig(baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD)):
        arithmetic = navigator_factory.get_navigator(NavigationType.NOISE_A050)
    with use_simulation_config(SimulationConfig(baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD_ENERGY)):
        energy = navigator_factory.get_navigator(NavigationType.NOISE_A050)

    assert arithmetic is not energy
    assert small_grid_for_every_map[1] == [BaselineNoiseMap.ROUND_4_ROAD, BaselineNoiseMap.ROUND_4_ROAD_ENERGY]
