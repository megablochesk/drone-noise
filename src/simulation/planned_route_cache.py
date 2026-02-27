from __future__ import annotations

from dataclasses import dataclass

from common.coordinate import Coordinate


@dataclass(frozen=True)
class PlannedRouteKey:
    start_northing: float
    start_easting: float
    end_northing: float
    end_easting: float


@dataclass(frozen=True)
class StoredPlannedRoute:
    route_coordinates: tuple[tuple[float, float], ...]
    altitudes: tuple[float, ...]


@dataclass(frozen=True)
class PlannedRouteCacheStats:
    entry_count: int
    hit_count: int
    miss_count: int

    @property
    def request_count(self) -> int:
        return self.hit_count + self.miss_count

    @property
    def hit_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.hit_count / self.request_count


class PlannedRouteCache:
    def __init__(self):
        self._cached_routes: dict[PlannedRouteKey, StoredPlannedRoute] = {}
        self._hit_count = 0
        self._miss_count = 0

    @property
    def entry_count(self) -> int:
        return len(self._cached_routes)

    @property
    def hit_count(self) -> int:
        return self._hit_count

    @property
    def miss_count(self) -> int:
        return self._miss_count

    def get_stats(self) -> PlannedRouteCacheStats:
        return PlannedRouteCacheStats(
            entry_count=self.entry_count,
            hit_count=self.hit_count,
            miss_count=self.miss_count,
        )

    def get(self, start: Coordinate, end: Coordinate) -> tuple[list[Coordinate], list[float]] | None:
        cache_key = self._build_cache_key(start, end)
        stored_planned_route = self._cached_routes.get(cache_key)

        if stored_planned_route is None:
            self._miss_count += 1
            return None

        self._hit_count += 1
        return self._restore_planned_route(stored_planned_route)

    def store(self, start: Coordinate, end: Coordinate, route: list[Coordinate], altitudes: list[float]):
        cache_key = self._build_cache_key(start, end)
        self._cached_routes[cache_key] = self._freeze_planned_route(route, altitudes)

    def clear(self):
        self._cached_routes.clear()
        self._hit_count = 0
        self._miss_count = 0

    @staticmethod
    def _build_cache_key(start: Coordinate, end: Coordinate) -> PlannedRouteKey:
        return PlannedRouteKey(
            start_northing=start.northing,
            start_easting=start.easting,
            end_northing=end.northing,
            end_easting=end.easting,
        )

    @staticmethod
    def _freeze_planned_route(route: list[Coordinate], altitudes: list[float]) -> StoredPlannedRoute:
        frozen_route_coordinates = tuple(
            (coordinate.northing, coordinate.easting)
            for coordinate in route
        )
        frozen_altitudes = tuple(altitudes)
        return StoredPlannedRoute(
            route_coordinates=frozen_route_coordinates,
            altitudes=frozen_altitudes,
        )

    @staticmethod
    def _restore_planned_route(stored_planned_route: StoredPlannedRoute) -> tuple[list[Coordinate], list[float]]:
        restored_route = [
            Coordinate(northing=northing, easting=easting)
            for northing, easting in stored_planned_route.route_coordinates
        ]
        restored_altitudes = list(stored_planned_route.altitudes)
        return restored_route, restored_altitudes