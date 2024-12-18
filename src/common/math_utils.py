import math
import random
from typing import List

import numpy as np
from common.constants import M_2_LATITUDE, M_2_LONGITUDE, DRONE_NOISE, DRONE_ALTITUTE
from common.coordinate import Coordinate

DRONE_ALTITUDE_SQUARED = DRONE_ALTITUTE * DRONE_ALTITUTE

NOISE_AT_SOURCE = DRONE_NOISE

from matplotlib import pyplot as plt
import seaborn as sns


def offset_coordinate(coordinate: Coordinate, la_range, lo_range):
    """
    Add offset to a coordinate.
    
    :param coordinate:
    :param la_range: latitude offset range (0, la_range)
    :param lo_range: longitude offset range (0, lo_range)
    :return: An offset coordinate
    """
    coordinate.latitude += random.uniform(-la_range, la_range)
    coordinate.longitude += random.uniform(-lo_range, lo_range)


def calculate_distance(c1: Coordinate, c2: Coordinate):
    """
    Calculate distances between two coordinates

    :param c1: current coordinate
    :param c2: another coordinate
    :return: straight-line distance from c1 to c2 in meters
    """
    la_distance, lo_distance = c2 - c1

    la_distance_m = la_distance / M_2_LATITUDE
    lo_distance_m = lo_distance / M_2_LONGITUDE

    return math.sqrt(la_distance_m * la_distance_m +
                     lo_distance_m * lo_distance_m)


def straight_distance_matrix(row1, col1, row2, col2):
    """Calculate the straight distance in matrix"""
    dx = abs(col1 - col2)
    dy = abs(row1 - row2)
    return math.sqrt(dx * dx + dy * dy)


SQRT_OF_2 = math.sqrt(2)


def diagonal_distance_matrix(row1, col1, row2, col2):
    """Calculate the diagonal distance in matrix"""
    dx = abs(col1 - col2)
    dy = abs(row1 - row2)
    return SQRT_OF_2 * min(dx, dy) + abs(dx - dy)


def difference(list1, list2):
    """Return a list of elements that in list1 but not in list2"""
    return list(set(list1).difference(set(list2)))


def union(list1, list2):
    """Return a list of elements that in list1 or list2"""
    return list(set(list1).union(set(list2)))


def intersection(list1, list2):
    """Return a list of elements that in both list1 and list2"""
    return list(set(list1).intersection(set(list2)))


def find_nearest_free_drone(order, free_drones):
    """
    Find the nearest drone among free drones to a given order

    :param order: the target order
    :param free_drones: all free drones that can chosen from
    :return the nearest drone
    """
    return free_drones[nearest_neighbor_idx(
        neighbors=[x.location for x in free_drones],
        target=order.start_location)]


def nearest_neighbor(neighbors: List[Coordinate], target: Coordinate) -> Coordinate:
    """
    Find the nearest neighbor to the target location.

    :param neighbors: All candidate neighbors around the target
    :param target:  The target location
    :return: The location of the nearest neighbor
    """
    return neighbors[nearest_neighbor_idx(neighbors, target)]


def nearest_neighbor_idx(neighbors: List[Coordinate], target: Coordinate) -> int:
    """
    Find the index of the nearest neighbor to the target location.

    :param neighbors: All candidate neighbors around the target
    :param target:  The target location
    :return: The index of the nearest neighbor
    """
    distances = []
    for neighbor in neighbors:
        line_distance = calculate_distance(neighbor, target)

        distances.append(line_distance)

    return np.argmin(distances)


def calculate_noise_m(x_dist, y_dist):
    """
    Calculate the matrix at distance.
    
    :param x_dist: x-axis distance to center x in meters
    :param y_dist: y-axis distance to center y
    :param central_noise: the center matrix level
    :return: the matrix at (center_x + x_dist, center_y + y_dist)
    """
    return NOISE_AT_SOURCE - math.fabs(10 * math.log10(x_dist * x_dist + y_dist * y_dist))


BASELINE_NOISE_AT_ALTITUDE = DRONE_NOISE - 20 * math.log10(DRONE_ALTITUTE)
# DISTANCE_OF_ZERO_NOISE = math.sqrt(10 ** (0.1 * DRONE_NOISE) - DRONE_ALTITUDE_SQUARED)


def calculate_noise_at_distance(distance):
    if distance <= 1:
        return BASELINE_NOISE_AT_ALTITUDE

    total_distance_squared = distance * distance + DRONE_ALTITUDE_SQUARED

    return NOISE_AT_SOURCE - 10 * math.log10(total_distance_squared)


