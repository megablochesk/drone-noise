from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

from common.file_utils import save_dataframe_to_pickle, load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH
from noise.grid_generator import get_valid_cells
from orders.order_generator import MSOA_INDEX, MSOA_POPULATIONS

CELL_POPULATION = load_dataframe_from_pickle(CELL_POPULATION_PATH)


def calculate_population_in_area(area):
	total_population = 0

	for msoa_code, polygon in MSOA_INDEX.items():
		intersection = area.intersection(polygon)
		if not intersection.is_empty:
			total_population += MSOA_POPULATIONS[msoa_code] * (intersection.area / polygon.area)

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


def get_cell_population(row, col):
	cell = CELL_POPULATION[(CELL_POPULATION['row'] == row) & (CELL_POPULATION['col'] == col)]
	return cell['population'].values[0] if not cell.empty else 0


def calculate_population_impacted_by_noise(main_df, threshold=55):
	rows = []
	for _, row in main_df.iterrows():
		noise_impact = row['noise_impact_df']
		total_population_impacted = 0

		for _, cell in noise_impact.iterrows():
			if cell['combined_noise'] > threshold > cell['noise_level']:
				total_population_impacted += get_cell_population(cell['row'], cell['col'])

		rows.append({
			'dataset_name': row['dataset_name'],
			'num_drones': row['num_drones'],
			'impacted_population': total_population_impacted
		})

	return pd.DataFrame(rows)


def get_cells_impacted_by_noise(main_df, threshold=55):
	impacted_cells = []

	for _, row in main_df.iterrows():
		noise_impact = row['noise_impact_df']

		for _, cell in noise_impact.iterrows():
			if cell['combined_noise'] > threshold > cell['noise_level']:
				impacted_cells.append({
					'dataset_name': row['dataset_name'],
					'num_drones': row['num_drones'],
					'row': cell['row'],
					'col': cell['col'],
					'population': get_cell_population(cell['row'], cell['col'])
				})

	df = pd.DataFrame(impacted_cells)

	if not df.empty:
		df = df.groupby(['dataset_name', 'num_drones', 'row', 'col'], as_index=False).sum()

	return df
