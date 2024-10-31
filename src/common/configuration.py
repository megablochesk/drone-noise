# Switches
# Print delivery info to the terminal
PRINT_TERMINAL = True
# Plot the simulation
PLOT_SIMULATION = True
# Use DensityMatrix to track matrix: tracking noise in matrix
USE_DENSITY_MATRIX = True
# Use local order data: True - load predefined orders; False - generate new orders
USE_LOCAL_ORDER = True
# TODO: load and use population density for harm calculation and path-finding
USE_POPULATION_DENSITY = False

# Prioritize low average noise cells
# Use the first or second cost function: 'first' - K; 'second' - P
COST_FUNCTION = 'second'
PRIORITIZE_K = 0
PRIORITIZE_P = 5

# Coordinates of warehouses
WAREHOUSES = [
    [37.805858377440266, -122.41276123169143],
    [37.76077744044274, -122.390011845567],
    [37.7426674419608, -122.39981393102507]
]

LONDON_WAREHOUSES = [
    [51.500773, 0.160277],
    [51.389926, 0.110440],
    [51.361253, -0.119953],
    [51.375578, -0.124525],
    [51.372757, -0.121484],
    [51.556886, -0.264871],
    [51.556944, -0.262778],
    [51.653594, -0.024036],
    [51.524925, 0.111827],
    [51.520417, -0.006570],
    [51.504271, -0.447186],
    [51.520837, -0.006301],
    [51.521963, -0.080489],
    [51.502286, -0.073931]
]

# Total number of orders (5000 predefined orders)
ORDERS = 5
# Total number of drones
DRONES = 400
# Noise matrix cell size (in meter)
NOISE_CELL_LENGTH = 100
NOISE_CELL_WIDTH = 100
# Harm threshold (in dB)
HARM_AVG_LEVEL = 45
HARM_MAX_LEVEL = 85

# Center iteration running step (doesn't work if the program is running very slowly)
# e.g. CENTER_PER_SLICE_TIME = 1s, the program will run each iteration for 0.5 second (if possible)
# when it's the iteration to writing data to local, the program will slow down a little bit,
# but it will run faster in the next a few iterations to compensate for the slow-down
CENTER_PER_SLICE_TIME = 0.5

# Paths
# Base path for saving/loading orders to/from the local
ORDER_BASE_PATH = 'recourses/data/order/orders_v2.csv'
NEW_ORDER_BASE_PATH = 'recourses/data/order/drone_delivery_orders.csv'
# Base path for saving/loading matrix tracking data
NOISE_BASE_PATH = 'recourses/results/matrix/trajectory'
# Base path for saving heatmap/density map
HEATMAP_BASE_PATH = 'recourses/results/matrix/heatmaps'
# Base path for saving overlay images of folium map and density matrix
OVERLAY_BASE_PATH = 'recourses/results/matrix/heatmaps/overlay'
# Geographical data
GEO_PATH = 'recourses/data/geo/shown_geography.geojson'
# Old population density data
OLD_POPULATION_DENSITY_PATH = 'recourses/data/population/shown_tract_popdensity2010.csv'
# New population density data
NEW_POPULATION_DENSITY_PATH = 'recourses/data/population/London_msoa_2021_with_population_density.geojson'
# Simulation plotter background image
BACKGROUND_IMAGE_PATH = 'recourses/images/map.jpeg'
# Base path for saving matrix density matrix
MATRIX_BASE_PATH = 'recourses/results/matrix/matrix'
# Base path for saving matrix histogram
HISTOGRAM_BASE_PATH = 'recourses/results/matrix/histogram'
# Base path for experiment results
RESULT_BASE_PATH = 'recourses/results/experiments'

# Map
CRS = 'epsg:3857'
# Map boundary
MAP_LEFT   = -0.510 + 0.004
MAP_RIGHT  =  0.334 + 0.020
MAP_TOP    =  51.691 - 0.005
MAP_BOTTOM =  51.286 + 0.003
# offset range 0-200m (latitude) to a random generated coordinate
# Notice this is calculated at around 37 latitude
RANDOM_LA_COORD_OFFSET = 0.001802
# Notice this is calculated at around 37 latitude
# offset range 0-200m (longitude) to a random generated coordinate
RANDOM_LO_COORD_OFFSET = 0.002278

# geo popup layer style and highlight functions
style_function = lambda x: {'fillColor': '#ffffff',
                            'color': '#000000',
                            'fillOpacity': 0.1,
                            'weight': 0.1}
highlight_function = lambda x: {'fillColor': '#000000',
                                'color': '#000000',
                                'fillOpacity': 0.50,
                                'weight': 0.1}
