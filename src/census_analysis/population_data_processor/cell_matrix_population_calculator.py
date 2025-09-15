from census_analysis.cell_matrix_calculator_utils import calculate_cell_matrix_property
from census_analysis.msoa_data import MSOA_DATA
from common.file_utils import save_dataframe_to_pickle
from common.path_configs import CELL_POPULATION_PATH
from noise.grid_generator import get_valid_cells


def calculate_cell_matrix_population():
	cells = get_valid_cells()

	def process_cell(cell):
		cell["population"] = _calculate_population_in_area(cell["geometry"])
		return cell

	cell_population_df = calculate_cell_matrix_property(cells, process_cell)

	save_dataframe_to_pickle(cell_population_df, CELL_POPULATION_PATH)


def _calculate_population_in_area(area):
	total_population = 0

	for msoa_code, polygon in MSOA_DATA.msoa_index.items():
		intersection = area.intersection(polygon)
		if not intersection.is_empty:
			total_population += MSOA_DATA.msoa_populations[msoa_code] * (intersection.area / polygon.area)

	return total_population
