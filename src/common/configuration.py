from common.coordinate import Coordinate

# Switches
PRINT_DRONE_STATISTICS = False
PRINT_MODEL_STATISTICS = True
PLOT_MAP = False
PLOT_STATISTICS = True

TOTAL_ORDER_NUMBER = 1000
TOTAL_DRONE_NUMBER = 400

NOISE_GRID_CELL_SIZE_METERS = 500

DRONE_NOISE_AT_SOURCE = 90.0  # The central sound level of a flying drone (db)
DRONE_SPEED = 27  # metres per second, average drone speed

MODEL_START_TIME = 36000  # 10 a.m. - model start time (10 * 60 * 60)
MODEL_TIME_STEP = 30  # seconds
DRONE_ALTITUTE = 100.0  # meters


# Map boundary in British National Grid
class MapBoundaries:
    LEFT = 503568.18
    RIGHT = 561950.07
    TOP = 200930.56
    BOTTOM = 155850.78


# Data paths
ORDER_BASE_PATH_FURTHEST = f'recourses/data/order/drone_delivery_orders_10000_furthest.csv'
ORDER_BASE_PATH_RANDOM = f'recourses/data/order/drone_delivery_orders_10000_random.csv'
ORDER_BASE_PATH_CLOSEST = f'recourses/data/order/drone_delivery_orders_10000_closest.csv'

ORDER_BASE_PATH = ORDER_BASE_PATH_FURTHEST

BASE_NOISE_PATH = f'recourses/data/base_noise/base_noise_london_map_{NOISE_GRID_CELL_SIZE_METERS}.geojson'
RESULT_BASE_PATH = 'recourses/results/experiments'
MAP_FILE_PATH = f'drone_delivery_simulation.html'
MSOA_POPULATION_PATH = 'recourses/data/MSOA_population_dataset_filtered.geojson'
LONDON_BOUNDARIES_PATH = 'recourses/data/greater-london-boundaries.geo.json'

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
