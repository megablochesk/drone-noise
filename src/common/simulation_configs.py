from __future__ import annotations

from dataclasses import dataclass, replace

from common.enum import NavigationType
from common.path_configs import ORDER_BASE_PATH_MIXED_50_50


@dataclass(frozen=True)
class SimulationConfig:
    plot_map: bool = False
    print_model_stats: bool = True

    orders_in_dataset: int = 100_000
    orders_to_process: int = 100
    number_of_drones: int = 100

    drone_landing: bool = False

    navigator_type: NavigationType = NavigationType.STRAIGHT

    order_dataset_path: str = ORDER_BASE_PATH_MIXED_50_50

    def with_overrides(self, **kwargs) -> "SimulationConfig":
        return replace(self, **kwargs)


DEFAULT_SIMULATION_CONFIGS = SimulationConfig()