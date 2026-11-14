"""Routes on the array navigation grid; a route's start becomes a depot if it is not one already.

The shortest-path tree of a depot is built on first use (a fraction of a second), so nothing is cached on
disk and a tree can never belong to another noise map or cost.
"""
import numpy as np
from scipy.spatial import cKDTree

from common.coordinate import Coordinate
from noise.navigator.navigation_grid import NavigationGrid
from noise.navigator.shortest_path_tree import calculate_search_tree, calculate_shortest_path_tree
from noise.navigator.warehouse_dijkstra_router import follow_parents_from_target


class GridRouteNavigator:
    def __init__(self, grid: NavigationGrid, edge_costs: np.ndarray, depot_locations: list[Coordinate]):
        self.grid = grid
        self.edge_costs = edge_costs
        self.cell_centres = cKDTree(np.column_stack([grid.eastings, grid.northings]))
        self.depot_cells = {self.find_nearest_cell(location) for location in depot_locations}
        self.parents_by_depot_cell: dict[int, np.ndarray] = {}
        # With an edge of zero cost the published choice among equally cheap routes can loop (alpha = 1).
        self.has_free_edges = bool(np.any(edge_costs <= 0.0))

    def get_optimal_route_coordinates(self, start: Coordinate, end: Coordinate) -> tuple[np.ndarray, np.ndarray] | None:
        """Eastings and northings of the cell centres along the route.

        None if the end cannot be reached, or if both ends lie in one cell and the grid has no route to offer.
        """
        start_cell, end_cell = self.find_nearest_cell(start), self.find_nearest_cell(end)
        if start_cell == end_cell:
            return None

        route_cells = self.find_route_cells(start_cell, end_cell)
        if len(route_cells) == 0:
            return None
        return self.grid.eastings[route_cells], self.grid.northings[route_cells]

    def find_route_cells(self, start_cell: int, end_cell: int) -> np.ndarray:
        """Out of a depot along its tree; into a depot along the reverse of the route out of it.

        A start that is neither becomes a depot, so depot layouts that were not announced work too: a drone's
        first leg leaves its depot.
        """
        if start_cell not in self.depot_cells and end_cell in self.depot_cells:
            return follow_parents_from_target(self.get_parents(end_cell), end_cell, start_cell)
        self.depot_cells.add(start_cell)
        return follow_parents_from_target(self.get_parents(start_cell), start_cell, end_cell)[::-1]

    def get_parents(self, depot_cell: int) -> np.ndarray:
        if depot_cell not in self.parents_by_depot_cell:
            self.parents_by_depot_cell[depot_cell] = self.build_tree(depot_cell)
        return self.parents_by_depot_cell[depot_cell]

    def build_tree(self, depot_cell: int) -> np.ndarray:
        """The published choice among equally cheap routes; the tree of the search itself where that could loop."""
        graph = (len(self.grid.rows), self.grid.edge_starts, self.grid.edge_ends, self.edge_costs)
        if self.has_free_edges:
            return calculate_search_tree(*graph, depot_cell)
        return calculate_shortest_path_tree(*graph, depot_cell)[0]

    def find_nearest_cell(self, location: Coordinate) -> int:
        _, cell = self.cell_centres.query((location.easting, location.northing))
        return int(cell)
