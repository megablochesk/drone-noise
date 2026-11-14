"""Maps of the residents of each census group, one file per group under the published names."""
import matplotlib

matplotlib.use("Agg")

import pandas as pd

from census_analysis.census_data_heatmap_plotter import draw_group_population_maps, draw_population_map

GROUPS = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], 3: [1.0, 2.0, 3.0], 13: [9.0, 18.0, 27.0]})
GROUPS.attrs["ethnicity_code_to_name"] = {3: "Indian", 13: "British"}


def test_one_map_is_written_per_group_named_by_category_code_and_colour_range(tmp_path):
    draw_group_population_maps(GROUPS, "ethnicity", (0.0, 1000.0), tmp_path, "Population per cell")

    assert sorted(path.name for path in tmp_path.iterdir()) == ["ethnicity_13_0.0_1000.0.eps", "ethnicity_3_0.0_1000.0.eps"]


def test_population_map_is_written_as_population(tmp_path):
    population = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], "population": [10.0, 20.0, 30.0]})

    draw_population_map(population, tmp_path)

    assert [path.name for path in tmp_path.iterdir()] == ["population.eps"]
