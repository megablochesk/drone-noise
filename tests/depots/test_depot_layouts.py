from common.model_configs import model_config
from depots.depot_layouts import ACTUAL_LAYOUT, resolve_depot_layout


def test_actual_layout_is_the_published_set_of_fourteen_sites():
    """Published configuration: the 14 named sites of `Warehouses.london_default`."""
    depots = resolve_depot_layout(ACTUAL_LAYOUT)
    assert len(depots) == 14
    assert depots == model_config.warehouses.bng_coordinates
