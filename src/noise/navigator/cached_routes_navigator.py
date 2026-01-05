from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from common.coordinate import Coordinate
from common.file_utils import load_data_from_pickle, path_exists, save_data_as_pickle
from common.path_configs import get_noise_navigation_route_orders_file
from common.runtime_configs import get_simulation_config
from noise.navigator.navigator_base import BaseNavigator
from noise.navigator.warehouse_route_cache_generator import WarehouseRouteCacheGenerator

runtime_simulation_config = get_simulation_config()

GridNode = Tuple[int, int]


class CachedRoutesNavigator(BaseNavigator):
    def __init__(
        self,
        order_route_path: Optional[str] = None,
        build_with_heavy: bool = False,
        save_on_build: bool = True,
        heavy: WarehouseRouteCacheGenerator | None = None,
    ):
        super().__init__()

        if order_route_path is None:
            order_route_path = runtime_simulation_config.order_dataset_path

        self._route_pickle_path = get_noise_navigation_route_orders_file(order_route_path)
        self._save_on_build = save_on_build
        self._heavy = heavy if heavy is not None else (WarehouseRouteCacheGenerator() if build_with_heavy else None)

        if path_exists(self._route_pickle_path):
            self._routes: Dict[Tuple[Coordinate, Coordinate], List[GridNode]] = load_data_from_pickle(self._route_pickle_path)
        else:
            if self._heavy is None:
                raise FileNotFoundError(self._route_pickle_path)
            self._routes = {}

    def get_optimal_route(self, start: Coordinate, end: Coordinate) -> List[GridNode] | None:
        exact = self._routes.get((start, end))
        if exact is not None:
            return exact

        rev = self._routes.get((end, start))
        if rev is not None:
            return list(reversed(rev))

        if self._heavy is None:
            return None

        path = self._heavy.get_optimal_route(start, end)
        self._routes[(start, end)] = path

        if self._save_on_build:
            save_data_as_pickle(self._routes, self._route_pickle_path)

        return path
