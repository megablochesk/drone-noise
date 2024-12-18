import numpy as np
import pandas as pd
import folium
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from PIL import Image
import branca
import matplotlib

MAP_LEFT = -0.510 + 0.004
MAP_RIGHT = 0.334 + 0.020
MAP_TOP = 51.691 - 0.005
MAP_BOTTOM = 51.286 + 0.003


def read_data(result_path):
    """Read necessary data from CSV files."""
    matrix_df = pd.read_csv(f'{result_path}/matrix.csv')
    config_df = pd.read_csv(f'{result_path}/config.csv')
    drone_df = pd.read_csv(f'{result_path}/drone.csv')
    return matrix_df, config_df, drone_df


def generate_density_matrix(matrix_df, config_df):
    """Generate density matrix from data."""
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

    return avg_noises, max_noises, std, iterations, X, Y, rows, cols, config

def plot_noise_on_map(avg_noises):
    """Plot the average noise matrix on a Folium map of London."""

    # Center coordinates
    center_lat = (MAP_TOP + MAP_BOTTOM) / 2
    center_lon = (MAP_LEFT + MAP_RIGHT) / 2

    # Normalize the average noises
    vmin = 25  # Minimum noise level for color scaling
    vmax = 60  # Maximum noise level for color scaling
    norm = Normalize(vmin=vmin, vmax=vmax)
    colormap = cm.get_cmap('jet')  # Choose your preferred colormap

    # Apply normalization and colormap
    norm_avg_noises = norm(avg_noises)
    img = colormap(norm_avg_noises)

    # Flip the image vertically to match the map's orientation
    # img = np.flipud(img)

    # Convert to uint8 format
    img_uint8 = (img * 255).astype(np.uint8)

    # Save the image
    img_pil = Image.fromarray(img_uint8)
    img_pil.save('avg_noises.png')

    # Create the Folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # Define the image bounds
    bounds = [[MAP_BOTTOM, MAP_LEFT], [MAP_TOP, MAP_RIGHT]]

    # Add the image overlay
    folium.raster_layers.ImageOverlay(
        name='Average Noise',
        image='avg_noises.png',
        bounds=bounds,
        opacity=0.6,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)

    # Create a matching colormap for the colorbar
    colors = [cm.jet(i) for i in np.linspace(0, 1, 256)]
    colors_hex = [matplotlib.colors.rgb2hex(c) for c in colors]
    colormap = branca.colormap.LinearColormap(
        colors=colors_hex,
        vmin=vmin,
        vmax=vmax,
        caption='Average Noise (dB)'
    )

    # Add the colorbar to the map
    colormap.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Save the map to an HTML file
    m.save('avg_noise_map.html')
    print("Map has been saved to 'avg_noise_map.html'")


def add_noise_pollution_layer():
    # Path to your result data
    model_data_folder = f'../recourses/results/experiments/v2_o500_d400_p0_z100'
    base_noise_dataset = f'../recources/data/base_noise/test1'

    matrix_df, config_df, drone_df = read_data(model_data_folder)

    # Generate density matrix
    avg_noises, max_noises, std, iterations, X, Y, rows, cols, config = generate_density_matrix(matrix_df, config_df)

    # Plot the average noise on the map
    plot_noise_on_map(avg_noises)


if __name__ == '__main__':
    add_noise_pollution_layer()
