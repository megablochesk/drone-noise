import matplotlib

from common.configuration import MATPLOTLIB_BACKEND
from common.configuration import NUMBER_OF_HOURS
from visualiser.barchart import plot_barchart_stats

matplotlib.use(MATPLOTLIB_BACKEND)


def plot_avg_noise_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column='avg_noise_diff',
        xlabel='Number of Drones',
        ylabel='Average Noise Increase (dB)',
        # title='Average Noise Difference by Drone Number and Dataset',
        filename='del_noise'
    )


def plot_delivered_orders_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column='delivered_orders_number',
        xlabel='Number of Drones',
        ylabel=f'Number of Orders Delivered in {NUMBER_OF_HOURS} Hours',
        # title='Delivered Orders by Drone Number and Dataset',
        filename='del_orders'
    )


def plot_execution_time_barchart(results_df):
    return plot_barchart_stats(
        results_df,
        value_column='execution_time_seconds',
        xlabel='Number of Drones',
        ylabel='Execution Time, seconds',
        filename='exec_time',
        decimal_places=2
    )
