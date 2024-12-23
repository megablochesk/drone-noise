import pandas as pd
from common.configuration import ORDER_BASE_PATH
from common.coordinate import Coordinate
from orders.order import Order


class OrderGenerator:
    @staticmethod
    def load_orders(number_of_orders):
        print(f"Loading orders data from {ORDER_BASE_PATH}")
        order_df = pd.read_csv(ORDER_BASE_PATH)

        print("Initializing orders from local data...")
        limited_df = order_df.head(number_of_orders)

        orders = [
            Order(
                order_id=int(row['Order ID']),
                start_location=Coordinate(row['Start Northing'], row['Start Easting']),
                end_location=Coordinate(row['End Northing'], row['End Easting'])
            )
            for _, row in limited_df.iterrows()
        ]

        print("Done initializing orders")

        return orders
