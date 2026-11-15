from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

import pandas as pd
from tqdm import tqdm

from census_analysis.msoa_cache import CachedMSOA
from census_analysis.msoa_data import load_msoa_data
from census_analysis.population_data_processor.cell_matrix_population_calculator import (
    split_group_counts_by_overlapping_area,
)
from common.enum import BoundaryDatum
from noise.grid_generator import PUBLISHED_BOUNDARY_DATUM, get_valid_cells


def calculate_cell_matrix_property(cells, cell_process_method):
    results = []

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(cell_process_method, cell): cell for cell in cells}
        for future in tqdm(as_completed(futures), total=len(cells), desc="Processing cells"):
            results.append(future.result())

    return pd.DataFrame(results)


def _bbox_overlap(box_1, box_2):
    minx1, miny1, maxx1, maxy1 = box_1
    minx2, miny2, maxx2, maxy2 = box_2
    return (minx1 <= maxx2) and (maxx1 >= minx2) and (miny1 <= maxy2) and (maxy1 >= miny2)


def calculate_cell_property(area_geom, msoa_cache: CachedMSOA) -> Dict[int, float]:
    totals = {c: 0.0 for c in msoa_cache.codes}
    area_bounds = area_geom.bounds

    for msoa_code, polygon in msoa_cache.polygons.items():
        if not _bbox_overlap(area_bounds, msoa_cache.bounds[msoa_code]):
            continue

        intersection = area_geom.intersection(polygon)
        if intersection.is_empty:
            continue

        msoa_area = msoa_cache.areas[msoa_code]
        intersection_fraction = intersection.area / msoa_area
        if intersection_fraction <= 0:
            continue

        counts = msoa_cache.counts.get(msoa_code)

        for code, value in counts.items():
            if value:
                totals[code] += value * intersection_fraction

    return totals


def calculate_cell_matrix_groups(
        group_pivot: pd.DataFrame, cell_size: int, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM
) -> pd.DataFrame:
    """Residents of every cell by group, for a table of group counts per MSOA (rows) and group code (columns).

    All cells are split in one pass over a spatial index; the cell-by-cell calculation above gives the same
    values but takes hours on a fine grid.
    """
    msoa_index = load_msoa_data().msoa_index
    msoa_codes = [msoa_code for msoa_code in group_pivot.index if msoa_code in msoa_index]
    cells = get_valid_cells(cell_size, boundary_datum)

    cell_group_counts = split_group_counts_by_overlapping_area(
        [cell["geometry"] for cell in cells], [msoa_index[msoa_code] for msoa_code in msoa_codes],
        group_pivot.loc[msoa_codes].to_numpy(dtype=float),
    )
    cell_matrix = pd.DataFrame(cells)
    for position, group_code in enumerate(group_pivot.columns):
        cell_matrix[int(group_code)] = cell_group_counts[:, position]
    return cell_matrix
