from common.path_configs import get_mixed_order_dataset_pattern
from experiments.config_generator import generate_configs_for_datasets
from experiments.experiment_executor import run_complex_experiment
from visualiser.paper_experiment_figures import draw_mixed_stocking_noise_maps

NUMBER_OF_ORDERS_IN_DATASETS = 100_000
NUMBER_OF_ORDERS_TO_PROCESS = 100_000
NUMBER_OF_DRONES = 500

ORDER_DATASETS = {
    f'r{random_ratio}_c{closest_ratio}': get_mixed_order_dataset_pattern(random_ratio, closest_ratio, NUMBER_OF_ORDERS_IN_DATASETS)
    for random_ratio, closest_ratio in [(ratio, 100 - ratio) for ratio in range(100, 0, -10)]
}


def generate_configs():
    return generate_configs_for_datasets(
        ORDER_DATASETS,
        NUMBER_OF_ORDERS_TO_PROCESS,
        NUMBER_OF_DRONES
    )


def run_mixed_random_and_best_stocking_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="mixed_random_and_best_stocking",
        configs_with_names=generate_configs(),
        visualisation_function=draw_mixed_stocking_noise_maps,
    )
