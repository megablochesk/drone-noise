from __future__ import annotations

from dataclasses import dataclass, replace

from common.enum import NavigationType
from common.path_configs import ORDER_BASE_PATH_MIXED_50_50


@dataclass(frozen=True)
class SimulationConfig:
    plot_map: bool = False
    print_model_stats: bool = False

    orders: int = 100
    drones: int = 100

    drone_landing: bool = False

    navigator_type: NavigationType = NavigationType.STRAIGHT

    default_order_base_path: str = ORDER_BASE_PATH_MIXED_50_50

    def with_overrides(self, **kwargs) -> "SimulationConfig":
        return replace(self, **kwargs)


simulation_configs = SimulationConfig()
