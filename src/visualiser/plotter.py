import matplotlib
from common.configuration import NUMBER_OF_HOURS
from visualiser.analysis import (
    analyze_and_plot_noise_increase,
    analyze_and_plot_population_impact,
    calculate_noise_increase_cells,
    plot_cell_population,
    plot_cells_impacted_by_noise,
)
from visualiser.barchart import plot_barchart_stats
from visualiser.linegraph import plot_linegraph

matplotlib.use('Qt5Agg')


def plot_avg_noise_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column="avg_noise_diff",
        xlabel="Number of Drones",
        ylabel="Average Noise Increase (dB)",
        # title='Average Noise Difference by Drone Number and Dataset',
        filename="del_noise",
    )


def plot_avg_noise_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column="avg_noise_diff",
        xlabel="Number of Drones",
        ylabel="Average Noise Difference, dBs",
        # title='Average Noise Difference by Drone Number and Dataset'
    )


def plot_delivered_orders_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column="delivered_orders_number",
        xlabel="Number of Drones",
        ylabel=f"Number of Orders Delivered in {NUMBER_OF_HOURS} Hours",
        # title='Delivered Orders by Drone Number and Dataset',
        filename="del_orders",
    )


def plot_delivered_orders_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column="delivered_orders_number",
        xlabel="Number of Drones",
        ylabel=f"Number of Orders Delivered in {NUMBER_OF_HOURS} Hours",
        # title='Delivered Orders by Drone Number and Dataset'
    )


def plot_execution_time_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column="execution_time_seconds",
        xlabel="Number of Drones",
        ylabel="Execution Time, seconds",
        filename="exec_time",
        decimal_places=2,
    )
