from common.runtime_configs import get_simulation_config

GROUND_ALTITUDE_M = 0.0


class LandingPlanner:
    def __init__(self):
        simulation_config = get_simulation_config()
        model = simulation_config.model

        self.use_drone_landing = simulation_config.drone_landing
        self.lands_once_at_customer = self.use_drone_landing and simulation_config.land_once_at_customer
        self.number_of_landing_steps = model.landing_steps
        self.flight_altitude_m = model.drone.flight_altitude_m
        self.intermediate_altitudes_ascending = model.intermediate_altitudes_ascending
        self.intermediate_altitudes_descending = model.intermediate_altitudes_descending

    def add_landing_sequence(self, route, start, end):
        if self.is_zero_distance_route(route) and self.lands_once_at_customer:
            return [start]

        if self.is_zero_distance_route(route) and self.use_drone_landing:
            count = 1 + 2 * self.number_of_landing_steps
            return [start] * count

        if self.use_drone_landing:
            return self._pad_landing_sequence(route, start, end)

        return route

    def assign_altitudes(self, route):
        if self.is_zero_distance_route(route) and self.lands_once_at_customer:
            return [GROUND_ALTITUDE_M]

        if self.is_zero_distance_route(route):
            return [self.flight_altitude_m]

        if self.use_drone_landing:
            path_len = len(route) - 2 * self.number_of_landing_steps
            return self._landing_altitudes(path_len)

        return [self.flight_altitude_m] * len(route)

    @staticmethod
    def is_zero_distance_route(route):
        return len(route) == 1

    def _landing_altitudes(self, mid_len):
        return (
            self.intermediate_altitudes_ascending +
            [self.flight_altitude_m] * mid_len +
            self.intermediate_altitudes_descending
        )

    def _pad_landing_sequence(self, route, start, end):
        return [start] * self.number_of_landing_steps + route + [end] * self.number_of_landing_steps
