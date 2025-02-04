from common.file_utils import load_dataframe_from_pickle
from stats.experiments import unlimited_orders_limited_time_experiment
from stats.plotter import (
    plot_show, plot_avg_noise_barchart, plot_delivered_orders_barchart,
    plot_delivered_orders_linegraph, plot_avg_noise_linegraph, analyze_and_plot_noise_increase
)

FROM_FILE = True

if __name__ == '__main__':
    results_file = "results 72000 5.pkl"

    if FROM_FILE:
        experiment_results = load_dataframe_from_pickle(results_file)
    else:
        experiment_results = unlimited_orders_limited_time_experiment(results_file)

    fig1 = plot_avg_noise_barchart(experiment_results)
    fig2 = plot_delivered_orders_barchart(experiment_results)

    fig3 = plot_delivered_orders_linegraph(experiment_results)
    fig4 = plot_avg_noise_linegraph(experiment_results)

    figs = [analyze_and_plot_noise_increase(experiment_results, db) for db in range(55, 65, 5)]

    plot_show()
