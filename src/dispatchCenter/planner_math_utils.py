import math
from typing import List

from common.configuration import DRONE_NOISE

SQRT_OF_2 = math.sqrt(2)


def pop_lowest_priority_node(open_nodes: List):
    min_priority = float('inf')
    min_index = 0

    for i in range(len(open_nodes)):
        node = open_nodes[i]
        if node.fn < min_priority:
            min_priority = node.fn
            min_index = i

    return open_nodes.pop(min_index)


def backtrack_path_to_start_node(initial_node_row, initial_node_column, current):
    grid_path = []
    row, col = current.row, current.column
    while row != initial_node_row or col != initial_node_column:
        grid_path.insert(0, [row, col])
        p_node = current.parent
        if p_node is not None:
            current = p_node
            row, col = current.row, current.column
        else:
            break
    grid_path.insert(0, [row, col])
    return grid_path


def diagonal_distance_matrix(row1, col1, row2, col2):
    dx = abs(col1 - col2)
    dy = abs(row1 - row2)
    return SQRT_OF_2 * min(dx, dy) + abs(dx - dy)


def expansion_cost_1(parent_node_row, parent_node_column, child_node_row, child_node_column, avg_matrix,
                     priority_K):
    distance = diagonal_distance_matrix(parent_node_row, parent_node_column, child_node_row, child_node_column)
    expand_cost = distance * DRONE_NOISE + priority_K * avg_matrix[child_node_row][child_node_column]

    return expand_cost


def expansion_cost_2(parent_node_row, parent_node_column, child_node_row, child_node_column, avg_matrix,
                     priority_P):
    distance = diagonal_distance_matrix(parent_node_row, parent_node_column, child_node_row, child_node_column)
    expand_cost = distance * DRONE_NOISE + math.pow(avg_matrix[child_node_row][child_node_column], priority_P)

    return expand_cost


def find_node(row, col, open_nodes: List):
    idx = -1
    for i in range(len(open_nodes)):
        if open_nodes[i].row == row and open_nodes[i].column == col:
            idx = i
            break

    if idx != -1:
        return open_nodes[idx]
    else:
        return None


def heuristic(row1, col1, row2, col2, step_cost):
    distance = calculate_straight_distance_in_matrix(row1, col1, row2, col2)
    return step_cost * distance


def calculate_straight_distance_in_matrix(row1, col1, row2, col2):
    dx = abs(col1 - col2)
    dy = abs(row1 - row2)
    return math.sqrt(dx * dx + dy * dy)
