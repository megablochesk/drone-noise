from common.coordinate import Coordinate, calculate_distance
from common.runtime_configs import get_simulation_config
from route_planner.route_planner import RoutePlanner


class StraightLinePlanner(RoutePlanner):
    def __init__(self):
        model = get_simulation_config().model
        self.time_step_s = model.time.step_s
        self.speed_mps = model.drone.speed_mps

    def plan_route(self, start, end):
        distance = calculate_distance(start, end)
        if distance == 0:
            return [start]

        total_time = distance / self.speed_mps
        steps = int(total_time // self.time_step_s)

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
