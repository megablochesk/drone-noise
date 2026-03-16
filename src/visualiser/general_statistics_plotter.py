import matplotlib

from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS
from visualiser.linegraph import plot_linegraph_stats

matplotlib.use(PATH_CONFIGS.matplotlib_backend)


def plot_avg_noise_linegraph(results_df, filename="del_noise"):
    return plot_linegraph_stats(
        results_df,
        value_column='avg_noise_diff',
        xlabel='Number of Drones',
        ylabel='Average Noise Increase (dB)',
        filename=filename
    )


def plot_delivered_orders_linegraph(results_df, filename="del_orders"):
    return plot_linegraph_stats(
        results_df,
        value_column='delivered_orders_number',
        xlabel='Number of Drones',
        ylabel=f'Number of Orders Delivered in {model_config.time.hours} Hours',
        filename=filename
    )


def plot_execution_time_linegraph(results_df):
    return plot_linegraph_stats(
        results_df,
        value_column='execution_time_seconds',
        xlabel='Number of Drones',
        ylabel='Execution Time, seconds',
        filename='exec_time',
    )
