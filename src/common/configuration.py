# Switches
# Print delivery info to the terminal
PRINT_TERMINAL = True
# Plot the simulation
PLOT_SIMULATION = True
# Use DensityMatrix to track matrix: tracking noise in matrix
USE_DENSITY_MATRIX = True

# Prioritize low average noise cells
# Use the first or second cost function: 'first' - K; 'second' - P
COST_FUNCTION = 'second'
PRIORITIZE_K = 5
PRIORITIZE_P = 0


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

TOTAL_ORDER_NUMBER = 500
TOTAL_DRONE_NUMBER = 400

NOISE_MATRIX_CELL_LENGTH = 500
NOISE_MATRIX_CELL_WIDTH = 500

DRONE_NOISE = 90  # The central sound level of a flying drone (db)
DRONE_ALTITUTE = 100

# Center iteration running step (doesn't work if the program is running very slowly)
# e.g. CENTER_PER_SLICE_TIME = 1s, the program will run each iteration for 0.5 second (if possible)
# when it's the iteration to writing data to local, the program will slow down a little bit,
# but it will run faster in the next a few iterations to compensate for the slow-down
CENTER_PER_SLICE_TIME = 0.01

# Paths
# Base path for saving/loading orders to/from the local
ORDER_BASE_PATH = 'recourses/data/order/ne_drone_delivery_orders_1000.csv'
# Base path for experiment results
RESULT_BASE_PATH = 'recourses/results/experiments'

# Map boundary
MAP_LEFT = 503700.00  # was 504278.00
MAP_RIGHT = 562823.00
MAP_TOP = 201205.00
MAP_BOTTOM = 155489.00
