from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from common.warehouse_configs import Warehouses


@dataclass(frozen=True)
class MapBoundaries:
    left: float = 503_568.18
    right: float = 561_950.07
    top: float = 200_930.56
    bottom: float = 155_850.78

@dataclass(frozen=True)
class DroneConfig:
    noise_at_source_db: float = 90.0
    speed_mps: int = 27
    flight_altitude_m: float = 100.0
    landing_delay_s: int = 60

@dataclass(frozen=True)
class TimeConfig:
    start_s: int = 36_000     # 10:00
    end_s: int = 72_000       # 20:00
    step_s: int = 30

    @property
    def hours(self) -> int:
        return int((self.end_s - self.start_s) / 3600)

@dataclass(frozen=True)
class GridConfig:
    noise_cell_m: int = 500
    nav_cell_m: int = 100

@dataclass(frozen=True)
class ModelConfig:
    grid: GridConfig = field(default_factory=GridConfig)
    time: TimeConfig = field(default_factory=TimeConfig)
    drone: DroneConfig = field(default_factory=DroneConfig)
    map_boundaries: MapBoundaries = field(default_factory=MapBoundaries)
    warehouses: Warehouses = field(default_factory=Warehouses.london_default)

    @property
    def landing_steps(self) -> int:
        return math.ceil(self.drone.landing_delay_s / self.time.step_s)

    @property
    def intermediate_altitudes_ascending(self) -> List[float]:
        n = self.landing_steps
        h = self.drone.flight_altitude_m
        return [h * (i / n) for i in range(0, n)]

    @property
    def intermediate_altitudes_descending(self) -> List[float]:
        return list(reversed(self.intermediate_altitudes_ascending))


model_config = ModelConfig()
