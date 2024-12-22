import csv
import sys

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import seaborn as sns
from folium.raster_layers import ImageOverlay
from matplotlib import pyplot as plt

from common.configuration import RESULT_BASE_PATH
from visual.visual import plot_histogram, plot_matrix
from visual.visual_configuration import (style_function, highlight_function, POPULATION_DENSITY_PATH, HARM_AVG_LEVEL,
                                         HARM_MAX_LEVEL, GEO_PATH, CRS)


def get_result_path(directory_path):
    """Get the result path from command-line arguments or default."""
    directory = directory_path
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    result_path = f'./{RESULT_BASE_PATH}/{directory}'
    return result_path


def read_data(result_path):
    """Read necessary data from CSV files."""
    matrix_df = pd.read_csv(f'{result_path}/matrix.csv')
    config_df = pd.read_csv(f'{result_path}/config.csv')
    drone_df = pd.read_csv(f'{result_path}/drone.csv')
    return matrix_df, config_df, drone_df


def generate_density_matrix_images(matrix_df, config_df, result_path):
    """Generate density matrix images."""
    config = config_df.iloc[0]
    rows = int(config['Rows'])
    cols = int(config['Cols'])

    la = np.linspace(config['Top Latitude'], config['Bottom Latitude'], rows)
    lo = np.linspace(config['Left Longitude'], config['Right Longitude'], cols)
    avg_noises = matrix_df['Average Noise'].to_numpy().reshape(rows, cols)
    max_noises = matrix_df['Maximum Noise'].to_numpy().reshape(rows, cols)

    std = np.std(avg_noises)
    iterations = int(matrix_df.iloc[0]['Time'])

    X, Y = np.meshgrid(lo, la)

    avg_title = f"Average regional noise in {iterations} iterations"
    max_title = f"Maximum regional noise in {iterations} iterations"

    plot_matrix(X, Y, avg_noises, avg_title, f'{result_path}/avg_matrix', color_min=25, color_max=60)
    plot_matrix(X, Y, max_noises, max_title, f'{result_path}/max_matrix', color_min=40, color_max=105)

    return avg_noises, max_noises, std, iterations, X, Y, rows, cols, config


def generate_harm_maps(avg_noises, max_noises, config, result_path, X, Y, rows, cols):
    """Generate harm maps and count harmful cells."""
    avg_noises_harm = np.array(avg_noises)
    max_noises_harm = np.array(max_noises)

    cnt_avg_harm_cell = 0
    cnt_max_harm_cell = 0
    cnt_100_harm_cell = 0

    for i in range(rows):
        for j in range(cols):
            if avg_noises_harm[i][j] - HARM_AVG_LEVEL >= 0:
                cnt_avg_harm_cell += 1
            else:
                avg_noises_harm[i][j] = 0
            if max_noises_harm[i][j] - HARM_MAX_LEVEL >= 0:
                cnt_max_harm_cell += 1
            else:
                max_noises_harm[i][j] = 0
            if max_noises_harm[i][j] >= 100:
                cnt_100_harm_cell += 1

    avg_harm_title = f"Average regional noise (>{HARM_AVG_LEVEL}db)"
    max_harm_title = f"Maximum regional noise (>{HARM_MAX_LEVEL}db)"

    plot_matrix(X, Y, avg_noises_harm, avg_harm_title, f'{result_path}/avg_harm_matrix', color_min=0, color_max=55)
    plot_matrix(X, Y, max_noises_harm, max_harm_title, f'{result_path}/max_harm_matrix', color_min=0, color_max=105)

    return cnt_avg_harm_cell, cnt_max_harm_cell, cnt_100_harm_cell


def print_harm_counts(cnt_avg_harm_cell, cnt_max_harm_cell, cnt_100_harm_cell, rows, cols):
    """Print the count of harmful cells."""
    total_cells = rows * cols

    print(
        f"Number of cells over avg harm threshold: {cnt_avg_harm_cell}, {round(cnt_avg_harm_cell / total_cells * 100, 3)}%")
    print(
        f"Number of cells over max harm threshold: {cnt_max_harm_cell}, {round(cnt_max_harm_cell / total_cells * 100, 3)}%")
    print(f"Number of cells over 100 db: {cnt_100_harm_cell}, {round(cnt_100_harm_cell / total_cells * 100, 3)}%")


def compute_simulation_time(drone_df):
    """Compute and print total simulation time."""
    avg_speed = 22  # 80km/h = 22m/s

    total_distance = drone_df['Total Distance'].sum()
    total_simulation_time = total_distance / avg_speed
    total_orders = drone_df['Total Orders'].sum()

    print(f"Total simulation time: {round(total_simulation_time)} seconds, to deliver {total_orders} orders")


