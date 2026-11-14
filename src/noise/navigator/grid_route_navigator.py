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
        self.search_parents_by_warehouse_cell: dict[int, np.ndarray] = {}

    def get_optimal_route_coordinates(self, start: Coordinate, end: Coordinate) -> tuple[np.ndarray, np.ndarray] | None:
        """Eastings and northings of the cell centres along the route; None if the end cannot be reached."""
        route_cells = self.find_route_cells(self.find_nearest_cell(start), self.find_nearest_cell(end))
        if len(route_cells) == 0:
            return None
        return self.grid.eastings[route_cells], self.grid.northings[route_cells]

    def find_route_cells(self, start_cell: int, end_cell: int) -> np.ndarray:
        """Out of a warehouse along its tree; into a warehouse along the reverse of the route out of it."""
        if start_cell in self.warehouse_cells:
            return self.follow_tree(start_cell, end_cell)[::-1]
        if end_cell in self.warehouse_cells:
            return self.follow_tree(end_cell, start_cell)
        raise ValueError("Routes are only planned from or to a warehouse")

    def follow_tree(self, warehouse_cell: int, other_cell: int) -> np.ndarray:
        """Cells from the other cell back to the warehouse, by the published choice among equally cheap routes.

        Where edges of zero cost make that choice loop, the tree of the search itself is followed instead.
        """
        route_cells = follow_parents_from_target(self.get_parents(warehouse_cell), warehouse_cell, other_cell)
        if len(route_cells) > 0:
            return route_cells
        return follow_parents_from_target(self.get_search_parents(warehouse_cell), warehouse_cell, other_cell)

    def get_parents(self, warehouse_cell: int) -> np.ndarray:
        if warehouse_cell not in self.parents_by_warehouse_cell:
            parents, _ = calculate_shortest_path_tree(*self._describe_graph(), warehouse_cell)
            self.parents_by_warehouse_cell[warehouse_cell] = parents
        return self.parents_by_warehouse_cell[warehouse_cell]

    def get_search_parents(self, warehouse_cell: int) -> np.ndarray:
        if warehouse_cell not in self.search_parents_by_warehouse_cell:
            self.search_parents_by_warehouse_cell[warehouse_cell] = calculate_search_tree(*self._describe_graph(), warehouse_cell)
        return self.search_parents_by_warehouse_cell[warehouse_cell]

    def _describe_graph(self) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
        return len(self.grid.rows), self.grid.edge_starts, self.grid.edge_ends, self.edge_costs

    def find_nearest_cell(self, location: Coordinate) -> int:
        known_cell = self.cell_by_warehouse.get(location)
        return known_cell if known_cell is not None else self._query_nearest_cell(location)

    def _query_nearest_cell(self, location: Coordinate) -> int:
        _, cell = self.cell_centres.query((location.easting, location.northing))
        return int(cell)
