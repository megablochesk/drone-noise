from common.coordinate import Coordinate, calculate_distance
from common.configuration import DRONE_SPEED, MODEL_TIME_STEP


class PathPlanner:
    def __init__(self):
        self.speed = DRONE_SPEED
        self.step_time = MODEL_TIME_STEP

    def plan(self, start: Coordinate, end: Coordinate):
        distance = calculate_distance(start, end)
        if distance == 0:
            return [start]

        total_time = distance / self.speed
        number_of_steps = int(total_time // self.step_time)  # floor division for the number of intervals

        if number_of_steps == 0:  # If the distance is too small to form even a single step, just return start and end
            return [start, end]

        return self.calculate_standard_path(start, end, number_of_steps)

    @staticmethod
    def calculate_standard_path(start, end, number_of_steps):
        path = []

        for i in range(number_of_steps + 1):
            t = i / number_of_steps
            n = start.northing + (end.northing - start.northing) * t
            e = start.easting + (end.easting - start.easting) * t
            path.append(Coordinate(n, e))

        if path[-1] != end:
            path.append(end)

        return path
