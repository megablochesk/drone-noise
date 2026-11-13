from dataclasses import replace
from pathlib import Path

import pandas as pd

from common.coordinate import Coordinate
from common.model_configs import ModelConfig, model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from simulation.simulator import Simulator

WAREHOUSE = Coordinate(northing=182_049.78, easting=538_402.03)


def destination_east_of_warehouse(distance_m: float) -> Coordinate:
    return Coordinate(northing=WAREHOUSE.northing, easting=WAREHOUSE.easting + distance_m)


def write_order_dataset(path: Path, destinations: list[Coordinate], warehouse: Coordinate = WAREHOUSE) -> str:
    orders = pd.DataFrame({
        "Order ID": range(1, len(destinations) + 1),
        "Start Northing": warehouse.northing,
        "Start Easting": warehouse.easting,
        "End Northing": [destination.northing for destination in destinations],
        "End Easting": [destination.easting for destination in destinations],
    })
    orders.to_csv(path, index=False)
    return str(path)


def model_with_duration(duration_s: int, base_model: ModelConfig = model_config) -> ModelConfig:
    return replace(base_model, time=replace(base_model.time, start_s=0, end_s=duration_s))


def run_small_simulation(config: SimulationConfig, warehouse_locations: list[Coordinate] | None = None) -> Simulator:
    with use_simulation_config(config):
        simulator = Simulator(warehouse_locations=warehouse_locations or [WAREHOUSE])
        simulator.run()
    return simulator
