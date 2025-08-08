from __future__ import annotations

from dataclasses import dataclass, replace, field
from typing import Tuple

from common.enum import NavigationType


@dataclass(frozen=True)
class Switches:
    print_drone_stats: bool = False
    print_model_stats: bool = False
    plot_map: bool = False
    plot_stats: bool = False
    take_landing_into_account: bool = False

@dataclass(frozen=True)
class SimulationConfig:
    orders: int = 100
    drones: int = 100
    navigator_type: NavigationType = NavigationType.STRAIGHT
    order_dataset_types: Tuple[str, ...] = ("furthest", "random", "closest")

@dataclass(frozen=True)
class SimulatorConfig:
    switches: Switches = field(default_factory=Switches)
    sim: SimulatorConfig = field(default_factory=SimulationConfig)
    default_order_base_path: str = "recourses/data/order/mixed_stocking_100000_random50_closest50.csv"

    def with_overrides(self, **kwargs) -> "SimulatorConfig":
        return replace(self, **kwargs)


simulation_configs = SimulatorConfig()