def calculate_mixed_noise_level(sound_sources):
    if len(sound_sources) == 0:
        return 0

    linear_sum = sum(math.exp(source * math.log(10) / 10) for source in sound_sources)

    return 10 * math.log10(linear_sum)


def heuristic(row1, col1, row2, col2, step_cost):
    """
    Heuristic function calculates heuristic cost from (row1, col1) to (row2, col2) with a given step cost.
    
    :param row1: row index of node1
    :param col1: column index of node1
    :param row2: row index of node2
    :param col2: column index of node2
    :param step_cost: movement cost
    :return: heuristic cost
    """
    distance = straight_distance_matrix(row1, col1, row2, col2)
    return step_cost * distance


def cost_1(row1, col1, row2, col2, avg_matrix, priority_K):
    """
    Calculate the expansion cost from parent node to child node.
    
    :param row1: parent node row
    :param col1: parent node col
    :param row2: child node row
    :param col2: child node col
    :param avg_matrix: average-matrix matrix
    :param priority_K: priority parameter, K
    :return: cost from parent to child
    """
    distance = diagonal_distance_matrix(row1, col1, row2, col2)
    expand_cost = distance * DRONE_NOISE + priority_K * avg_matrix[row2][col2]
    return expand_cost


def cost_2(row1, col1, row2, col2, avg_matrix, priority_P):
    """
    Calculate the expansion cost from parent node to child node.

    :param row1: parent node row
    :param col1: parent node col
    :param row2: child node row
    :param col2: child node col
    :param avg_matrix: average-matrix matrix
    :param priority_P: priority parameter, P
    :return: cost from parent to child
    """
    distance = diagonal_distance_matrix(row1, col1, row2, col2)
    expand_cost = distance * DRONE_NOISE + math.pow(avg_matrix[row2][col2], priority_P)
    return expand_cost


def backtrack(row0, col0, current):
    """
    Find the path from the current node to the start node.
    
    :param row0: row index of the initial node
    :param col0: column index of the initial node
    :param current: current node
    :return: a path, i.e., a list of nodes
    """
    grid_path = []
    row, col = current.row, current.col
    while row != row0 or col != col0:
        grid_path.insert(0, [row, col])
        p_node = current.parent
        if p_node is not None:
            current = p_node
            row, col = current.row, current.col
        else:
            break
    grid_path.insert(0, [row, col])
    return grid_path


def pop_lowest_priority(open_nodes: List):
    """
    Pop the node with the lowest priority.
    
    :param open_nodes: a list of nodes
    :return: A node with the lowest priority in the list
    """
    min_priority = float('inf')
    min_index = 0
    for i in range(len(open_nodes)):
        node = open_nodes[i]
        if node.fn < min_priority:
            min_priority = node.fn
            min_index = i
    return open_nodes.pop(min_index)


def find_node(row, col, open_nodes: List):
    """
    Find a node in a 2d array.
    
    :param row: row index
    :param col: column index
    :param open_nodes: 2d array
    :return: open_nodes[row][col]
    """
    idx = -1
    for i in range(len(open_nodes)):
        if open_nodes[i].row == row and open_nodes[i].col == col:
            idx = i
            break
    if idx != -1:
        return open_nodes[idx]
    else:
        return None


def plot_matrix(X, Y, Z, title, path, color_min, color_max):
    """
    Plot a density matrix.
    
    :param X: X-axis in pcolormesh
    :param Y: Y-axis in pcolormesh
    :param Z: Z-axis (data) in pcolormesh
    :param title: figure title
    :param path: figure saving path
    :param color_min: min value of color bar
    :param color_max: max value of color bar
    :return:
    """
    fig, ax = plt.subplots()
    plt.pcolormesh(X, Y, Z)
    plt.colorbar()
    plt.clim(vmin=color_min, vmax=color_max)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.title(title)
    plt.savefig(path, bbox_inches='tight')
    plt.close()


def plot_histogram(data, title, path, y_bottom, y_top, x_bottom=0, x_top=None):
    """
    Plot a histogram.
    
    :param data: histogram data (from a pandas dataframe)
    :param title: figure title
    :param path: figure saving path
    :param y_bottom: bottom bar value
    :param y_top: top bar value
    :return:
    """
    fig, ax = plt.subplots()
    plt.ylim(y_bottom, y_top)
    if x_top != None:
        plt.xlim(x_bottom, x_top)
    plt.title(title)
    sns.histplot(data=data, kde=True)
    plt.savefig(path, bbox_inches='tight')
    plt.close()
