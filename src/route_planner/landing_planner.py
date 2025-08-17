from common.model_configs import model_config
from common.runtime_configs import runtime_simulation_config

TAKE_INTO_ACCOUNT_LANDING = runtime_simulation_config.drone_landing

NUMBER_OF_LANDING_STEPS = model_config.landing_steps

DRONE_FLIGHT_ALTITUDE = model_config.drone.flight_altitude_m

INTERMEDIATE_ALTITUDES_ASCENDING = model_config.intermediate_altitudes_ascending
INTERMEDIATE_ALTITUDES_DESCENDING = model_config.intermediate_altitudes_descending


class AltitudePlanner:
    def add_landing_sequence(self, route, start, end):
        if self.is_zero_distance_route(route) and TAKE_INTO_ACCOUNT_LANDING:
            count = 1 + 2 * NUMBER_OF_LANDING_STEPS
            return [start] * count

        if TAKE_INTO_ACCOUNT_LANDING:
            return self._pad_landing_sequence(route, start, end)

        return route

    def assign_altitudes(self, route):
        if self.is_zero_distance_route(route):
            return [DRONE_FLIGHT_ALTITUDE]

        if TAKE_INTO_ACCOUNT_LANDING:
            path_len = len(route) - 2 * NUMBER_OF_LANDING_STEPS
            return self._landing_altitudes(path_len)

        return [DRONE_FLIGHT_ALTITUDE] * len(route)

    @staticmethod
    def is_zero_distance_route(route):
        return len(route) == 1

    @staticmethod
    def _landing_altitudes(mid_len):
        return (
            INTERMEDIATE_ALTITUDES_ASCENDING +
            [DRONE_FLIGHT_ALTITUDE] * mid_len +
            INTERMEDIATE_ALTITUDES_DESCENDING
        )

    @staticmethod
    def _pad_landing_sequence(route, start, end):
        return [start] * NUMBER_OF_LANDING_STEPS + route + [end] * NUMBER_OF_LANDING_STEPS
