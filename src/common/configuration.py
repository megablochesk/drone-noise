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
    ('MLN3', (51.502286, -0.073931))
]

LONDON_WAREHOUSES_OLD = [
    ('DBR1', (550041.28, 180193.93)),
    ('DBR2', (546937.62, 167766.96)),
    ('DCR1', (530990.34, 164142.21)),
    ('DCR2', (530631.31, 165727.01)),
    ('DCR3', (530850.99, 165418.73)),
    ('DHA1', (520386.09, 185648.81)),
    ('DHA2', (520531.03, 185658.7)),
    ('DIG1', (536790.04, 196826.63)),
    ('DRM4', (546601.21, 182781.49)),
    ('DXE1', (538402.03, 182049.78)),
    ('DXN1', (507871.84, 179513.55)),
    ('EHU2', (538419.42, 182097.0)),
    ('MLN2', (533269.42, 182084.59)),
    ('MLN3', (533781.95, 179908.41)),
]

TOTAL_ORDER_NUMBER = 10
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
ORDER_BASE_PATH = 'recourses/data/order/drone_delivery_orders_old.csv'
# Base path for experiment results
RESULT_BASE_PATH = 'recourses/results/experiments'

# Map boundary
MAP_LEFT   = -0.510 + 0.004
MAP_RIGHT  =  0.334 + 0.020
MAP_TOP    =  51.691 - 0.005
MAP_BOTTOM =  51.286 + 0.003
