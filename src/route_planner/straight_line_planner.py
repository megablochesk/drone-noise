from common.configuration import DRONE_SPEED, MODEL_TIME_STEP
from common.coordinate import Coordinate, calculate_distance
from route_planner.route_planner import RoutePlanner


class StraightLinePlanner(RoutePlanner):
    def plan_route(self, start, end):
        distance = calculate_distance(start, end)
        if distance == 0:
            return [start]

        total_time = distance / DRONE_SPEED
        steps = int(total_time // MODEL_TIME_STEP)

        if steps == 0:
            return [start, end]

        delta_e = end.easting - start.easting
        delta_n = end.northing - start.northing

        route = [
            Coordinate(
                start.northing + delta_n * (i / steps),
                start.easting + delta_e * (i / steps)
            )
            for i in range(steps + 1)
        ]

        if route[-1] != end:
            route.append(end)

        return route
