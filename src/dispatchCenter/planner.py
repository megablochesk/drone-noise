from matrix.noise import DensityMatrix
from cityMap.citymap import Coordinate
from common.decorators import auto_str
from common.math_utils import heuristic, cost_1, cost_2, pop_lowest_priority, find_node, backtrack
from common.constants import DRONE_NOISE
from common.configuration import COST_FUNCTION, PRIORITIZE_P, PRIORITIZE_K


@auto_str
class Node:
    def __init__(self, row, col, parent, gn, hn):
        self.row = row                  # row in the matrix
        self.col = col                  # col in the matrix
        self.parent = parent            # parent Node
        self.gn = gn                    # gn: actual cost
        self.hn = hn                    # hn: heuristic cost
        self.fn = self.gn + self.hn     # priority


@auto_str
class PathPlanner:
    def __init__(self, matrix: DensityMatrix):
        self.matrix = matrix
        
    def plan(self, start: Coordinate, end: Coordinate, time_count):
        """A-star search"""
        start_cell = self.matrix.get_cell(start)
        end_cell = self.matrix.get_cell(end)
        avg_matrix = self.matrix.get_average_matrix(time_count)
        
        open_nodes = list()  # [Node, Node, ...]
        close_nodes = set()  # {[row, col], ...}

        start_node = self._create_node(start_cell, end_cell, gn=0)
        open_nodes.append(start_node)

        while open_nodes:
            current_node = self._pop_lowest_priority_node(open_nodes)

            if self._is_goal_node(current_node, end_cell):
                return self._construct_real_path(current_node, start_cell, end)

            close_nodes.add((current_node.row, current_node.col))
            children = self.expand(current_node)

            for child in children:
                if (child.row, child.col) in close_nodes:
                    continue

                # TODO: consider population density
                cost = self._calculate_cost(current_node, child, avg_matrix)

                child_gn = current_node.gn + cost
                child_hn = self._calculate_heuristic(child, end_cell)

                existing_node = find_node(child.row, child.col, open_nodes)
                if existing_node and existing_node.gn > child_gn:
                        self._update_node(existing_node, current_node, child_gn, child_hn)
                elif not existing_node:
                    self._add_new_node(open_nodes, child, current_node, child_gn, child_hn)

        return []
    
    def expand(self, current_node):
        """Expand current node to 8 directions"""
        directions = [(i, j) for i in range(-1, 2) for j in range(-1, 2) if not (i == 0 and j == 0)]
        children = [
            Node(current_node.row + i, current_node.col + j, current_node, 0, 0)
            for i, j in directions
            if self._is_within_bounds(current_node.row + i, current_node.col + j)
        ]
        return children

    def _create_node(self, start_cell, end_cell, gn):
        hn = heuristic(start_cell.row, start_cell.col, end_cell.row, end_cell.col, 0)
        return Node(start_cell.row, start_cell.col, None, gn, hn)

    def _pop_lowest_priority_node(self, open_nodes):
        return pop_lowest_priority(open_nodes)

    def _is_goal_node(self, node, end_cell):
        return node.row == end_cell.row and node.col == end_cell.col

    def _construct_real_path(self, current_node, start_cell, end):
        grid_path = backtrack(start_cell.row, start_cell.col, current_node)
        return [self.matrix.matrix[row][col].centroid for row, col in grid_path] + [end]

    def _calculate_cost(self, current_node, child, avg_matrix):
        if COST_FUNCTION is 'first':
            return cost_1(current_node.row, current_node.col, child.row, child.col, avg_matrix, PRIORITIZE_K)
        else:
            return cost_2(current_node.row, current_node.col, child.row, child.col, avg_matrix, PRIORITIZE_P)

    def _calculate_heuristic(self, child, end_cell):
        return heuristic(child.row, child.col, end_cell.row, end_cell.col, DRONE_NOISE)

    def _update_node(self, existing_node, parent_node, new_gn, new_hn):
        existing_node.parent = parent_node
        existing_node.gn = new_gn
        existing_node.fn = new_gn + new_hn

    def _add_new_node(self, open_nodes, child, parent_node, child_gn, child_hn):
        child.parent = parent_node
        child.gn = child_gn
        child.hn = child_hn
        child.fn = child_gn + child_hn
        open_nodes.append(child)

    def _is_within_bounds(self, row, column):
        return 0 <= row < self.matrix.rows and 0 <= column < self.matrix.cols
