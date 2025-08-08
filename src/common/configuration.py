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

# Data paths
ORDER_DATASET_TYPES = simulation_configs.sim.order_dataset_types

ORDER_BASE_PATH = simulation_configs.default_order_base_path

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

NOISE_GRID_CELL_SIZE = model_config.grid.noise_cell_m
NAVIGATION_GRID_CELL_SIZE = model_config.grid.nav_cell_m

BASE_NOISE_PATH = model_config.paths.base_noise_path(NOISE_GRID_CELL_SIZE)
NAVIGATION_BASE_NOISE_PATH = model_config.paths.base_noise_path(NAVIGATION_GRID_CELL_SIZE)

NAVIGATION_GRAPH_PATH = model_config.paths.navigation_graph_path(NAVIGATION_GRID_CELL_SIZE)
CELL_POPULATION_PATH = model_config.paths.cell_population_path(NOISE_GRID_CELL_SIZE)
