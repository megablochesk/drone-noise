from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple, Dict, List

from common.coordinate import Coordinate


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
class PathsConfiguration:
    order_folder: str = "recourses/data/order/"
    base_noise_folder: str = "recourses/data/base_noise/"
    noise_graph_navigation_folder: str = "recourses/data/noise_graph_navigation/"
    msoa_population_path: str = "recourses/data/MSOA_population_dataset_filtered.geojson"
    london_boundaries_path: str = "recourses/data/greater-london-boundaries.geo.json"
    experiment_results_path: str = "recourses/experiment_results/"
    map_file_path: str = "drone_delivery_simulation.html"

    matplotlib_backend: str = "Qt5Agg"

    def single_type_order_dataset(self, order_dataset_type: str, stocking_number: int) -> str:
        return f"{self.order_folder}drone_delivery_orders_{stocking_number}_{order_dataset_type}.csv"

    def mixed_order_dataset(self, random_ratio: int, closest_ratio: int, stocking_number: int) -> str:
        return f"{self.order_folder}mixed_stocking_{stocking_number}_random{random_ratio}_closest{closest_ratio}.csv"

    def base_noise_path(self, cell_size_meters: int) -> str:
        return f"{self.base_noise_folder}base_noise_london_map_{cell_size_meters}.geojson"

    def navigation_graph_path(self, navigation_cell_size_meters: int) -> str:
        return f"{self.noise_graph_navigation_folder}navigation_graph_{navigation_cell_size_meters}"

    def warehouse_paths_cache(self) -> str:
        return f"{self.noise_graph_navigation_folder}warehouse_paths_cache.pkl"

    def cell_population_path(self, noise_cell_size_meters: int) -> str:
        return f"recourses/data/cell_population_{noise_cell_size_meters}.pkl"

@dataclass(frozen=True)
class Warehouses:
    bng_coordinates: Dict[str, Coordinate]
    latlon_coordinates: Dict[str, Tuple[float, float]]

    @staticmethod
    def london_default() -> "Warehouses":
        return Warehouses(
            bng_coordinates={
                "DBR1": Coordinate(180193.93, 550041.28),
                "DBR2": Coordinate(167766.96, 546937.62),
                "DCR1": Coordinate(164142.21, 530990.34),
                "DCR2": Coordinate(165727.01, 530631.31),
                "DCR3": Coordinate(165418.73, 530850.99),
                "DHA1": Coordinate(185648.81, 520386.09),
                "DHA2": Coordinate(185658.7, 520531.03),
                "DIG1": Coordinate(196826.63, 536790.04),
                "DRM4": Coordinate(182781.49, 546601.21),
                "DXE1": Coordinate(182049.78, 538402.03),
                "DXN1": Coordinate(179513.55, 507871.84),
                "EHU2": Coordinate(182097.0, 538419.42),
                "MLN2": Coordinate(182084.59, 533269.42),
                "MLN3": Coordinate(179908.41, 533781.95),
            },
            latlon_coordinates={
                "DBR1": (51.500773, 0.160277),
                "DBR2": (51.389926, 0.110440),
                "DCR1": (51.361253, -0.119953),
                "DCR2": (51.375578, -0.124525),
                "DCR3": (51.372757, -0.121484),
                "DHA1": (51.556886, -0.264871),
                "DHA2": (51.556944, -0.262778),
                "DIG1": (51.653594, -0.024036),
                "DRM4": (51.524925, 0.111827),
                "DXE1": (51.520417, -0.006570),
                "DXN1": (51.504271, -0.447186),
                "EHU2": (51.520837, -0.006301),
                "MLN2": (51.521963, -0.080489),
                "MLN3": (51.502286, -0.073931),
            },
        )

@dataclass(frozen=True)
class ModelConfig:
    grid: GridConfig = field(default_factory=GridConfig)
    time: TimeConfig = field(default_factory=TimeConfig)
    drone: DroneConfig = field(default_factory=DroneConfig)
    map_boundaries: MapBoundaries = field(default_factory=MapBoundaries)
    paths: PathsConfiguration = field(default_factory=PathsConfiguration)
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
