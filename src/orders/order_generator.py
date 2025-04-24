import json
import random

import pandas as pd
from common.configuration import (
    ORDER_BASE_PATH, LONDON_WAREHOUSES, MSOA_POPULATION_PATH,
    get_mixed_order_dataset_pattern
)
from common.coordinate import Coordinate
from orders.order import Order
from shapely.geometry import shape, Point


def load_all_orders(path):
    return pd.read_csv(path)


def load_orders(number_of_orders, path=ORDER_BASE_PATH):
    order_df = load_all_orders(path)

    limited_df = order_df.head(number_of_orders)

    orders = [
        Order(
            order_id=int(row['Order ID']),
            start_location=Coordinate(row['Start Northing'], row['Start Easting']),
            end_location=Coordinate(row['End Northing'], row['End Easting'])
        )
        for _, row in limited_df.iterrows()
    ]

    return orders


def load_geojson(geojson_path):
    with open(geojson_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_msoa_index():
    geojson_data = load_geojson(MSOA_POPULATION_PATH)

    msoa_dict = {}
    msoa_populations = {}

    for feature in geojson_data['features']:
        msoa_code = feature['properties'].get('msoa21cd', '').strip()
        population = feature['properties'].get('population', None)

        polygon = shape(feature['geometry'])

        if population is not None:
            msoa_dict[msoa_code] = polygon
            msoa_populations[msoa_code] = population

    return msoa_dict, msoa_populations


def generate_random_point_in_msoa(msoa_code, polygon, max_attempts=10000):
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    if not polygon.is_valid or polygon.area == 0:
        return polygon.centroid

    # Proceed with random sampling if the polygon has a valid area
    minx, miny, maxx, maxy = polygon.bounds

    for _ in range(max_attempts):
        randx = random.uniform(minx, maxx)
        randy = random.uniform(miny, maxy)
        point = Point(randx, randy)
        if polygon.contains(point):
            return point

    print(msoa_code)
    return polygon.centroid


def generate_point_for_msoa(msoa_code):
    polygon = MSOA_INDEX.get(msoa_code)
    if not polygon:
        raise ValueError(f"No polygon found for MSOA code: {msoa_code}")

    random_point = generate_random_point_in_msoa(msoa_code, polygon)
    x_rounded = round(random_point.x, 2)
    y_rounded = round(random_point.y, 2)

    return x_rounded, y_rounded


def calculate_population_distribution(msoa_populations):
    total_population = sum(msoa_populations.values())
    if total_population == 0:
        raise ValueError("Total population is zero, cannot generate weighted points.")

    cumulative = 0.0
    distribution = []
    for msoa_code, pop in msoa_populations.items():
        cumulative += pop / total_population
        distribution.append((msoa_code, cumulative))
    return distribution


def generate_random_population_based_point():
    r = random.random()

    for msoa_code, cum_prob in POPULATION_DISTRIBUTION:
        if r <= cum_prob:
            x, y = generate_point_for_msoa(msoa_code)
            return msoa_code, x, y


def distance_between_points(warehouse, point):
    wx, wy = warehouse
    x, y = point

    dx = wx - x
    dy = wy - y

    return dx * dx + dy * dy


def find_warehouse(destination_point, comparator):
    chosen_coord = None
    chosen_distance = None

    for name, coord in LONDON_WAREHOUSES:
        dist = distance_between_points(destination_point, (coord.easting, coord.northing))
        if chosen_distance is None or comparator(dist, chosen_distance):
            chosen_distance = dist
            chosen_coord = coord

    return chosen_coord.easting, chosen_coord.northing


def find_closest_warehouse(point):
    return find_warehouse(point, lambda current, best: current < best)


def find_furthest_warehouse(point):
    return find_warehouse(point, lambda current, best: current > best)


def choose_random_warehouse():
    warehouse = random.choice(LONDON_WAREHOUSES)
    return warehouse[1].easting, warehouse[1].northing


def choose_warehouse(point, method):
    match method:
        case 'closest':
            return find_closest_warehouse(point)
        case 'furthest':
            return find_furthest_warehouse(point)
        case 'random':
            return choose_random_warehouse()
        case _:
            raise ValueError(f"Unknown warehouse selection method: {method}")


def generate_order(order_id, destination_point, selection_method):
    _, destination_x, destination_y = destination_point
    warehouse_x, warehouse_y = choose_warehouse((destination_x, destination_y), selection_method)
    return {
        'Order ID': order_id,
        'Start Northing': warehouse_y,
        'Start Easting': warehouse_x,
        'End Northing': destination_y,
        'End Easting': destination_x
    }


def save_orders_to_csv(orders, filename):
    orders_df = pd.DataFrame(orders)
    orders_df.to_csv(filename, index=False)


MSOA_INDEX, MSOA_POPULATIONS = build_msoa_index()
POPULATION_DISTRIBUTION = calculate_population_distribution(MSOA_POPULATIONS)


def generate_datasets(number_of_deliveries=10_000):
    destinations = [generate_random_population_based_point() for _ in range(number_of_deliveries)]

    for method in ['closest', 'furthest', 'random']:
        orders = []
        for order_id in range(1, number_of_deliveries + 1):
            orders.append(generate_order(order_id, destinations[order_id - 1], method))

        save_file_name = f'recourses/data/order/drone_delivery_orders_{number_of_deliveries}_{method}.csv'

        save_orders_to_csv(orders, save_file_name)

def generate_mixed_stocking_datasets(number_of_deliveries=10_000):
    ratios = [(i, 100 - i) for i in range(100, 0, -10)]  # (random%, closest%)

    destinations = [generate_random_population_based_point() for _ in range(number_of_deliveries)]

    for random_pct, closest_pct in ratios:
        num_random = number_of_deliveries * random_pct // 100

        orders = []
        for i in range(1, num_random + 1):
            orders.append(generate_order(i, destinations[i - 1], 'random'))

        for i in range(num_random + 1, number_of_deliveries + 1):
            orders.append(generate_order(i, destinations[i - 1], 'closest'))

        random.shuffle(orders)

        save_file_name = get_mixed_order_dataset_pattern(random_pct, closest_pct, number_of_deliveries)

        save_orders_to_csv(orders, save_file_name)

