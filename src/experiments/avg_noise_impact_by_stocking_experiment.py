from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from common.file_utils import save_dataframe_to_pickle
from experiments.simulation_based_experiment_utils import (
    process_all_datasets, convert_results_to_dataframe, run_complex_experiment
)
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison

ORDER_DATASETS = {
    'closest': ORDER_BASE_PATH_CLOSEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'furthest': ORDER_BASE_PATH_FURTHEST
}

NUMBER_OF_DRONES = 100
NUMBER_OF_ORDERS = 100000


def unlimited_orders_limited_time_experiment(results_path):
    datasets = ORDER_DATASETS.items()
    results = process_all_datasets(datasets, NUMBER_OF_ORDERS, NUMBER_OF_DRONES)

    results_df = convert_results_to_dataframe(results)

    save_dataframe_to_pickle(results_df, results_path)

    return results_df


def plot_noise_comparison_for_different_stocking(results_df):
    dataframes = [row['noise_impact_df'] for _, row in results_df.iterrows()]

    plot_noise_level_comparison(
        dataframes,
        metrics=['average_noise', 'average_noise', 'average_noise'],
        titles=['Best Stocking', 'Random Stocking', 'Worst Stocking'],
        file_name='noise_maps',
        vmin=15,
        vmax=45)


def run_avg_noise_for_different_stocking_experiment():
    results_file = "noise_maps_df_1.pkl"
    from_file = True

    run_complex_experiment(
        results_file,
        from_file,
        run_avg_noise_for_different_stocking_experiment,
        plot_noise_comparison_for_different_stocking
    )
