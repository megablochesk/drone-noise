from typing import Iterable

from common.enum import NavigationType
from common.simulation_configs import SimulationConfig, DEFAULT_SIMULATION_CONFIGS


def generate_configs_for_datasets(
    datasets: dict[str, str],
    orders: int,
    drones: int,
    base_config: SimulationConfig= DEFAULT_SIMULATION_CONFIGS
):
    return [
        (dataset_name, base_config.with_overrides(
            orders_to_process=orders,
            number_of_drones=drones,
            order_dataset_path=dataset_path
        ))
        for dataset_name, dataset_path in datasets.items()
    ]


def build_configs_for_datasets_and_drones(
    datasets: dict[str, str],
    orders: int,
    drone_cases: Iterable[int],
    base_config: SimulationConfig= DEFAULT_SIMULATION_CONFIGS
):
    return [
        (f"{dataset_name}_d{drones}", base_config.with_overrides(
            orders_to_process=orders,
            number_of_drones=drones,
            order_dataset_path=dataset_path
        ))
        for dataset_name, dataset_path in datasets.items()
        for drones in drone_cases
    ]


def build_configs_for_datasets_drones_and_navigation_types(
    datasets: dict[str, str],
    orders: int,
    drone_cases: Iterable[int],
    navigation_types: Iterable[NavigationType],
    base_config: SimulationConfig = DEFAULT_SIMULATION_CONFIGS,
):
    return [
        (
            f"{dataset_name}_d{number_of_drones}_nav{navigation_type.name}",
            base_config.with_overrides(
                orders_to_process=orders,
                number_of_drones=number_of_drones,
                order_dataset_path=dataset_path,
                navigator_type=navigation_type,
            ),
        )
        for dataset_name, dataset_path in datasets.items()
        for number_of_drones in drone_cases
        for navigation_type in navigation_types
    ]


def build_configs_for_single(
    name: str,
    base_config: SimulationConfig= DEFAULT_SIMULATION_CONFIGS
):
    return [(name, base_config)]
