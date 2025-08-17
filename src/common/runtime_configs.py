from contextlib import contextmanager
from typing import Iterator

from common.simulation_configs import SimulationConfig

runtime_simulation_config: SimulationConfig | None = None

def get_simulation_config() -> SimulationConfig:
    return runtime_simulation_config

def set_simulation_config(config: SimulationConfig) -> None:
    global runtime_simulation_config
    runtime_simulation_config = config

@contextmanager
def use_simulation_config(config: SimulationConfig) -> Iterator[SimulationConfig]:
    previous = get_simulation_config()
    set_simulation_config(config)
    try:
        yield config
    finally:
        set_simulation_config(previous)