import matplotlib

from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS
from visualiser.barchart import plot_barchart_stats, plot_combined_bars
from visualiser.statistics import plot_dataset_stat_difference

matplotlib.use(PATH_CONFIGS.matplotlib_backend)


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


def plot_comparison_avg_noise_barchart(results_df):
    plot_combined_bars(
        results_df,
        value_column="avg_noise_diff",
        xlabel="Number of Drones",
        ylabel="Average Noise Difference (dB)",
        title="Normal vs Routed — Average Noise",
        filename='avg_noise_diff_comp',
        decimal_places=2
    )


def plot_comparison_orders_barchart(results_df):
    plot_combined_bars(
        results_df,
        value_column="delivered_orders_number",
        xlabel="Number of Drones",
        ylabel="Delivered Orders",
        title="Normal vs Routed — Delivered Orders",
        filename='orders_number_comp'
    )


def plot_comparison_execution_time_barchart(results_df):
    plot_combined_bars(
        results_df,
        value_column="execution_time_seconds",
        xlabel="Number of Drones",
        ylabel="Execution Time (s)",
        title="Normal vs Routed — Execution Time",
        filename='exec_time_comp'
    )


def plot_delivered_orders_comparison(results_df):
    plot_dataset_stat_difference(
        results_df,
        value_col="delivered_orders_number",
        title="Average Order Number Difference to Normal",
        ylabel="% of order number compared to Normal",
        filename='del_orders_comp_stat'
    )


def plot_avg_noise_diff_comparison(results_df):
    plot_dataset_stat_difference(
        results_df,
        value_col="avg_noise_diff",
        ylabel="% of average noise difference compared to Normal",
        title="Average Noise Difference: Normal vs Routed",
        filename='avg_noise_diff_comp_stat'
    )
