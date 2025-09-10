import pandas as pd

from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH

CELL_POPULATION = load_dataframe_from_pickle(CELL_POPULATION_PATH)


def calculate_noise_increase_cells(main_df, threshold: int = 55) -> pd.DataFrame:
	rows = []
	for _, row in main_df.iterrows():
		noise_impact = row["noise_impact_df"]
		impacted_cells_number = ((
				(noise_impact["combined_noise"] > threshold) &
				(noise_impact["noise_level"] < threshold))
				.sum())

		rows.append({
			"dataset": row["dataset"],
			"dataset_name": row["dataset_name"],
			"num_drones": row["num_drones"],
			"navigation_type": row["navigation_type"],
			"cells_exceeding_threshold": impacted_cells_number
		})

	return pd.DataFrame(rows)


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
			"dataset": row["dataset"],
			'dataset_name': row['dataset_name'],
			'num_drones': row['num_drones'],
			"navigation_type": row["navigation_type"],
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
