"""Stylised depot layouts for the layout experiment, plus the actual sites of the published model."""
import math
import random
from functools import lru_cache

import numpy as np
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from sklearn.cluster import KMeans

from common.coordinate import Coordinate, calculate_distance
from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS
from metrics.cell_table import load_cell_table
from noise.grid_generator import load_and_reproject_geojson
from noise.noise_grid import load_noise_grid
from orders.seeded_order_pool import COORDINATE_DECIMALS, MAXIMUM_SAMPLING_ATTEMPTS, sample_point_in_polygon

ACTUAL_LAYOUT = "actual"
SINGLE_HUB_LAYOUT = "single_hub"
RING_LAYOUT = "ring_18km"
POPULATION_KMEANS_LAYOUT = "population_kmeans"
NUMBER_OF_RANDOM_DRAWS = 5
RANDOM_DRAW_LAYOUTS = tuple(f"random_draw_{draw}" for draw in range(1, NUMBER_OF_RANDOM_DRAWS + 1))

NUMBER_OF_STYLISED_DEPOTS = 14
RING_RADIUS_M = 18_000.0
# Half a noise cell: a snapped depot sits clearly inside the boundary rather than on its edge.
BOUNDARY_INSET_M = 250.0
KMEANS_SEED = 0
KMEANS_RESTARTS = 10


def calculate_population_weighted_centre(
        eastings: np.ndarray, northings: np.ndarray, population: np.ndarray
) -> Coordinate:
    return Coordinate(
        northing=np.average(northings, weights=population), easting=np.average(eastings, weights=population)
    )


def place_depots_on_ring(centre: Coordinate, radius_m: float, number_of_depots: int) -> list[Coordinate]:
    """Evenly spaced depots, the first due east of the centre, then anticlockwise."""
    bearings_rad = [2.0 * math.pi * depot / number_of_depots for depot in range(number_of_depots)]
    return [
        Coordinate(
            northing=centre.northing + radius_m * math.sin(bearing_rad),
            easting=centre.easting + radius_m * math.cos(bearing_rad),
        )
        for bearing_rad in bearings_rad
    ]


def snap_inside_boundary(point: Coordinate, centre: Coordinate, boundary: BaseGeometry, inset_m: float) -> Coordinate:
    """Leaves inside points alone; pulls outside points along the line to the centre until `inset_m` inside."""
    if boundary.contains(Point(point.easting, point.northing)):
        return point

    line_from_centre = LineString([(centre.easting, centre.northing), (point.easting, point.northing)])
    first_exit = line_from_centre.intersection(boundary.boundary)
    exit_distance_m = min(line_from_centre.project(crossing) for crossing in explode_points(first_exit))
    snapped = line_from_centre.interpolate(exit_distance_m - inset_m)
    return Coordinate(northing=snapped.y, easting=snapped.x)


def explode_points(geometry: BaseGeometry) -> list[Point]:
    return [Point(coordinates) for part in getattr(geometry, "geoms", [geometry]) for coordinates in part.coords]


def cluster_population_weighted_centres(
        eastings: np.ndarray, northings: np.ndarray, population: np.ndarray, number_of_depots: int, seed: int
) -> list[Coordinate]:
    """Centres of a k-means clustering of the cells in which every cell counts with its population."""
    clustering = KMeans(n_clusters=number_of_depots, n_init=KMEANS_RESTARTS, random_state=seed)
    clustering.fit(np.column_stack([eastings, northings]), sample_weight=population)
    return [Coordinate(northing=northing, easting=easting) for easting, northing in clustering.cluster_centers_]


def sample_uniform_depots(boundary: BaseGeometry, number_of_depots: int, seed: int) -> list[Coordinate]:
    random_generator = random.Random(f"depot-layout-{seed}")
    points = [
        sample_point_in_polygon(boundary, random_generator, MAXIMUM_SAMPLING_ATTEMPTS)
        for _ in range(number_of_depots)
    ]
    return [Coordinate(northing=point.y, easting=point.x) for point in points]


@lru_cache(maxsize=1)
def load_study_boundary() -> BaseGeometry:
    return load_and_reproject_geojson(PATH_CONFIGS.london_boundaries_path).geometry.union_all()


def load_population_centre() -> Coordinate:
    grid, cell_table = load_noise_grid(), load_cell_table()
    return calculate_population_weighted_centre(grid.centroid_eastings, grid.centroid_northings, cell_table.population)


def build_stylised_depots(layout_name: str) -> list[Coordinate]:
    grid, cell_table, boundary = load_noise_grid(), load_cell_table(), load_study_boundary()
    centre = load_population_centre()

    if layout_name == SINGLE_HUB_LAYOUT:
        return [centre]
    if layout_name == RING_LAYOUT:
        return place_depots_on_ring(centre, RING_RADIUS_M, NUMBER_OF_STYLISED_DEPOTS)
    if layout_name == POPULATION_KMEANS_LAYOUT:
        return cluster_population_weighted_centres(
            grid.centroid_eastings, grid.centroid_northings, cell_table.population, NUMBER_OF_STYLISED_DEPOTS, KMEANS_SEED
        )
    if layout_name in RANDOM_DRAW_LAYOUTS:
        return sample_uniform_depots(boundary, NUMBER_OF_STYLISED_DEPOTS, seed=RANDOM_DRAW_LAYOUTS.index(layout_name) + 1)

    raise ValueError(f"Unknown depot layout: {layout_name}")


def round_like_order_coordinates(depot: Coordinate) -> Coordinate:
    return Coordinate(
        northing=round(depot.northing, COORDINATE_DECIMALS), easting=round(depot.easting, COORDINATE_DECIMALS)
    )


@lru_cache(maxsize=None)
def resolve_depot_layout(layout_name: str) -> dict[str, Coordinate]:
    """Depot name -> location. Stylised depots are named after their layout and position in it."""
    if layout_name == ACTUAL_LAYOUT:
        return dict(model_config.warehouses.bng_coordinates)

    centre, boundary = load_population_centre(), load_study_boundary()
    depots = [
        round_like_order_coordinates(snap_inside_boundary(depot, centre, boundary, BOUNDARY_INSET_M))
        for depot in build_stylised_depots(layout_name)
    ]
    return {f"{layout_name}_{position:02d}": depot for position, depot in enumerate(depots, start=1)}
