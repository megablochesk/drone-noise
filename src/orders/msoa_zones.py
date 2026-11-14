from census_analysis.msoa_data import load_msoa_data
from orders.seeded_order_pool import DemandZone


def load_population_zones() -> list[DemandZone]:
    """One demand zone per MSOA, weighted by its census population."""
    return [
        DemandZone(code=msoa_code, polygon=load_msoa_data().msoa_index[msoa_code], weight=population)
        for msoa_code, population in load_msoa_data().msoa_populations.items()
    ]
