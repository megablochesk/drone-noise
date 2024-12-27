# Switches
PRINT_DRONE_STATISTICS = False
PRINT_MODEL_STATISTICS = True
PLOT_SIMULATION = True
USE_DENSITY_MATRIX = True

TOTAL_ORDER_NUMBER = 50
TOTAL_DRONE_NUMBER = 400

NOISE_MATRIX_CELL_LENGTH = 500  # meters
NOISE_MATRIX_CELL_WIDTH = 500  # meters

DRONE_NOISE = 90  # The central sound level of a flying drone (db)
DRONE_SPEED = 27  # metres per second, average drone speed

MODEL_START_TIME = 36000  # 10 a.m. - model start time (10 * 60 * 60)
MODEL_TIME_STEP = 30  # seconds
DRONE_ALTITUTE = 100  # meters

# Map boundary in British National Grid
MAP_LEFT = 504278.00
MAP_RIGHT = 562823.00
MAP_TOP = 201205.00
MAP_BOTTOM = 155489.00

# Base path for saving/loading orders to/from the local
ORDER_BASE_PATH = 'recourses/data/order/ne_drone_delivery_orders_1000.csv'
# Base path for experiment results
RESULT_BASE_PATH = 'recourses/results/experiments'

LONDON_WAREHOUSES = [
    ('DBR1', (180193.93, 550041.28)),
    ('DBR2', (167766.96, 546937.62)),
    ('DCR1', (164142.21, 530990.34)),
    ('DCR2', (165727.01, 530631.31)),
    ('DCR3', (165418.73, 530850.99)),
    ('DHA1', (185648.81, 520386.09)),
    ('DHA2', (185658.7, 520531.03)),
    ('DIG1', (196826.63, 536790.04)),
    ('DRM4', (182781.49, 546601.21)),
    ('DXE1', (182049.78, 538402.03)),
    ('DXN1', (179513.55, 507871.84)),
    ('EHU2', (182097.0, 538419.42)),
    ('MLN2', (182084.59, 533269.42)),
    ('MLN3', (179908.41, 533781.95)),
]