import numpy as np
import pandas as pd
import shapely
from shapely import STRtree

from census_analysis.msoa_data import load_msoa_data
from noise.grid_generator import CELL_SIZE, get_valid_cells


def calculate_overlap_areas(cells: np.ndarray, regions: np.ndarray) -> np.ndarray:
    """Area of each cell-region pair. A cell wholly inside its region needs no geometry; the others are cut
    out of the region with a rectangle clip, which is far cheaper than a general intersection."""
    shapely.prepare(regions)
    cell_is_inside = shapely.contains_properly(regions, cells)

    overlap_areas = shapely.area(cells)
    partial_pairs = np.flatnonzero(~cell_is_inside)
    clipped_regions = [
        shapely.clip_by_rect(region, *cell_bounds)
        for region, cell_bounds in zip(regions[partial_pairs], shapely.bounds(cells[partial_pairs]).tolist())
    ]
    overlap_areas[partial_pairs] = shapely.area(np.array(clipped_regions, dtype=object))
    return overlap_areas


def find_region_shares_in_cells(cell_geometries, region_polygons) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For every overlapping cell-region pair: the cell, the region, and the share of the region's area in the
    cell. A spatial index finds the pairs."""
    cells = np.array(cell_geometries, dtype=object)
    regions = np.array(region_polygons, dtype=object)
    region_indices, cell_indices = STRtree(cells).query(regions, predicate="intersects")

    overlap_areas = calculate_overlap_areas(cells[cell_indices], regions[region_indices])
    return cell_indices, region_indices, overlap_areas / shapely.area(regions)[region_indices]


def split_population_by_overlapping_area(cell_geometries, region_polygons, region_populations: np.ndarray) -> np.ndarray:
    """Population of every rectangular cell: each region's population times the share of the region's area
    inside the cell."""
    cell_indices, region_indices, region_shares = find_region_shares_in_cells(cell_geometries, region_polygons)
    return np.bincount(
        cell_indices, weights=region_populations[region_indices] * region_shares, minlength=len(cell_geometries)
    )


def split_group_counts_by_overlapping_area(cell_geometries, region_polygons, region_group_counts: np.ndarray) -> np.ndarray:
    """The same split for several groups at once: rows of the input are regions, rows of the result are cells."""
    cell_indices, region_indices, region_shares = find_region_shares_in_cells(cell_geometries, region_polygons)
    cell_group_counts = np.zeros((len(cell_geometries), region_group_counts.shape[1]))
    np.add.at(cell_group_counts, cell_indices, region_group_counts[region_indices] * region_shares[:, np.newaxis])
    return cell_group_counts


def calculate_cell_matrix_population(cell_size=CELL_SIZE):
    cells = get_valid_cells(cell_size)
    msoa_data = load_msoa_data()
    msoa_codes = list(msoa_data.msoa_index)

    cell_matrix = pd.DataFrame(cells)
    cell_matrix["population"] = split_population_by_overlapping_area(
        [cell["geometry"] for cell in cells],
        [msoa_data.msoa_index[msoa_code] for msoa_code in msoa_codes],
        np.array([msoa_data.msoa_populations[msoa_code] for msoa_code in msoa_codes], dtype=np.float64),
    )
    return cell_matrix
