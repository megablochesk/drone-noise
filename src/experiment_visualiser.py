from common.file_utils import load_dataframe_from_pickle
from stats.experiments import unlimited_orders_limited_time_experiment
from stats.plotter import (
    plot_avg_noise_barchart, plot_delivered_orders_barchart,
    plot_delivered_orders_linegraph, plot_avg_noise_linegraph, analyze_and_plot_noise_increase,
    analyze_and_plot_population_impact, plot_cell_population, plot_cells_impacted_by_noise,
    plot_execution_time_barchart
)
from stats.statistics import plot_delivery_distance_statistics
from stats.cell_population_calculator import calculate_cell_matrix_population
from stats.plot_utils import save_figures, plot_figures, add_font_style

FROM_FILE = True

if __name__ == '__main__':
    results_file = "results 72000 8.pkl"

    if FROM_FILE:
        experiment_results = load_dataframe_from_pickle(results_file)
    else:
        experiment_results = unlimited_orders_limited_time_experiment(results_file)

    add_font_style()
    # plot_cells_impacted_by_noise(experiment_results, 55)

    # exec = plot_execution_time_barchart(experiment_results)

    #fig1 = plot_avg_noise_barchart(experiment_results)
    fig2 = plot_delivered_orders_barchart(experiment_results)

    #figs = [analyze_and_plot_noise_increase(experiment_results, db) for db in range(55, 60, 5)]

    # figs2 = [analyze_and_plot_population_impact(experiment_results, db) for db in range(55, 60, 5)]

    #plot_cell_population()
    #plot_delivery_distance_statistics()

    save_figures()

    plot_figures()
