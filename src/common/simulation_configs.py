from __future__ import annotations

from dataclasses import dataclass, replace

from common.enum import BaselineNoiseMap, NavigationType, NoiseCalculation
from common.model_configs import ModelConfig, model_config
from common.path_configs import ORDER_BASE_PATH_RANDOM


@dataclass(frozen=True)
class SimulationConfig:
    plot_map: bool = False
    print_model_stats: bool = True

    orders_in_dataset: int = 100_000
    orders_to_process: int = 100_000
    number_of_drones: int = 1250

    drone_landing: bool = False
    land_once_at_customer: bool = False

    navigator_type: NavigationType = NavigationType.STRAIGHT
    noise_calculation: NoiseCalculation = NoiseCalculation.PER_STEP_LEVELS
    baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED

    order_dataset_path: str = ORDER_BASE_PATH_RANDOM

    model: ModelConfig = model_config

    def with_overrides(self, **kwargs) -> "SimulationConfig":
        return replace(self, **kwargs)


DEFAULT_SIMULATION_CONFIGS = SimulationConfig()