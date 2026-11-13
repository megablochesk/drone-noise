from common.coordinate import Coordinate
from common.file_utils import load_df_from_csv
from common.runtime_configs import get_simulation_config
from orders.order import Order


def load_orders(number_of_orders, path=None):
    if path is None:
        path = get_simulation_config().order_dataset_path

    limited_df = load_df_from_csv(path).head(number_of_orders)

    return [
        Order(
            order_id=order_id,
            start_location=Coordinate(start_northing, start_easting),
            end_location=Coordinate(end_northing, end_easting)
        )
        for order_id, start_northing, start_easting, end_northing, end_easting in zip(
            limited_df['Order ID'].tolist(),
            limited_df['Start Northing'].tolist(),
            limited_df['Start Easting'].tolist(),
            limited_df['End Northing'].tolist(),
            limited_df['End Easting'].tolist(),
        )
    ]
