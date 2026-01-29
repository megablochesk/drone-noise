from __future__ import annotations

from typing import Iterable, List, Tuple

import networkx as nx

from common.coordinate import Coordinate
from noise.noise_graph_builder import load_or_build_graph

GridNode = Tuple[int, int]


class BaseNavigator:
    def __init__(self, graph: nx.Graph | None = None):
        self.graph: nx.Graph = graph if graph is not None else load_or_build_graph()

    def get_optimal_route(self, start: Coordinate, end: Coordinate) -> List[GridNode]:
        raise NotImplementedError

    def nodes_to_coordinates(self, nodes: Iterable[GridNode]) -> List[Coordinate]:
        out: List[Coordinate] = []
        for n in nodes:
            attrs = self.graph.nodes[n]
            e = attrs.get("easting")
            no = attrs.get("northing")

            if e is None or no is None:
                pos = attrs.get("pos")
                if pos is None:
                    raise KeyError(f"Node {n} is missing (easting,northing) and pos.")
                e, no = pos[0], pos[1]

            out.append(Coordinate(northing=no, easting=e))
        return out
