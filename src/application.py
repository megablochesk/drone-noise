from experiments.simulation_based_experiments.avg_noise_impact_by_stocking_experiment import \
    run_avg_noise_for_different_stocking_experiment
from experiments.simulation_based_experiments.drone_landing_experiment import run_drone_landing_experiment
from experiments.simulation_based_experiments.drone_number_change_experiment import run_drone_number_change_experiment
from experiments.simulation_based_experiments.navigation_type_change_experiment import \
    run_navigation_type_change_experiment
from experiments.simulation_based_experiments.simple_experiment import run_standard_experiment

if __name__ == '__main__':
    load_results_from_saved_file = True

    #compute_and_visualise_population_data()

    #run_standard_experiment(load_results_from_saved_file)

    #run_drone_number_change_experiment(load_results_from_saved_file)

    #run_drone_landing_experiment(load_results_from_saved_file)

    run_avg_noise_for_different_stocking_experiment(load_results_from_saved_file)

    #run_navigation_type_change_experiment(load_results_from_saved_file)

    #run_mixed_random_and_best_stocking_experiment()
    #generate_mixed_stocking_datasets(100_000)
