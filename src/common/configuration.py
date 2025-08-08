import math

from common.coordinate import Coordinate
from common.enum import NavigationType

# Switches
PRINT_DRONE_STATISTICS = False
PRINT_MODEL_STATISTICS = False
PLOT_MAP = False
PLOT_STATISTICS = False

TAKE_INTO_ACCOUNT_LANDING = False
NAVIGATOR_TYPE = NavigationType.STRAIGHT

TOTAL_ORDER_NUMBER = 100_000
TOTAL_DRONE_NUMBER = 500

NOISE_GRID_CELL_SIZE = 500 # meters
NAVIGATION_GRID_CELL_SIZE = 100 # meters

DRONE_NOISE_AT_SOURCE = 90.0  # The central sound level of a drone (dB)
DRONE_SPEED = 27  # metres per second

MODEL_START_TIME = 36_000  # 10 a.m. - model start time (10 * 60 * 60)
MODEL_END_TIME = 72_000  # 8 p.m.
NUMBER_OF_HOURS = int((MODEL_END_TIME - MODEL_START_TIME) / 3600)
MODEL_TIME_STEP = 30  # seconds
LANDING_TIME_DELAY = 60 # seconds
DRONE_FLIGHT_ALTITUDE = 100.0  # meters

NUMBER_OF_LANDING_STEPS = math.ceil(LANDING_TIME_DELAY / MODEL_TIME_STEP)

INTERMEDIATE_ALTITUDES_ASCENDING = [
    DRONE_FLIGHT_ALTITUDE * (i / NUMBER_OF_LANDING_STEPS)
    for i in range(0, NUMBER_OF_LANDING_STEPS)
]
INTERMEDIATE_ALTITUDES_DESCENDING = INTERMEDIATE_ALTITUDES_ASCENDING[::-1]


# Map boundary in British National Grid
class MapBoundaries:
    LEFT = 503568.18
    RIGHT = 561950.07
    TOP = 200930.56
    BOTTOM = 155850.78


# Data paths
ORDER_FOLDER = 'recourses/data/order/'
ORDER_DATASET_TYPES = ['furthest', 'random', 'closest']

def get_single_type_order_dataset_pattern(order_dataset_type, stocking_number=TOTAL_ORDER_NUMBER):
    return ORDER_FOLDER + f'drone_delivery_orders_{stocking_number}_{order_dataset_type}.csv'

def get_mixed_order_dataset_pattern(random_ratio, closest_ratio, stocking_number=TOTAL_ORDER_NUMBER):
    return ORDER_FOLDER + f'mixed_stocking_{stocking_number}_random{random_ratio}_closest{closest_ratio}.csv'

ORDER_BASE_PATH_FURTHEST = get_single_type_order_dataset_pattern('furthest', 100_000)
ORDER_BASE_PATH_RANDOM = get_single_type_order_dataset_pattern('random', 100_000)
ORDER_BASE_PATH_CLOSEST = get_single_type_order_dataset_pattern('closest', 100_000)
ORDER_BASE_PATH_MIXED_50_50 = get_mixed_order_dataset_pattern(50, 50, 100_000)

def get_noise_navigation_route_orders_file(file_path):
    return file_path.replace('.csv', '_routes.pkl')

ORDER_BASE_PATH = ORDER_BASE_PATH_MIXED_50_50

BASE_NOISE_FOLDER = 'recourses/data/base_noise/'

BASE_NOISE_PATH = BASE_NOISE_FOLDER + f'base_noise_london_map_{NOISE_GRID_CELL_SIZE}.geojson'
NAVIGATION_BASE_NOISE_PATH = BASE_NOISE_FOLDER + f'base_noise_london_map_{NAVIGATION_GRID_CELL_SIZE}.geojson'

NOISE_GRAPH_NAVIGATION_FOLDER = 'recourses/data/noise_graph_navigation/'

NAVIGATION_GRAPH_PATH = NOISE_GRAPH_NAVIGATION_FOLDER + f'navigation_graph_{NAVIGATION_GRID_CELL_SIZE}'
WAREHOUSE_PATHS_CACHE = NOISE_GRAPH_NAVIGATION_FOLDER + "warehouse_paths_cache.pkl"

MAP_FILE_PATH = 'drone_delivery_simulation.html'
MSOA_POPULATION_PATH = 'recourses/data/MSOA_population_dataset_filtered.geojson'
CELL_POPULATION_PATH = f'recourses/data/cell_population_{NOISE_GRID_CELL_SIZE}.pkl'
LONDON_BOUNDARIES_PATH = 'recourses/data/greater-london-boundaries.geo.json'

EXPERIMENT_RESULTS_PATH = 'recourses/experiment_results/'

MATPLOTLIB_BACKEND = 'Qt5Agg'

LONDON_WAREHOUSES = [
    ('DBR1', Coordinate(180193.93, 550041.28)),
    ('DBR2', Coordinate(167766.96, 546937.62)),
    ('DCR1', Coordinate(164142.21, 530990.34)),
    ('DCR2', Coordinate(165727.01, 530631.31)),
    ('DCR3', Coordinate(165418.73, 530850.99)),
    ('DHA1', Coordinate(185648.81, 520386.09)),
    ('DHA2', Coordinate(185658.7, 520531.03)),
    ('DIG1', Coordinate(196826.63, 536790.04)),
    ('DRM4', Coordinate(182781.49, 546601.21)),
    ('DXE1', Coordinate(182049.78, 538402.03)),
    ('DXN1', Coordinate(179513.55, 507871.84)),
    ('EHU2', Coordinate(182097.0, 538419.42)),
    ('MLN2', Coordinate(182084.59, 533269.42)),
    ('MLN3', Coordinate(179908.41, 533781.95)),
]

LONDON_WAREHOUSES_LATLON = [
    ('DBR1', (51.500773, 0.160277)),
    ('DBR2', (51.389926, 0.110440)),
    ('DCR1', (51.361253, -0.119953)),
    ('DCR2', (51.375578, -0.124525)),
    ('DCR3', (51.372757, -0.121484)),
    ('DHA1', (51.556886, -0.264871)),
    ('DHA2', (51.556944, -0.262778)),
    ('DIG1', (51.653594, -0.024036)),
    ('DRM4', (51.524925, 0.111827)),
    ('DXE1', (51.520417, -0.006570)),
    ('DXN1', (51.504271, -0.447186)),
    ('EHU2', (51.520837, -0.006301)),
    ('MLN2', (51.521963, -0.080489)),
    ('MLN3', (51.502286, -0.073931)),
]
