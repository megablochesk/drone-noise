import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Point, Polygon
import random
from datetime import datetime, timedelta
from geopy.distance import distance

from common.configuration import NEW_POPULATION_DENSITY_PATH

WAREHOUSES = {
    'Name': [
        'DBR1', 'DBR2', 'DCR1', 'DCR2', 'DCR3', 'DHA1', 'DHA2',
        'DIG1', 'DRM4', 'DXE1', 'DXN1', 'EHU2', 'MLN2', 'MLN3'
    ],
    'Latitude': [
        51.500773, 51.389926, 51.361253, 51.375578, 51.372757, 51.556886,
        51.556944, 51.653594, 51.524925, 51.520417, 51.504271,
        51.520837, 51.521963, 51.502286
    ],
    'Longitude': [
        0.160277, 0.110440, -0.119953, -0.124525, -0.121484, -0.264871,
        -0.262778, -0.024036, 0.111827, -0.006570, -0.447186,
        -0.006301, -0.080489, -0.073931
    ]
}

GREATER_LONDON_POLYGON = Polygon([
    (-0.510375, 51.28676),
    (-0.334015, 51.42504),
    (-0.152641, 51.56667),
    (-0.003906, 51.66193),
    (0.166626, 51.66193),
    (0.334015, 51.54897),
    (0.334015, 51.36512),
    (0.166626, 51.23339),
    (-0.003906, 51.23339),
    (-0.152641, 51.36512),
    (-0.334015, 51.42504),
    (-0.510375, 51.28676)
])

AREAS = {
    'Name': ['Central London', 'North London', 'East London', 'South London', 'West London'],
    'Latitude': [51.5074, 51.5908, 51.5099, 51.4451, 51.5123],
    'Longitude': [-0.1278, -0.0918, 0.0554, -0.0209, -0.2082],
    'PopulationDensity': [100, 80, 70, 60, 50]
}

MAX_DISTANCE_KM = 5
WAREHOUSE_MAX_DISTANCE_KM = 10
ORDER_COUNT = 5000


def load_warehouses():
    return pd.DataFrame(WAREHOUSES)


def load_areas():
    return pd.DataFrame(AREAS)


def generate_random_point(lat, lon, max_distance_km):
    angle = random.uniform(0, 360)
    distance_offset = random.uniform(0, max_distance_km)
    origin = (lat, lon)
    destination = distance(kilometers=distance_offset).destination(origin, angle)
    return destination.latitude, destination.longitude


def is_within_greater_london(lat, lon):
    point = Point(lon, lat)
    return GREATER_LONDON_POLYGON.contains(point)


def calculate_distance(lat1, lon1, lat2, lon2):
    return ox.distance.great_circle(lat1, lon1, lat2, lon2) / 1000


def find_nearest_warehouse(warehouses_df, dest_lat, dest_lon):
    distances = warehouses_df.apply(
        lambda row: calculate_distance(row['Latitude'], row['Longitude'], dest_lat, dest_lon),
        axis=1
    )
    warehouses_df['Distance'] = distances
    min_distance = distances.min()
    if min_distance > WAREHOUSE_MAX_DISTANCE_KM:
        return None
    nearest_warehouse = warehouses_df.loc[distances.idxmin()]
    return nearest_warehouse


def select_area_by_population_density(areas_df):
    return areas_df.sample(weights=areas_df['PopulationDensity']).iloc[0]


def generate_order(order_id, warehouses_df, areas_df, current_time):
    area = select_area_by_population_density(areas_df)
    dest_lat, dest_lon = generate_random_point(area['Latitude'], area['Longitude'], MAX_DISTANCE_KM)
    if not is_within_greater_london(dest_lat, dest_lon):
        return None
    nearest_warehouse = find_nearest_warehouse(warehouses_df, dest_lat, dest_lon)
    if nearest_warehouse is None:
        return None
    order = {
        'Order ID': order_id,
        'Start Latitude': nearest_warehouse['Latitude'],
        'Start Longitude': nearest_warehouse['Longitude'],
        'End Latitude': dest_lat,
        'End Longitude': dest_lon,
        'Generate Time': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
        'Description': ''
    }
    return order


def generate_orders(num_orders):
    warehouses_df = load_warehouses()
    areas_df = load_areas()

    orders = []
    order_id = 1
    current_time = datetime.now()

    while order_id <= num_orders:
        order = generate_order(order_id, warehouses_df, areas_df, current_time)
        if order:
            orders.append(order)
            order_id += 1
            current_time += timedelta(seconds=random.randint(1, 5))

    return orders


def save_orders_to_csv(orders, filename='drone_delivery_orders.csv'):
    orders_df = pd.DataFrame(orders)
    orders_df.to_csv(filename, index=False)


if __name__ == "__main__":
    orders = generate_orders(ORDER_COUNT)
    save_orders_to_csv(orders)
