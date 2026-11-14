import random

from census_analysis.msoa_data import load_msoa_data
from common.enum import OrderDatasetType
from common.file_utils import save_df_to_csv
from common.model_configs import model_config
from common.path_configs import get_single_type_order_dataset_pattern, get_mixed_order_dataset_pattern
from orders.seeded_order_pool import sample_point_in_polygon

LONDON_WAREHOUSES = list(model_config.warehouses.bng_coordinates.items())
ORDER_DATASET_TYPES = tuple(e.value for e in OrderDatasetType)


def generate_random_point_in_msoa(msoa_code, polygon, max_attempts=10000):
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    if not polygon.is_valid or polygon.area == 0:
        return polygon.centroid

    point = sample_point_in_polygon(polygon, random, max_attempts)
    if point is not None:
        return point

    print(msoa_code)
    return polygon.centroid


def generate_point_for_msoa(msoa_code):
    polygon = load_msoa_data().msoa_index.get(msoa_code)
    if not polygon:
        raise ValueError(f"No polygon found for MSOA code: {msoa_code}")

    random_point = generate_random_point_in_msoa(msoa_code, polygon)
    return round(random_point.x, 2), round(random_point.y, 2)


def generate_random_population_based_point():
    random_value = random.random()
    for msoa_code, msoa_pop_distribution in load_msoa_data().population_distribution:
        if random_value <= msoa_pop_distribution:
            x, y = generate_point_for_msoa(msoa_code)
            return msoa_code, x, y
    return None


def distance_between_points(warehouse_coordinates, point_coordinates):
    wx, wy = warehouse_coordinates
    x, y = point_coordinates

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
        case OrderDatasetType.CLOSEST:
            return find_closest_warehouse(point)
        case OrderDatasetType.FURTHEST:
            return find_furthest_warehouse(point)
        case OrderDatasetType.RANDOM:
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


def generate_datasets(number_of_orders=10_000):
    destinations = [generate_random_population_based_point() for _ in range(number_of_orders)]

    for method in ORDER_DATASET_TYPES:
        orders = []
        for order_id in range(1, number_of_orders + 1):
            orders.append(generate_order(order_id, destinations[order_id - 1], method))

        save_file_name = get_single_type_order_dataset_pattern(method, number_of_orders)

        save_df_to_csv(orders, save_file_name)


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

        save_df_to_csv(orders, save_file_name)
