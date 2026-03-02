from __future__ import annotations

from dataclasses import dataclass, replace

from common.enum import NavigationType
from common.path_configs import ORDER_BASE_PATH_RANDOM


@dataclass(frozen=True)
class SimulationConfig:
    plot_map: bool = False
    print_model_stats: bool = True

    orders_in_dataset: int = 100_000
    orders_to_process: int = 100_000
    number_of_drones: int = 1250

    drone_landing: bool = True

    navigator_type: NavigationType = NavigationType.STRAIGHT

    order_dataset_path: str = ORDER_BASE_PATH_RANDOM

    def with_overrides(self, **kwargs) -> "SimulationConfig":
        return replace(self, **kwargs)


DEFAULT_SIMULATION_CONFIGS = SimulationConfig()