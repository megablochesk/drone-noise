from orders.order_generator import generate_mixed_stocking_datasets
from experiments.drone_noise_from_mixed_stocking_experiment import run_mixed_random_and_best_stocking_experiment
from experiments.drone_number_change_experiment import run_drone_number_change_experiment
from experiments.avg_noise_impact_by_stocking_experiment import run_avg_noise_for_different_stocking_experiment
from experiments.simple_experiment import run_standard_experiment


if __name__ == '__main__':
    run_standard_experiment()

    #run_avg_noise_for_different_stocking_experiment()
    #run_mixed_random_and_best_stocking_experiment()
    #run_drone_number_change_experiment()

    # generate_mixed_stocking_datasets(100_000)
