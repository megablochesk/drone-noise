import matplotlib

from common.model_configs import model_config
from visualiser.barchart import plot_barchart_stats

matplotlib.use(model_config.paths.matplotlib_backend)


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
        ylabel=f'Number of Orders Delivered in {model_config.time.hours} Hours',
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
