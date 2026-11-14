from census_analysis.cell_matrix_calculator_utils import calculate_cell_matrix_property
from census_analysis.msoa_data import load_msoa_data
from noise.grid_generator import get_valid_cells


def calculate_cell_matrix_population():
	cells = get_valid_cells()

	def process_cell(cell):
		cell["population"] = _calculate_population_in_area(cell["geometry"])
		return cell

	return calculate_cell_matrix_property(cells, process_cell)


def _calculate_population_in_area(area):
	total_population = 0

	for msoa_code, polygon in load_msoa_data().msoa_index.items():
		intersection = area.intersection(polygon)
		if not intersection.is_empty:
			total_population += load_msoa_data().msoa_populations[msoa_code] * (intersection.area / polygon.area)

	return total_population
