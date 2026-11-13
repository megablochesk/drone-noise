from common.coordinate import Coordinate
from common.model_configs import model_config

ACTUAL_LAYOUT = "actual"


def resolve_depot_layout(layout_name: str) -> dict[str, Coordinate]:
    if layout_name == ACTUAL_LAYOUT:
        return dict(model_config.warehouses.bng_coordinates)

    raise ValueError(f"Unknown depot layout: {layout_name}")
