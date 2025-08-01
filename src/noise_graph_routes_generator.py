from pathlib import Path

from common.configuration import ORDER_FOLDER
from common.file_utils import write_csv
from noise.noise_graph_navigator import NoiseGraphNavigator
from orders.order_generator import load_orders

NUMBER_OF_ORDERS = -1 # all
NOISE_GRAPH_NAVIGATOR = NoiseGraphNavigator()
CSV_ROUTE_FILE_HEADER = ['Order ID', 'Route']


def get_list_of_csv_files():
    folder_path = Path(ORDER_FOLDER)

    if not folder_path.exists():
        raise FileNotFoundError(f"Order folder not found: {ORDER_FOLDER}")

    csv_files = tuple(f for f in folder_path.glob("*.csv")
                      if not f.name.endswith('_routes.csv'))

    if not csv_files:
        raise ValueError(f"No CSV files found in {ORDER_FOLDER}")

    return csv_files

def calculate_routes(orders):
    routes = []

    for order in orders:
        route = NOISE_GRAPH_NAVIGATOR.get_optimal_route(order.start_location, order.end_location)

        routes.append((order.order_id, route))

    return routes


def main():
    print(f"Starting order processing from folder: {ORDER_FOLDER}")

    csv_files = get_list_of_csv_files()

    for csv_file in csv_files:
        print(f'Start processing {csv_file}')
        file_path = str(csv_file)

        orders = load_orders(number_of_orders=NUMBER_OF_ORDERS, path=file_path)

        routes = calculate_routes(orders)

        routes_file_path = file_path.replace('.csv', '_routes.csv')

        write_csv(
            routes_file_path,
            CSV_ROUTE_FILE_HEADER,
            routes
        )


if __name__ == "__main__":
    main()