def create_overlay_map(result_path, config):
    """Create and save an overlay map with folium."""
    geo = gpd.read_file(f'./{GEO_PATH}')
    pd_data = pd.read_csv(f'./{POPULATION_DENSITY_PATH}')
    popup = geo.merge(pd_data, left_on="id2", right_on="tract")

    threshold_scale = list(pd_data["Population_Density_in_2010"].quantile([0, 0.2, 0.4, 0.6, 0.8, 1]))
    x_center = geo.to_crs(CRS).centroid.to_crs(geo.crs).x.mean()
    y_center = geo.to_crs(CRS).centroid.to_crs(geo.crs).y.mean()

    mymap = folium.Map(location=[y_center, x_center], zoom_start=13)
    folium.Choropleth(
        geo_data=popup,
        name='Choropleth',
        data=pd_data,
        columns=['tract', 'Population_Density_in_2010'],
        key_on="properties.id2",
        fill_color='YlGnBu',
        fill_opacity=0.7,
        line_opacity=0.2,
        threshold_scale=threshold_scale,
        legend_name='Population Density (number of people per square mile)',
        smooth_factor=0
    ).add_to(mymap)

    NIL = folium.features.GeoJson(
        popup,
        style_function=style_function,
        control=False,
        highlight_function=highlight_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=['tract', 'Name', 'Population_Density_in_2010'],
            aliases=['Tract: ', 'Name: ', 'Population Density (people in per sq mi): '],
            style=("background-color: white; color: #333333; font-family: arial;"
                   " font-size: 12px; padding: 10px;")
        )
    )
    mymap.add_child(NIL)
    mymap.keep_in_front(NIL)

    max_img_path = f'{result_path}/max_matrix.png'
    avg_img_path = f'{result_path}/avg_matrix.png'
    avg_harm_img_path = f'{result_path}/avg_harm_matrix.png'
    max_harm_img_path = f'{result_path}/max_harm_matrix.png'
    overlay_bounds = [
        [config['Bottom Latitude'] * 0.9998 - 0.001, config['Left Longitude'] * 1.00018 - 0.006],
        [config['Top Latitude'] * 1.00025 - 0.001, config['Right Longitude'] * 0.99952 - 0.004]
    ]
    overlays = [
        (max_img_path, 'maximum', 1),
        (avg_img_path, 'average', 1),
        (avg_harm_img_path, 'average_harm', 0.8),
        (max_harm_img_path, 'maximum_harm', 0.8)
    ]
    for img_path, name, opacity in overlays:
        overlay = ImageOverlay(
            img_path,
            overlay_bounds,
            name=name,
            opacity=opacity
        )
        mymap.add_child(overlay)

    folium.LayerControl().add_to(mymap)
    html_path = f'{result_path}/overlay.html'
    mymap.save(html_path)


def generate_histograms(matrix_df, result_path):
    """Generate histograms for average and maximum noise."""
    sns.set_style('whitegrid')
    plt.ylim((0, 1000))
    plot_histogram(
        data=matrix_df['Average Noise'],
        title='Histogram of average regional noise',
        path=f'{result_path}/avg_histogram',
        y_bottom=0,
        y_top=1200,
        x_bottom=25,
        x_top=55
    )
    plt.ylim((0, 10000))
    plot_histogram(
        data=matrix_df['Maximum Noise'],
        title='Maximum',
        path=f'{result_path}/max_histogram',
        y_bottom=0,
        y_top=4000,
        x_bottom=30,
        x_top=75
    )


def compute_and_save_fairness_data(matrix_df, drone_df, config, iterations, std, result_path):
    """Compute and save fairness-related data to a CSV file."""
    total_drones = drone_df['Total Distance'].count()
    total_distance = drone_df['Total Distance'].sum()
    total_orders = drone_df['Total Orders'].sum()
    total_noise = matrix_df['Average Noise'].sum() * iterations
    avg_distance = total_distance / total_orders
    max_noise = matrix_df['Average Noise'].max()
    mean_noise = matrix_df['Average Noise'].mean()
    quantile_25_noise = matrix_df['Average Noise'].quantile(0.25)
    quantile_50_noise = matrix_df['Average Noise'].quantile(0.50)  # median
    quantile_75_noise = matrix_df['Average Noise'].quantile(0.75)

    fairness_fields = [
        'Total Drones', 'Total Orders', 'Total Distance', 'Total Noise',
        'Order Average Distance', 'std dev', 'Maximum Average Noise',
        'Mean Average Noise', '25% Quantiles', '50% Quantiles', '75% Quantiles', 'Priority'
    ]
    fairness_data = [[
        total_drones, total_orders, total_distance, total_noise,
        avg_distance, std, max_noise, mean_noise, quantile_25_noise,
        quantile_50_noise, quantile_75_noise, config['Prioritization K']
    ]]
    fairness_path = f'{result_path}/fairness.csv'
    with open(fairness_path, 'w', newline='') as f:
        write = csv.writer(f)
        write.writerow(fairness_fields)
        write.writerows(fairness_data)


def main():
    """Main function to execute all steps."""
    result_path = get_result_path(model_data_folder)

    matrix_df, config_df, drone_df = read_data(result_path)

    avg_noises, max_noises, std, iterations, X, Y, rows, cols, config = generate_density_matrix_images(
        matrix_df, config_df, result_path)

    cnt_avg_harm_cell, cnt_max_harm_cell, cnt_100_harm_cell = generate_harm_maps(
        avg_noises, max_noises, config, result_path, X, Y, rows, cols)

    print_harm_counts(cnt_avg_harm_cell, cnt_max_harm_cell, cnt_100_harm_cell, rows, cols)

    compute_simulation_time(drone_df)

    create_overlay_map(result_path, config)

    generate_histograms(matrix_df, result_path)

    compute_and_save_fairness_data(matrix_df, drone_df, config, iterations, std, result_path)


if __name__ == "__main__":
    model_data_folder = 'v2_o50_d400_p0_z100'

    main()
