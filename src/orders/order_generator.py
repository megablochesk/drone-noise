import json
import random

import pandas as pd
from common.configuration import ORDER_BASE_PATH, LONDON_WAREHOUSES, MSOA_POPULATION_PATH
from common.coordinate import Coordinate
from orders.order import Order
from shapely.geometry import shape, Point


def load_orders(number_of_orders):
    order_df = pd.read_csv(ORDER_BASE_PATH)

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


def generate_random_points(num_points):
    generated_points = []

    for _ in range(num_points):
        generated_points.append(generate_random_population_based_point())

    return generated_points


def generate_random_population_based_point():
    r = random.random()

    for msoa_code, cum_prob in POPULATION_DISTRIBUTION:
        if r <= cum_prob:
            x, y = generate_point_for_msoa(msoa_code)
            return msoa_code, x, y


def find_warehouse(point, comparison):
    x, y = point
    best_warehouse = None
    best_distance_sq = None

    for name, (wx, wy) in LONDON_WAREHOUSES:
        dx = wx - x
        dy = wy - y
        dist_sq = dx * dx + dy * dy

        if best_distance_sq is None or comparison(dist_sq, best_distance_sq):
            best_distance_sq = dist_sq
            best_warehouse = (name, (wx, wy))

    return best_warehouse[1]


def find_closest_warehouse(point):
    return find_warehouse(point, lambda current, best: current < best)


def find_furthest_warehouse(point):
    return find_warehouse(point, lambda current, best: current > best)


def choose_random_warehouse():
    warehouse = random.choice(LONDON_WAREHOUSES)
    return warehouse[1]


def choose_warehouse(point, method):
    if method == 'closest':
        return find_closest_warehouse(point)
    elif method == 'furthest':
        return find_furthest_warehouse(point)
    elif method == 'random':
        return choose_random_warehouse()
    else:
        raise ValueError(f"Unknown warehouse selection method: {method}")


def generate_order(order_id, selection_method):
    _, destination_x, destination_y = generate_random_population_based_point()
    warehouse_x, warehouse_y = choose_warehouse((destination_x, destination_y), selection_method)

    return {
        'Order ID': order_id,
        'Start Northing': warehouse_y,
        'Start Easting': warehouse_x,
        'End Northing': destination_y,
        'End Easting': destination_x
    }


def generate_orders(num_orders, selection_method):
    orders = []
    for order_id in range(1, num_orders + 1):
        orders.append(generate_order(order_id, selection_method))
    return orders


def save_orders_to_csv(orders, filename='drone_delivery_orders.csv'):
    orders_df = pd.DataFrame(orders)
    orders_df.to_csv(filename, index=False)


MSOA_INDEX, MSOA_POPULATIONS = build_msoa_index()
POPULATION_DISTRIBUTION = calculate_population_distribution(MSOA_POPULATIONS)

if __name__ == "__main__":
    number_of_deliveries = 10000
    suffix = 'closest'  # can be 'closest', 'furthest', or 'random'

    save_file_name = f'data/order/drone_delivery_orders_{number_of_deliveries}_{suffix}.csv'
    delivery_orders = generate_orders(number_of_deliveries, suffix)
    save_orders_to_csv(delivery_orders, save_file_name)
