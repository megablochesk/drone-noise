from dataclasses import dataclass

from common.file_utils import ensure_suffix
from common.model_configs import model_config


@dataclass(frozen=True)
class PathsConfiguration:
    data_dir: str = "recourses/data"
    order_dir: str = f"{data_dir}/order/"
    base_noise_dir: str = f"{data_dir}/base_noise"
    noise_graph_navigation_dir: str = f"{data_dir}/noise_graph_navigation"
    experiment_results_dir: str = "recourses/experiment_results"

    msoa_population_path: str = f"{data_dir}/MSOA_population_dataset_filtered.geojson"
    london_boundaries_path: str = f"{data_dir}/greater-london-boundaries.geo.json"

    map_file_path: str = "drone_delivery_simulation.html"

    matplotlib_backend = "Qt5Agg"

    census_dir: str = "recourses/census2021"
    ethnicity_dataset_path: str = f"{census_dir}/ethnicity_msoa_dataset.csv"
    age_dataset_path: str = f"{census_dir}/age_msoa_dataset.csv"

    def single_type_order_dataset(self, order_dataset_type: str, stocking_number: int) -> str:
        return f"{self.order_dir}drone_delivery_orders_{stocking_number}_{order_dataset_type}.csv"

    def mixed_order_dataset(self, random_ratio: int, closest_ratio: int, stocking_number: int) -> str:
        return f"{self.order_dir}mixed_stocking_{stocking_number}_random{random_ratio}_closest{closest_ratio}.csv"

    def base_noise_path(self, cell_size_meters: int) -> str:
        return f"{self.base_noise_dir}/base_noise_london_map_{cell_size_meters}.geojson"

    def navigation_graph_path(self, navigation_cell_size_meters: int) -> str:
        return f"{self.noise_graph_navigation_dir}/navigation_graph_{navigation_cell_size_meters}"

    def warehouse_paths_cache(self) -> str:
        return f"{self.noise_graph_navigation_dir}/warehouse_paths_cache.pkl"

    @staticmethod
    def cell_population_path(noise_cell_size_meters: int) -> str:
        return f"recourses/data/cell_population_{noise_cell_size_meters}.pkl"

    @staticmethod
    def cell_ethnicity_path(noise_cell_size_meters: int) -> str:
        return f"recourses/data/cell_ethnicity_{noise_cell_size_meters}.pkl"


PATH_CONFIGS = PathsConfiguration()

ORDER_BASE_PATH_FURTHEST = PATH_CONFIGS.single_type_order_dataset("furthest", 100_000)
ORDER_BASE_PATH_RANDOM = PATH_CONFIGS.single_type_order_dataset("random", 100_000)
ORDER_BASE_PATH_CLOSEST = PATH_CONFIGS.single_type_order_dataset("closest", 100_000)
ORDER_BASE_PATH_MIXED_50_50 = PATH_CONFIGS.mixed_order_dataset(50, 50, 100_000)

BASE_NOISE_PATH = PATH_CONFIGS.base_noise_path(model_config.grid.noise_cell_m)
NAVIGATION_BASE_NOISE_PATH = PATH_CONFIGS.base_noise_path(model_config.grid.nav_cell_m)
NAVIGATION_GRAPH_PATH = PATH_CONFIGS.navigation_graph_path(model_config.grid.nav_cell_m)
CELL_POPULATION_PATH = PATH_CONFIGS.cell_population_path(model_config.grid.noise_cell_m)
CELL_ETHNICITY_PATH = PATH_CONFIGS.cell_ethnicity_path(model_config.grid.noise_cell_m)


def get_single_type_order_dataset_pattern(order_dataset_type: str, stocking_number: int) -> str:
    return PATH_CONFIGS.single_type_order_dataset(order_dataset_type, stocking_number)

def get_mixed_order_dataset_pattern(random_ratio: int, closest_ratio: int, stocking_number: int) -> str:
    return PATH_CONFIGS.mixed_order_dataset(random_ratio, closest_ratio, stocking_number)

def get_noise_navigation_route_orders_file(file_path: str) -> str:
    return file_path.replace(".csv", "_routes.pkl")

def get_experiment_results_full_file_path(file_name: str) -> str:
    return ensure_suffix(f"{PATH_CONFIGS.experiment_results_dir}/{file_name}", ".pkl")
