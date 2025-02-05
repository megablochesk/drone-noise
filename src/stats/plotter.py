import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns

from common.configuration import NUMBER_OF_HOURS
from stats.cell_population_calculator import (
	calculate_population_impacted_by_noise, CELL_POPULATION, get_cells_impacted_by_noise
)

matplotlib.use('Qt5Agg')


DATASET_TYPE_BAR_ORDER = ['closest', 'furthest', 'random']


def get_color_map(dataset_types):
    cmap = plt.get_cmap('tab10')
    return {ds: cmap(i) for i, ds in enumerate(dataset_types)}


def extract_sorted_values(results_df, dataset_types, num_drones, value_column):
    ds_values = []

    for ds in DATASET_TYPE_BAR_ORDER:
        if ds in dataset_types:
            row = results_df[(results_df['dataset_name'] == ds) & (results_df['num_drones'] == num_drones)]
            value = row.iloc[0][value_column] if not row.empty else 0
            ds_values.append((ds, value))

    return ds_values


def annotate_bargraph_data_points(ax, bar, value):
    ax.annotate(f'{value:.2f}' if isinstance(value, float) else f'{int(value)}',
                xy=(bar[0].get_x() + bar[0].get_width() / 2, value),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=10)


def plot_barchart(results_df, value_column, ylabel, title):
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df['dataset_name'].unique()]
    num_drones_list = sorted(results_df['num_drones'].unique())

    x = np.arange(len(num_drones_list))
    width = 0.2
    color_map = get_color_map(dataset_types)

    fig, ax = plt.subplots(figsize=(10, 6))
    added_labels = set()

    for i, num_drones in enumerate(num_drones_list):
        ds_values = extract_sorted_values(results_df, dataset_types, num_drones, value_column)
        num_datasets = len(ds_values)

        for j, (ds, value) in enumerate(ds_values):
            bar_position = x[i] - width * (num_datasets - 1) / 2 + j * width
            label = ds if ds not in added_labels else ""
            if ds not in added_labels:
                added_labels.add(ds)

            bar = ax.bar(bar_position, value, width, color=color_map[ds], label=label)
            annotate_bargraph_data_points(ax, bar, value)

    ax.set_xticks(x)
    ax.set_xticklabels(num_drones_list)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


def annotate_linegraph_data_points(ax, x, y):
    for xi, yi in zip(x, y):
        annotation = f'{yi:.2f}' if isinstance(yi, float) else f'{yi}'
        ax.annotate(annotation,
                    xy=(xi, yi),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=10)


def plot_linegraph(results_df, value_column, ylabel, title):
    dataset_types = [ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df['dataset_name'].unique()]
    color_map = get_color_map(dataset_types)

    fig, ax = plt.subplots(figsize=(10, 6))

    for dataset in dataset_types:
        df_ds = results_df[results_df['dataset_name'] == dataset].sort_values(by='num_drones')
        x = df_ds['num_drones'].values
        y = df_ds[value_column].values

        ax.plot(x, y, marker='o', color=color_map[dataset], label=dataset)

        annotate_linegraph_data_points(ax, x, y)

    ax.set_xlabel('Number of Drones')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title='Dataset Type')
    fig.tight_layout()

    return fig


def plot_avg_noise_barchart(results_df):
    return plot_barchart(
        results_df,
        value_column='avg_noise_diff',
        ylabel='Average Noise Difference (dBs)',
        title='Average Noise Difference by Drone Number and Dataset'
    )


def plot_avg_noise_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column='avg_noise_diff',
        ylabel='Average Noise Difference (dBs)',
        title='Average Noise Difference by Drone Number and Dataset'
    )


def plot_delivered_orders_barchart(results_df):
    return plot_barchart(
        results_df,
        value_column='delivered_orders_number',
        ylabel=f'Number of Delivered Orders per {NUMBER_OF_HOURS} Hours',
        title='Delivered Orders by Drone Number and Dataset'
    )


def plot_delivered_orders_linegraph(results_df):
    return plot_linegraph(
        results_df,
        value_column='delivered_orders_number',
        ylabel=f'Number of Delivered Orders per {NUMBER_OF_HOURS} Hours',
        title='Delivered Orders by Drone Number and Dataset'
    )


def calculate_noise_increase_cells(main_df, threshold=55):
    rows = []
    for _, row in main_df.iterrows():
        noise_impact = row['noise_impact_df']

        count = ((noise_impact['combined_noise'] > threshold) & (noise_impact['noise_level'] < threshold)).sum()
        rows.append({
            'dataset_name': row['dataset_name'],
            'num_drones': row['num_drones'],
            'cells_exceeding_threshold': count
        })
    return pd.DataFrame(rows)


def analyze_and_plot_noise_increase(main_df, threshold=55):
    summary_df = calculate_noise_increase_cells(main_df, threshold)
    return plot_barchart(
        summary_df,
        value_column='cells_exceeding_threshold',
        ylabel='Number of Cells',
        title=f'Cells with Combined Noise > {threshold} dB (Impact of Drone Deliveries)'
    )


def analyze_and_plot_population_impact(main_df, threshold=55):
    summary_df = calculate_population_impacted_by_noise(main_df, threshold)
    return plot_barchart(
        summary_df,
        value_column='impacted_population',
        ylabel='Impacted Population',
        title=f'Population Affected by Combined Noise > {threshold} dB (Impact of Drone Deliveries)'
    )


def plot_cell_population():
    df = CELL_POPULATION

    heatmap_data = df.pivot(index="row", columns="col", values="population")

    plt.figure(figsize=(8, 6))
    sns.heatmap(heatmap_data, cmap="viridis", annot=False, cbar=True)
    plt.title("Population Heatmap")
    plt.xlabel("Column")
    plt.ylabel("Row")
    plt.gca().invert_yaxis()


NUM_ROWS = 87
NUM_COLS = 112


def create_heatmap_matrix(group_df):
    heatmap_data = group_df.pivot(index="row", columns="col", values="population")

    row_range = np.arange(NUM_ROWS)
    col_range = np.arange(NUM_COLS)
    heatmap_data = heatmap_data.reindex(index=row_range, columns=col_range)

    return heatmap_data


def plot_cells_impacted_by_noise(main_df, threshold=55):
    df = get_cells_impacted_by_noise(main_df, threshold)

    for (dataset_name, num_drones), group_df in df.groupby(['dataset_name', 'num_drones']):
        heatmap_data = create_heatmap_matrix(group_df)

        plot_heatmap(heatmap_data, dataset_name, num_drones)


def plot_heatmap(heatmap_data, dataset_name, num_drones):
    plt.figure(figsize=(8, 6))

    plt.imshow(
        heatmap_data,
        cmap="viridis",
        interpolation="nearest",
        origin='lower',
        aspect="auto"
    )

    cbar = plt.colorbar()
    cbar.set_label("Population", rotation=270, labelpad=15)

    plt.title(f"Population Heatmap {dataset_name} with {num_drones} drones")
    plt.xlabel("Column")
    plt.ylabel("Row")
    plt.grid(visible=False)


def plot_show():
    plt.show()
