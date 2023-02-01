import pandas as pd
import numpy as np
from commons.configuration import RESULT_BASE_PATH
from commons.my_util import plot_matrix, plot_histogram
from commons.configuration import GEO_PATH, PD_PATH, CRS
from commons.configuration import style_function, highlight_function
from commons.configuration import HARM_AVG_LEVEL, HARM_MAX_LEVEL
import geopandas as gpd
import folium
from folium.raster_layers import ImageOverlay
import csv
import seaborn as sns
from matplotlib import pyplot as plt

plt.style.use('seaborn-white')
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 14
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42

avg_speed = 22 # 80km/h = 22m/s

total_drones = {}
total_distance = {}
total_orders = {}
total_simulation_time = {}
total_orders_per_hour = {}
total_noise = {}
avg_distance = {}
max_noise = {}
mean_noise = {}
std_noise = {}
noise_points = {}

# directory name: e.g. 'p=5', '2022-07-22_18:00:00'
for directory in ['v2_o200_d100_k0_z100', 'v2_o400_d200_k0_z100', 'v2_o800_d400_k0_z100', 'v2_o1600_d800_k0_z100']:

    # concat the path
    result_path = './' + RESULT_BASE_PATH + '/' + directory

    # read data
    matrix_df = pd.read_csv(result_path + '/matrix.csv')
    config_df = pd.read_csv(result_path + '/config.csv')
    drone_df = pd.read_csv(result_path + '/drone.csv')

    iterations = int(matrix_df.iloc[0]['Time'])
    total_drones = drone_df['Total Distance'].count()

    total_distance[total_drones] = drone_df['Total Distance'].sum()
    total_orders[total_drones] = drone_df['Total Orders'].sum()
    total_simulation_time[total_drones] = drone_df['Total Distance'].max() / 22
    total_orders_per_hour[total_drones] = total_orders[total_drones] / (total_simulation_time[total_drones]/3600.0)
    total_noise[total_drones] = matrix_df['Average Noise'].sum() * iterations
    avg_distance[total_drones] = total_distance[total_drones] / total_orders[total_drones]
    max_noise[total_drones] = matrix_df['Average Noise'].max()
    mean_noise[total_drones] = matrix_df['Average Noise'].mean()
    std_noise[total_drones] = matrix_df['Average Noise'].std()
    noise_points[total_drones] = matrix_df['Average Noise']

    print('%d drones, %d orders, %.2f sim time, %.2f orders per hour' % (total_drones, total_orders[total_drones],total_simulation_time[total_drones],  total_orders_per_hour[total_drones]))

print(total_distance)
print(total_orders)
print(total_simulation_time)
print(total_orders_per_hour)
print(total_noise)
print(avg_distance)
print(max_noise)
print(mean_noise)
print(std_noise)

#plt.figure()
#plt.title('Worst-case regional average noise')
#plt.xlabel('Number of drones')
#plt.ylabel('Noise max (dB)')
#plt.plot(list(max_noise.keys()), list(max_noise.values()), '.-')
#plt.show()

plt.figure()
#plt.title('Average regional-noise')
plt.xlabel('Number of drones')
plt.ylabel('Regional noise (dB)')
#plt.plot(list(mean_noise.keys()), list(mean_noise.values()), '.-')
plt.errorbar(list(mean_noise.keys()), list(mean_noise.values()), yerr=list(std_noise.values()))
for n in noise_points:
  plt.plot(np.ones(len(noise_points[n]))*n, noise_points[n], 'k', marker='.', alpha=.05)
plt.tight_layout()
plt.savefig('ndrones-noise.pdf')
plt.savefig('ndrones-noise.png')
plt.show()

