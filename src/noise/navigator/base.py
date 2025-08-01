from abc import ABC, abstractmethod
from typing import List, Tuple

from common.coordinate import Coordinate
from noise.noise_graph_builder import load_or_build_graph


class BaseNavigator(ABC):
    def __init__(self):
        self.graph = load_or_build_graph()

    @abstractmethod
    def get_optimal_route(
        self, start: Coordinate, end: Coordinate
    ) -> List[Tuple[int, int]]:
        ...

    def nodes_to_coordinates(self, nodes):
        return [
            Coordinate(
                northing=self.graph.nodes[node]["northing"],
                easting=self.graph.nodes[node]["easting"],
            )
            for node in nodes
        ]