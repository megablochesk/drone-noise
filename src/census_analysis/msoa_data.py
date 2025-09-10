from shapely.geometry import shape

from common.file_utils import load_json
from common.path_configs import PATH_CONFIGS

MSOA_DATASET_PATH = PATH_CONFIGS.msoa_population_path


class MSOAData:
    def __init__(self):
        self.msoa_index, self.msoa_populations = self._build_msoa_index()
        self.population_distribution = self._calculate_population_distribution()

    @staticmethod
    def _build_msoa_index(msoa_dataset_path=MSOA_DATASET_PATH):
        geojson_data = load_json(msoa_dataset_path)

        msoa_dict = {}
        msoa_populations = {}

        for feature in geojson_data['features']:
            msoa_code = feature['properties'].get('msoa21cd', '').strip()
            population = feature['properties'].get('population', None)

            polygon = shape(feature['geometry'])

            if population is not None:
                msoa_dict[msoa_code] = polygon
                msoa_populations[msoa_code] = population

        return msoa_dict, msoa_populations

    def _calculate_population_distribution(self):
        total_population = sum(self.msoa_populations.values())
        if total_population == 0:
            raise ValueError("Total population is zero, cannot generate weighted points.")

        cumulative = 0.0
        distribution = []
        for msoa_code, msoa_population in self.msoa_populations.items():
            cumulative += msoa_population / total_population
            distribution.append((msoa_code, cumulative))
        return distribution


MSOA_DATA = MSOAData()
