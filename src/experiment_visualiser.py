from common.file_utils import load_dataframe_from_pickle
from stats.experiments import unlimited_orders_limited_time_experiment
from stats.plotter import (
    plot_show, plot_avg_noise_barchart, plot_delivered_orders_barchart,
    plot_delivered_orders_linegraph, plot_avg_noise_linegraph, analyze_and_plot_noise_increase,
    analyze_and_plot_population_impact, plot_cell_population, plot_cells_impacted_by_noise
)
from stats.cell_population_calculator import calculate_cell_matrix_population

FROM_FILE = True

if __name__ == '__main__':
    results_file = "results 72000 6.pkl"

    if FROM_FILE:
        experiment_results = load_dataframe_from_pickle(results_file)
    else:
        experiment_results = unlimited_orders_limited_time_experiment(results_file)

    # plot_cells_impacted_by_noise(experiment_results, 55)

    # fig1 = plot_avg_noise_barchart(experiment_results)
    # fig2 = plot_delivered_orders_barchart(experiment_results)

    # fig3 = plot_delivered_orders_linegraph(experiment_results)
    # fig4 = plot_avg_noise_linegraph(experiment_results)

    # figs = [analyze_and_plot_noise_increase(experiment_results, db) for db in range(55, 65, 5)]

    # figs2 = [analyze_and_plot_population_impact(experiment_results, db) for db in range(45, 65, 5)]

    # plot_cell_population()

    plot_show()
