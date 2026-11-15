import os
from dataclasses import dataclass
from typing import Mapping

from common.enum import BoundaryDatum
from common.file_utils import ensure_suffix
from common.model_configs import PUBLISHED_BOUNDARY_DATUM, model_config

MATPLOTLIB_BACKEND_ENVIRONMENT_VARIABLE = "DRONE_NOISE_MATPLOTLIB_BACKEND"
INTERACTIVE_MATPLOTLIB_BACKEND = "Qt5Agg"


def name_boundary_datum(boundary_datum: BoundaryDatum) -> str:
    """File name part of a boundary reading: none for the published reading, the datum for any other."""
    return "" if boundary_datum is PUBLISHED_BOUNDARY_DATUM else f"_{boundary_datum.value}"


def resolve_matplotlib_backend(environment: Mapping[str, str]) -> str:
    return environment.get(MATPLOTLIB_BACKEND_ENVIRONMENT_VARIABLE, INTERACTIVE_MATPLOTLIB_BACKEND)


@dataclass(frozen=True)
class PathsConfiguration:
    data_dir: str = "recourses/data"
    order_dir: str = f"{data_dir}/order/"
    base_noise_dir: str = f"{data_dir}/base_noise"
    noise_graph_navigation_dir: str = f"{data_dir}/noise_graph_navigation"
    round4_road_noise_dir: str = f"{base_noise_dir}/round4_road_laeq16h"
    round4_road_noise_raster_path: str = f"{round4_road_noise_dir}/road_noise_laeq16h_round4_greater_london_10m.tif"
    experiment_results_dir: str = "recourses/experiment_results"
    revision_results_dir: str = "../results"
    revision_artifacts_dir: str = f"{revision_results_dir}/artifacts"

    msoa_population_path: str = f"{data_dir}/MSOA_population_dataset_filtered.geojson"
    london_boundaries_path: str = f"{data_dir}/greater-london-boundaries.geo.json"

    map_file_path: str = "drone_delivery_simulation.html"

    matplotlib_backend = resolve_matplotlib_backend(os.environ)

    census_dir: str = "recourses/census2021"
    ethnicity_dataset_path: str = f"{census_dir}/ethnicity_msoa_dataset.csv"
    age_dataset_path: str = f"{census_dir}/age_msoa_dataset.csv"

    def single_type_order_dataset(self, order_dataset_type: str, stocking_number: int) -> str:
        return f"{self.order_dir}drone_delivery_orders_{stocking_number}_{order_dataset_type}.csv"

    def mixed_order_dataset(self, random_ratio: int, closest_ratio: int, stocking_number: int) -> str:
        return f"{self.order_dir}mixed_stocking_{stocking_number}_random{random_ratio}_closest{closest_ratio}.csv"

    def base_noise_path(self, cell_size_meters: int) -> str:
        return f"{self.base_noise_dir}/base_noise_london_map_{cell_size_meters}.geojson"

    def round4_base_noise_path(self, cell_size_meters: int) -> str:
        return f"{self.base_noise_dir}/base_noise_london_map_{cell_size_meters}_round4_road_laeq16h.parquet"

    def round4_energy_base_noise_path(self, cell_size_meters: int) -> str:
        return f"{self.base_noise_dir}/base_noise_london_map_{cell_size_meters}_round4_road_laeq16h_energy.parquet"

    def navigation_graph_path(self, navigation_cell_size_meters: int) -> str:
        return f"{self.noise_graph_navigation_dir}/navigation_graph_{navigation_cell_size_meters}"

    def warehouse_paths_cache(self) -> str:
        return f"{self.noise_graph_navigation_dir}/warehouse_paths_cache.pkl"

    @staticmethod
    def cell_population_path(
            noise_cell_size_meters: int, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM
    ) -> str:
        return f"recourses/data/cell_population_{noise_cell_size_meters}{name_boundary_datum(boundary_datum)}.pkl"

    @staticmethod
    def cell_ethnicity_path(
            noise_cell_size_meters: int, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM
    ) -> str:
        return f"recourses/data/cell_ethnicity_{noise_cell_size_meters}{name_boundary_datum(boundary_datum)}.pkl"

    @staticmethod
    def cell_age_path(noise_cell_size_meters: int, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM) -> str:
        return f"recourses/data/cell_age_{noise_cell_size_meters}{name_boundary_datum(boundary_datum)}.pkl"


PATH_CONFIGS = PathsConfiguration()

ORDER_BASE_PATH_FURTHEST = PATH_CONFIGS.single_type_order_dataset("furthest", 100_000)
ORDER_BASE_PATH_RANDOM = PATH_CONFIGS.single_type_order_dataset("random", 100_000)
ORDER_BASE_PATH_CLOSEST = PATH_CONFIGS.single_type_order_dataset("closest", 100_000)
ORDER_BASE_PATH_MIXED_50_50 = PATH_CONFIGS.mixed_order_dataset(50, 50, 100_000)

BASE_NOISE_PATH = PATH_CONFIGS.base_noise_path(model_config.grid.noise_cell_m)
ROUND4_BASE_NOISE_PATH = PATH_CONFIGS.round4_base_noise_path(model_config.grid.noise_cell_m)
NAVIGATION_BASE_NOISE_PATH = PATH_CONFIGS.base_noise_path(model_config.grid.nav_cell_m)
NAVIGATION_GRAPH_PATH = PATH_CONFIGS.navigation_graph_path(model_config.grid.nav_cell_m)
CELL_POPULATION_PATH = PATH_CONFIGS.cell_population_path(model_config.grid.noise_cell_m)
CELL_ETHNICITY_PATH = PATH_CONFIGS.cell_ethnicity_path(model_config.grid.noise_cell_m)
CELL_AGE_PATH = PATH_CONFIGS.cell_age_path(model_config.grid.noise_cell_m)


def get_single_type_order_dataset_pattern(order_dataset_type: str, stocking_number: int) -> str:
    return PATH_CONFIGS.single_type_order_dataset(order_dataset_type, stocking_number)

def get_mixed_order_dataset_pattern(random_ratio: int, closest_ratio: int, stocking_number: int) -> str:
    return PATH_CONFIGS.mixed_order_dataset(random_ratio, closest_ratio, stocking_number)

def get_noise_navigation_route_orders_file(file_path: str) -> str:
    return file_path.replace(".csv", "_routes.pkl")

def get_experiment_results_full_file_path(file_name: str) -> str:
    return ensure_suffix(f"{PATH_CONFIGS.experiment_results_dir}/{file_name}", ".pkl")
