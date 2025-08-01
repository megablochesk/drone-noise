from typing import Dict, List, Tuple

from common.configuration import get_noise_navigation_route_orders_file, ORDER_BASE_PATH
from common.coordinate import Coordinate
from common.file_utils import load_data_from_pickle, path_exists
from .base import BaseNavigator


class LightNavigator(BaseNavigator):
    def __init__(self, order_route_path=None):
        super().__init__()

        if order_route_path is None:
            order_route_path = ORDER_BASE_PATH

        route_pickle_path = get_noise_navigation_route_orders_file(order_route_path)

        if not path_exists(route_pickle_path):
            raise FileNotFoundError(route_pickle_path)

        self._routes: Dict[
            Tuple[Coordinate, Coordinate], List[Tuple[int, int]]
        ] = load_data_from_pickle(route_pickle_path)

    def get_optimal_route(self, start: Coordinate, end: Coordinate) -> List[Tuple[int, int]]:
        exact_route = self._routes.get((start, end))

        if exact_route is not None:
            return exact_route

        reversed_route = self._routes.get((end, start))

        return list(reversed(reversed_route)) if reversed_route is not None else None
