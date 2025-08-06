from common.configuration import TAKE_INTO_ACCOUNT_LANDING, NUMBER_OF_LANDING_STEPS, DRONE_FLIGHT_ALTITUDE, \
    INTERMEDIATE_ALTITUDES_ASCENDING, INTERMEDIATE_ALTITUDES_DESCENDING


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
