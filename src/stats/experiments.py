import pandas as pd

from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from simulation.center import Center

ORDER_DATASETS = {
    'furthest': ORDER_BASE_PATH_FURTHEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'closest': ORDER_BASE_PATH_CLOSEST
}

NUMBER_OF_DRONES_CASES = [250, 500, 750, 1000, 1250]
NUMBER_OF_ORDERS = 100000


def unlimited_orders_limited_time_experiment(results_path):
    results = []
    for dataset_name, dataset_path in ORDER_DATASETS.items():

        for number_of_drones in NUMBER_OF_DRONES_CASES:
            print(dataset_name, number_of_drones, NUMBER_OF_ORDERS)

            center = Center(NUMBER_OF_ORDERS, number_of_drones, dataset_path)
            center.run_center()

            delivered_orders = center.get_delivered_orders_number()
            noise_impact_df = center.noise_impact

            avg_noise_diff = noise_impact_df['noise_difference'].mean()
            results.append({
                'dataset_name': dataset_name,
                'num_drones': number_of_drones,
                'num_orders': NUMBER_OF_ORDERS,
                'avg_noise_diff': avg_noise_diff,
                'noise_impact_df': noise_impact_df,
                'delivered_orders_number': delivered_orders
            })

    results_df = pd.DataFrame(results)

    save_dataframe_to_pickle(results_df, results_path)

    return results_df
