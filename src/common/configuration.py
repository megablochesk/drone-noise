from common.model_configs import model_config
from common.simulation_configs import simulation_configs

# Switches
PRINT_DRONE_STATISTICS = simulation_configs.switches.print_drone_stats
PRINT_MODEL_STATISTICS = simulation_configs.switches.print_model_stats
PLOT_MAP = simulation_configs.switches.plot_map
PLOT_STATISTICS = simulation_configs.switches.plot_stats
TAKE_INTO_ACCOUNT_LANDING = simulation_configs.switches.take_landing_into_account
NAVIGATOR_TYPE = simulation_configs.sim.navigator_type

# Simulation counts
TOTAL_ORDER_NUMBER = simulation_configs.sim.orders
TOTAL_DRONE_NUMBER = simulation_configs.sim.drones

# Grid sizes
NOISE_GRID_CELL_SIZE = model_config.grid.noise_cell_m
NAVIGATION_GRID_CELL_SIZE = model_config.grid.nav_cell_m

# Drone parameters
DRONE_NOISE_AT_SOURCE = model_config.drone.noise_at_source_db
DRONE_SPEED = model_config.drone.speed_mps

# Time parameters
MODEL_START_TIME = model_config.time.start_s
MODEL_END_TIME = model_config.time.end_s
NUMBER_OF_HOURS = model_config.time.hours
MODEL_TIME_STEP = model_config.time.step_s
LANDING_TIME_DELAY = model_config.drone.landing_delay_s
DRONE_FLIGHT_ALTITUDE = model_config.drone.flight_altitude_m

# Derived
NUMBER_OF_LANDING_STEPS = model_config.landing_steps
INTERMEDIATE_ALTITUDES_ASCENDING = model_config.intermediate_altitudes_ascending
INTERMEDIATE_ALTITUDES_DESCENDING = model_config.intermediate_altitudes_descending

# Map boundaries (legacy class form)
class MapBoundaries:
    LEFT = model_config.map_bounds.left
    RIGHT = model_config.map_bounds.right
    TOP = model_config.map_bounds.top
    BOTTOM = model_config.map_bounds.bottom

# Data paths
ORDER_FOLDER = model_config.paths.order_folder
ORDER_DATASET_TYPES = simulation_configs.sim.order_dataset_types

def get_single_type_order_dataset_pattern(order_dataset_type, stocking_number=TOTAL_ORDER_NUMBER):
    return model_config.paths.single_type_order_dataset(order_dataset_type, stocking_number)

def get_mixed_order_dataset_pattern(random_ratio, closest_ratio, stocking_number=TOTAL_ORDER_NUMBER):
    return model_config.paths.mixed_order_dataset(random_ratio, closest_ratio, stocking_number)

ORDER_BASE_PATH_FURTHEST = model_config.paths.single_type_order_dataset("furthest", 100_000)
ORDER_BASE_PATH_RANDOM = model_config.paths.single_type_order_dataset("random", 100_000)
ORDER_BASE_PATH_CLOSEST = model_config.paths.single_type_order_dataset("closest", 100_000)
ORDER_BASE_PATH_MIXED_50_50 = model_config.paths.mixed_order_dataset(50, 50, 100_000)

def get_noise_navigation_route_orders_file(file_path):
    return file_path.replace(".csv", "_routes.pkl")

ORDER_BASE_PATH = simulation_configs.default_order_base_path

BASE_NOISE_FOLDER = model_config.paths.base_noise_folder
BASE_NOISE_PATH = model_config.paths.base_noise_path(NOISE_GRID_CELL_SIZE)
NAVIGATION_BASE_NOISE_PATH = model_config.paths.base_noise_path(NAVIGATION_GRID_CELL_SIZE)

NOISE_GRAPH_NAVIGATION_FOLDER = model_config.paths.noise_graph_navigation_folder
NAVIGATION_GRAPH_PATH = model_config.paths.navigation_graph_path(NAVIGATION_GRID_CELL_SIZE)
WAREHOUSE_PATHS_CACHE = model_config.paths.warehouse_paths_cache()

MAP_FILE_PATH = model_config.paths.map_file_path
MSOA_POPULATION_PATH = model_config.paths.msoa_population_path
CELL_POPULATION_PATH = model_config.paths.cell_population_path(NOISE_GRID_CELL_SIZE)
LONDON_BOUNDARIES_PATH = model_config.paths.london_boundaries_path

EXPERIMENT_RESULTS_PATH = model_config.paths.experiment_results_path

MATPLOTLIB_BACKEND = model_config.paths.matplotlib_backend

# Warehouses
LONDON_WAREHOUSES = list(model_config.warehouses.bng_coordinates.items())
LONDON_WAREHOUSES_LATLON = list(model_config.warehouses.latlon_coordinates.items())
