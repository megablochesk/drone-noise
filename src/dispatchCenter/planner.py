from common.coordinate import Coordinate, calculate_distance
from common.configuration import DRONE_SPEED, MODEL_TIME_STEP


class PathPlanner:
    def __init__(self):
        self.speed = DRONE_SPEED
        self.step_time = MODEL_TIME_STEP

    def plan(self, start: Coordinate, end: Coordinate):
        dist = calculate_distance(start, end)
        if dist == 0:
            return [start]

        total_time = dist / self.speed
        steps = int(total_time // self.step_time)  # floor division for the number of intervals

        if steps == 0:  # If the distance is too small to form even a single step, just return start and end
            return [start, end]

        path = []
        for i in range(steps + 1):
            t = i / steps
            n = start.northing + (end.northing - start.northing) * t
            e = start.easting + (end.easting - start.easting) * t
            path.append(Coordinate(n, e))

        # Ensure end is added if not already there due to rounding
        if path[-1] != end:
            path.append(end)

        return path
