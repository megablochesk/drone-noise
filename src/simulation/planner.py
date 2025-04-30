from common.coordinate import Coordinate, calculate_distance
from common.configuration import (
    DRONE_SPEED, MODEL_TIME_STEP, TAKE_INTO_ACCOUNT_LANDING, DRONE_FLIGHT_ALTITUDE,
    NUMBER_OF_LANDING_STEPS, INTERMEDIATE_ALTITUDES_ASCENDING, INTERMEDIATE_ALTITUDES_DESCENDING
)


class PathPlanner:
    def __init__(self):
        self.speed = DRONE_SPEED
        self.step_time = MODEL_TIME_STEP

    def plan(self, start: Coordinate, end: Coordinate):
        distance = calculate_distance(start, end)
        if distance == 0:
            return self.plan_for_zero_distance(start)

        total_time = distance / self.speed
        steps = int(total_time // self.step_time)
        route = self.plan_standard_route(start, end, steps)

        if TAKE_INTO_ACCOUNT_LANDING:
            route = self.pad_landing_sequence(route, start, end)
            altitudes = self.assign_route_altitudes(len(route))
        else:
            altitudes = [DRONE_FLIGHT_ALTITUDE] * len(route)

        return route, altitudes

    def plan_for_zero_distance(self, start: Coordinate):
        if TAKE_INTO_ACCOUNT_LANDING:
            count = 1 + 2 * NUMBER_OF_LANDING_STEPS
            return [start] * count, self.assign_route_altitudes(1)

        return [start], [DRONE_FLIGHT_ALTITUDE]

    def plan_standard_route(self, start: Coordinate, end: Coordinate, steps: int):
        if steps == 0:
            base = [start, end] if calculate_distance(start, end) != 0 else [start]
        else:
            base = self.interpolate_coordinates(start, end, steps)
            if base[-1] != end:
                base.append(end)
        return base

    @staticmethod
    def interpolate_coordinates(start, end, steps):
        delta_easting = end.easting - start.easting
        delta_northing = end.northing - start.northing

        return [
            Coordinate(
                start.northing + delta_northing * (i / steps),
                start.easting + delta_easting * (i / steps)
            ) for i in range(steps + 1)
        ]

    @staticmethod
    def pad_landing_sequence(route, start, end):
        return [start] * NUMBER_OF_LANDING_STEPS + route + [end] * NUMBER_OF_LANDING_STEPS

    @staticmethod
    def assign_route_altitudes(path_length):
        main_route_altitudes = [DRONE_FLIGHT_ALTITUDE] * path_length

        return INTERMEDIATE_ALTITUDES_ASCENDING + main_route_altitudes + INTERMEDIATE_ALTITUDES_DESCENDING
