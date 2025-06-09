import numpy as np

from common.configuration import (
    DRONE_SPEED, MODEL_TIME_STEP, TAKE_INTO_ACCOUNT_LANDING, DRONE_FLIGHT_ALTITUDE,
    NUMBER_OF_LANDING_STEPS, INTERMEDIATE_ALTITUDES_ASCENDING, INTERMEDIATE_ALTITUDES_DESCENDING,
    NAVIGATION_BASE_NOISE_PATH, NOISE_BASED_ROUTING, NAVIGATION_GRID_CELL_SIZE
)
from common.coordinate import Coordinate, calculate_distance
from noise.noise_navigation_graph_utils import (
    build_graph, get_optimal_noise_based_route,
    generate_tree_from_graph, get_list_of_nodes_in_graph
)


class PathPlanner:
    def __init__(self):
        self.speed = DRONE_SPEED
        self.step_time = MODEL_TIME_STEP

        if NOISE_BASED_ROUTING:
            self.graph = build_graph(NAVIGATION_BASE_NOISE_PATH)
            self.tree = generate_tree_from_graph(self.graph)
            self.nodes = get_list_of_nodes_in_graph(self.graph)

    def plan(self, start: Coordinate, end: Coordinate):
        distance = calculate_distance(start, end)
        if distance == 0:
            return self.plan_for_zero_distance(start)

        if NOISE_BASED_ROUTING:
            route = self.plan_noise_impact_based_route(start, end)
        else:
            route = self.plan_straight_route(start, end, distance)

        altitudes, route = self.adjust_route_for_landing(start, end, route)

        return route, altitudes

    def plan_noise_impact_based_route(self, start: Coordinate, end: Coordinate):
        path_nodes = get_optimal_noise_based_route(
            self.graph, self.tree, self.nodes,
            start, end
        )

        route = self.sample_route_by_steps(path_nodes)

        route = [Coordinate(northing=self.graph.nodes[n]['pos'][1],
                            easting=self.graph.nodes[n]['pos'][0])
                 for n in route]

        if route[0] != start:
            route.insert(0, start)
        if route[-1] != end:
            route.append(end)

        return route

    def sample_route_by_steps(self, route):
        path_length = NAVIGATION_GRID_CELL_SIZE * (len(route) - 1)
        total_time = path_length / self.speed
        steps = int(total_time // self.step_time)

        if steps > 0 and len(route) > steps + 1:
            idx = np.linspace(0, len(route) - 1, steps + 1, dtype=int)
            route = [route[i] for i in idx]

        return route

    def plan_for_zero_distance(self, start: Coordinate):
        if TAKE_INTO_ACCOUNT_LANDING:
            count = 1 + 2 * NUMBER_OF_LANDING_STEPS
            return [start] * count, self.assign_route_altitudes(1)

        return [start], [DRONE_FLIGHT_ALTITUDE]

    def plan_straight_route(self, start, end, distance):
        total_time = distance / self.speed
        steps = int(total_time // self.step_time)

        if steps == 0:
            return [start, end]

        return self.plan_multiple_steps_straight_route(start, end, steps)

    def adjust_route_for_landing(self, start, end, route):
        if TAKE_INTO_ACCOUNT_LANDING:
            route = self.pad_landing_sequence(route, start, end)

            path_length = len(route) - 2 * NUMBER_OF_LANDING_STEPS
            altitudes = self.assign_route_altitudes(path_length)
        else:
            altitudes = [DRONE_FLIGHT_ALTITUDE] * len(route)

        return altitudes, route

    @staticmethod
    def plan_multiple_steps_straight_route(start, end, steps):
        delta_easting = end.easting - start.easting
        delta_northing = end.northing - start.northing

        route = [
            Coordinate(
                start.northing + delta_northing * (i / steps),
                start.easting + delta_easting * (i / steps)
            ) for i in range(steps + 1)
        ]

        if route[-1] != end:
            route.append(end)

        return route

    @staticmethod
    def pad_landing_sequence(route, start, end):
        return [start] * NUMBER_OF_LANDING_STEPS + route + [end] * NUMBER_OF_LANDING_STEPS

    @staticmethod
    def assign_route_altitudes(path_length):
        main_route_altitudes = [DRONE_FLIGHT_ALTITUDE] * path_length

        return INTERMEDIATE_ALTITUDES_ASCENDING + main_route_altitudes + INTERMEDIATE_ALTITUDES_DESCENDING
