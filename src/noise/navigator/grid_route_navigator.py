"""Routes between warehouses and customers on the array navigation grid.

The shortest-path tree of a warehouse is built on first use (a fraction of a second), so nothing is cached on
disk and a tree can never belong to another noise map or cost.
"""
import numpy as np
from scipy.spatial import cKDTree

from common.coordinate import Coordinate
from noise.navigator.navigation_grid import NavigationGrid
from noise.navigator.shortest_path_tree import calculate_search_tree, calculate_shortest_path_tree
from noise.navigator.warehouse_dijkstra_router import follow_parents_from_target


class GridRouteNavigator:
    def __init__(self, grid: NavigationGrid, edge_costs: np.ndarray, warehouse_locations: list[Coordinate]):
        self.grid = grid
        self.edge_costs = edge_costs
        self.cell_centres = cKDTree(np.column_stack([grid.eastings, grid.northings]))
        self.cell_by_warehouse = {location: self._query_nearest_cell(location) for location in warehouse_locations}
        self.warehouse_cells = set(self.cell_by_warehouse.values())
        self.parents_by_warehouse_cell: dict[int, np.ndarray] = {}
        # With an edge of zero cost the published choice among equally cheap routes can loop (alpha = 1).
        self.has_free_edges = bool(np.any(edge_costs <= 0.0))

    def get_optimal_route_coordinates(self, start: Coordinate, end: Coordinate) -> tuple[np.ndarray, np.ndarray] | None:
        """Eastings and northings of the cell centres along the route; None if the end cannot be reached."""
        route_cells = self.find_route_cells(self.find_nearest_cell(start), self.find_nearest_cell(end))
        if len(route_cells) == 0:
            return None
        return self.grid.eastings[route_cells], self.grid.northings[route_cells]

    def find_route_cells(self, start_cell: int, end_cell: int) -> np.ndarray:
        """Out of a warehouse along its tree; into a warehouse along the reverse of the route out of it."""
        if start_cell in self.warehouse_cells:
            return follow_parents_from_target(self.get_parents(start_cell), start_cell, end_cell)[::-1]
        if end_cell in self.warehouse_cells:
            return follow_parents_from_target(self.get_parents(end_cell), end_cell, start_cell)
        raise ValueError("Routes are only planned from or to a warehouse")

    def get_parents(self, warehouse_cell: int) -> np.ndarray:
        if warehouse_cell not in self.parents_by_warehouse_cell:
            self.parents_by_warehouse_cell[warehouse_cell] = self.build_tree(warehouse_cell)
        return self.parents_by_warehouse_cell[warehouse_cell]

    def build_tree(self, warehouse_cell: int) -> np.ndarray:
        """The published choice among equally cheap routes; the tree of the search itself where that could loop."""
        graph = (len(self.grid.rows), self.grid.edge_starts, self.grid.edge_ends, self.edge_costs)
        if self.has_free_edges:
            return calculate_search_tree(*graph, warehouse_cell)
        return calculate_shortest_path_tree(*graph, warehouse_cell)[0]

    def find_nearest_cell(self, location: Coordinate) -> int:
        known_cell = self.cell_by_warehouse.get(location)
        return known_cell if known_cell is not None else self._query_nearest_cell(location)

    def _query_nearest_cell(self, location: Coordinate) -> int:
        _, cell = self.cell_centres.query((location.easting, location.northing))
        return int(cell)
