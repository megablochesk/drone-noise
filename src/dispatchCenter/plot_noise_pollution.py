import branca
import folium
import matplotlib
import numpy as np
import pandas as pd
from PIL import Image
from matplotlib import cm
from matplotlib.colors import Normalize

from common.configuration import MAP_LEFT, MAP_TOP, MAP_RIGHT, MAP_BOTTOM


def read_data(result_path):
    matrix_df = pd.read_csv(f'{result_path}/matrix.csv')
    config_df = pd.read_csv(f'{result_path}/config.csv')
    drone_df = pd.read_csv(f'{result_path}/drone.csv')
    return matrix_df, config_df, drone_df


def generate_density_matrix(matrix_df, config_df):
    config = config_df.iloc[0]
    rows = int(config['Rows'])
    cols = int(config['Cols'])

    avg_noises = matrix_df['Average Noise'].to_numpy().reshape(rows, cols)
    max_noises = matrix_df['Maximum Noise'].to_numpy().reshape(rows, cols)

    return avg_noises, max_noises

def plot_noise_on_map(avg_noises):
    center_lat = (MAP_TOP + MAP_BOTTOM) / 2
    center_lon = (MAP_LEFT + MAP_RIGHT) / 2

    # Normalize the average noises
    vmin = 25  # Minimum noise level for color scaling
    vmax = 60  # Maximum noise level for color scaling
    norm = Normalize(vmin=vmin, vmax=vmax)
    colormap = cm.get_cmap('jet')  # Choose your preferred colormap

    norm_avg_noises = norm(avg_noises)
    img = colormap(norm_avg_noises)

    img_uint8 = (img * 255).astype(np.uint8)

    img_pil = Image.fromarray(img_uint8)
    img_pil.save('avg_noises.png')

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    bounds = [[MAP_BOTTOM, MAP_LEFT], [MAP_TOP, MAP_RIGHT]]

    folium.raster_layers.ImageOverlay(
        name='Average Noise',
        image='avg_noises.png',
        bounds=bounds,
        opacity=0.6,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)

    colors = [cm.jet(i) for i in np.linspace(0, 1, 256)]
    colors_hex = [matplotlib.colors.rgb2hex(c) for c in colors]
    colormap = branca.colormap.LinearColormap(
        colors=colors_hex,
        vmin=vmin,
        vmax=vmax,
        caption='Average Noise (dB)'
    )

    colormap.add_to(m)

    folium.LayerControl().add_to(m)

    m.save('avg_noise_map.html')
    print("Map has been saved to 'avg_noise_map.html'")


def add_noise_pollution_layer():
    model_data_folder = f'../recourses/results/experiments/v2_o500_d400_p0_z100'
    base_noise_dataset = f'../recources/data/base_noise/test1'

    matrix_df, config_df, drone_df = read_data(model_data_folder)

    avg_noises, _ = generate_density_matrix(matrix_df, config_df)

    plot_noise_on_map(avg_noises)


if __name__ == '__main__':
    add_noise_pollution_layer()
