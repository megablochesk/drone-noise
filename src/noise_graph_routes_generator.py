from pathlib import Path

from common.configuration import ORDER_FOLDER
from common.file_utils import save_data_as_pickle_highest_protocol
from noise.noise_graph_navigator import NoiseGraphNavigator
from orders.order_generator import load_orders

NUMBER_OF_ORDERS = -1  # all
NOISE_GRAPH_NAVIGATOR = NoiseGraphNavigator()


def get_list_of_csv_files():
    folder_path = Path(ORDER_FOLDER)

    if not folder_path.exists():
        raise FileNotFoundError(f"Order folder not found: {ORDER_FOLDER}")

    csv_files = tuple(f for f in folder_path.glob("*.csv"))

    if not csv_files:
        raise ValueError(f"No CSV files found in {ORDER_FOLDER}")

    return csv_files


def calculate_routes(orders):
    return [
        (order.start_location, order.end_location,
         NOISE_GRAPH_NAVIGATOR.get_optimal_route(order.start_location, order.end_location))
        for order in orders
    ]


def main():
    print(f"Starting order processing from folder: {ORDER_FOLDER}")

    csv_files = get_list_of_csv_files()

    for csv_file in csv_files:
        print(f"Processing {csv_file}")
        orders = load_orders(number_of_orders=NUMBER_OF_ORDERS, path=str(csv_file))

        routes = calculate_routes(orders)

        pickle_path = str(csv_file).replace('.csv', '_routes.pkl')
        save_data_as_pickle_highest_protocol(routes, pickle_path)


if __name__ == "__main__":
    main()
