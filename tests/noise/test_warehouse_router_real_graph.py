"""The router on the real navigation graph reproduces a stored cache of the published noise-aware runs."""
import pickle

import numpy as np
import pytest

from common.path_configs import PATH_CONFIGS
from noise.navigator.cost_function_generator import make_mixed_distance_noise_weight
from noise.navigator.warehouse_dijkstra_router import WarehouseDijkstraRouter, _tagged_cache_path
from noise.noise_graph_builder import load_or_build_graph

pytestmark = pytest.mark.slow
ALPHA = 0.5
STORED_CACHE_TAG = "mixed__a=0.50__dist=distance__noise=noise__hnib=0"
CHECKED_WAREHOUSES = 3


def test_trees_equal_the_stored_cache_of_the_published_runs():
    graph = load_or_build_graph()
    with open(_tagged_cache_path(PATH_CONFIGS.warehouse_paths_cache(), STORED_CACHE_TAG), "rb") as cache_file:
        stored = pickle.load(cache_file)
    weight = make_mixed_distance_noise_weight(graph=graph, alpha=ALPHA, higher_noise_is_better=False)
    warehouses = list(stored["spt"])[:CHECKED_WAREHOUSES]
    router = WarehouseDijkstraRouter(graph, warehouses, weight)

    assert router._nodes == stored["nodes"]
    for warehouse in warehouses:
        tree = router._build_spt(warehouse)
        np.testing.assert_array_equal(tree.pred_idx, stored["spt"][warehouse]["pred_idx"])
        np.testing.assert_array_equal(tree.dist, stored["spt"][warehouse]["dist"])
