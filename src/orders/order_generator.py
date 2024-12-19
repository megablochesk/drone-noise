import pandas as pd
from common.configuration import NEW_ORDER_BASE_PATH
from common.coordinate import Coordinate
from orders.order import Order


class OrderGenerator:
    @staticmethod
    def load_orders(number_of_orders):
        print(f"Loading orders data from {NEW_ORDER_BASE_PATH}")
        order_df = pd.read_csv(NEW_ORDER_BASE_PATH)

        print("Initializing orders from local data...")
        limited_df = order_df.head(number_of_orders)

        orders = [
            Order(
                order_id=row['Order ID'],
                start_location=Coordinate(row['Start Latitude'], row['Start Longitude']),
                end_location=Coordinate(row['End Latitude'], row['End Longitude'])
            )
            for _, row in limited_df.iterrows()
        ]

        print("Done initializing orders")

        return orders
