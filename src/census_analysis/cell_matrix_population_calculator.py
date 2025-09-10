from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

from census_analysis.msoa_data import MSOA_DATA
from common.file_utils import save_dataframe_to_pickle
from noise.grid_generator import get_valid_cells


def calculate_population_in_area(area):
	total_population = 0

	for msoa_code, polygon in MSOA_DATA.msoa_index.items():
		intersection = area.intersection(polygon)
		if not intersection.is_empty:
			total_population += MSOA_DATA.msoa_populations[msoa_code] * (intersection.area / polygon.area)

	return total_population


def calculate_cell_matrix_population():
	cells = get_valid_cells()

	def process_cell(cell):
		cell["population"] = calculate_population_in_area(cell["geometry"])
		return cell

	cell_population_list = []
	with ThreadPoolExecutor() as executor:
		futures = {executor.submit(process_cell, cell): cell for cell in cells}
		for future in tqdm(as_completed(futures), total=len(cells), desc="Processing cells"):
			cell_population_list.append(future.result())

	cell_population_df = pd.DataFrame(cell_population_list)
	save_dataframe_to_pickle(cell_population_df, 'cell_population.pkl')
