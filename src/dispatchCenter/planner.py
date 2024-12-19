import dispatchCenter.planner_math_utils as utils
from common.configuration import COST_FUNCTION, PRIORITIZE_P, PRIORITIZE_K
from common.constants import DRONE_NOISE
from common.coordinate import Coordinate
from matrix.noise import DensityMatrix


class Node:
    def __init__(self, row, column, parent, gn, hn):
        self.row = row                  # row in the matrix
        self.column = column                  # col in the matrix
        self.parent = parent            # parent Node
        self.gn = gn                    # gn: actual cost
        self.hn = hn                    # hn: heuristic cost
        self.fn = self.gn + self.hn     # priority


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
            current_node = utils.pop_lowest_priority_node(open_nodes)

            if self._is_goal_node(current_node, end_cell):
                return self._construct_real_path(current_node, start_cell, end)

            close_nodes.add((current_node.row, current_node.column))
            children = self.expand(current_node)

            for child in children:
                if (child.row, child.column) in close_nodes:
                    continue

                cost = self._calculate_cost(current_node, child, avg_matrix)

                child_gn = current_node.gn + cost
                child_hn = self._calculate_heuristic(child, end_cell)

                existing_node = utils.find_node(child.row, child.column, open_nodes)
                if existing_node and existing_node.gn > child_gn:
                    self._update_node(existing_node, current_node, child_gn, child_hn)
                elif not existing_node:
                    self._add_new_node(open_nodes, child, current_node, child_gn, child_hn)

        return []

    def expand(self, current_node):
        """Expand current node to 8 directions"""
        directions = [(i, j) for i in range(-1, 2) for j in range(-1, 2) if not (i == 0 and j == 0)]
        children = [
            Node(current_node.row + i, current_node.column + j, current_node, 0, 0)
            for i, j in directions
            if self._is_within_bounds(current_node.row + i, current_node.column + j)
        ]
        return children

    @staticmethod
    def _create_node(start_cell, end_cell, gn):
        hn = utils.heuristic(start_cell.row, start_cell.column, end_cell.row, end_cell.column, 0)
        return Node(start_cell.row, start_cell.column, None, gn, hn)


    @staticmethod
    def _is_goal_node(node, end_cell):
        return node.row == end_cell.row and node.column == end_cell.column


    def _construct_real_path(self, current_node, start_cell, end):
        grid_path = utils.backtrack_path_to_start_node(start_cell.row, start_cell.column, current_node)
        return [self.matrix.matrix[row][col].centroid for row, col in grid_path] + [end]

    @staticmethod
    def _calculate_cost(current_node, child, avg_matrix):
        if COST_FUNCTION is 'first':
            return utils.expansion_cost_1(current_node.row, current_node.column, child.row, child.column, avg_matrix, PRIORITIZE_K)
        else:
            return utils.expansion_cost_2(current_node.row, current_node.column, child.row, child.column, avg_matrix, PRIORITIZE_P)

    @staticmethod
    def _calculate_heuristic(child, end_cell):
        return utils.heuristic(child.row, child.column, end_cell.row, end_cell.column, DRONE_NOISE)

    @staticmethod
    def _update_node(existing_node, parent_node, new_gn, new_hn):
        existing_node.parent = parent_node
        existing_node.gn = new_gn
        existing_node.fn = new_gn + new_hn

    @staticmethod
    def _add_new_node(open_nodes, child, parent_node, child_gn, child_hn):
        child.parent = parent_node
        child.gn = child_gn
        child.hn = child_hn
        child.fn = child_gn + child_hn
        open_nodes.append(child)

    def _is_within_bounds(self, row, column):
        return 0 <= row < self.matrix.rows and 0 <= column < self.matrix.cols
