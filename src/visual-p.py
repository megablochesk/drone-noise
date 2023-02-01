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
time_per_order = {}
total_noise = {}
avg_distance = {}
max_noise = {}
mean_noise = {}
std_noise = {}

# directory name: e.g. 'p=5', '2022-07-22_18:00:00'
for directory in ['v2_o800_d400_k0_z100', 'v2_o800_d400_p1_z100', 'v2_o800_d400_p2_z100', 'v2_o800_d400_p3_z100', 'v2_o800_d400_p4_z100', 'v2_o800_d400_p5_z100']:

    if directory.find('_k0') > -1:
      p = 0
    else:
      p_k = directory.find('_p')
      p = int(directory[p_k+2])

    # concat the path
    result_path = './' + RESULT_BASE_PATH + '/' + directory

    # read data
    matrix_df = pd.read_csv(result_path + '/matrix.csv')
    config_df = pd.read_csv(result_path + '/config.csv')
    drone_df = pd.read_csv(result_path + '/drone.csv')

    iterations = int(matrix_df.iloc[0]['Time'])
    total_drones = drone_df['Total Distance'].count()

    total_distance[p] = drone_df['Total Distance'].sum()
    total_orders[p] = drone_df['Total Orders'].sum()
    total_simulation_time[p] = drone_df['Total Distance'].max() / 22
    total_orders_per_hour[p] = total_orders[p] / (total_simulation_time[p]/3600.0)
    time_per_order[p] = total_distance[p] / 22 / total_orders[p]
    total_noise[p] = matrix_df['Average Noise'].sum() * iterations
    avg_distance[p] = total_distance[p] / total_orders[p]
    max_noise[p] = matrix_df['Average Noise'].max()
    mean_noise[p] = matrix_df['Average Noise'].mean()
    std_noise[p] = matrix_df['Average Noise'].std()

    print('%d drones, %d orders, %.2f sim time, %.2f orders per hour, %.2f sec per order' % (total_drones, total_orders[p],total_simulation_time[p],  total_orders_per_hour[p], time_per_order[p]))

print(total_distance)
print(total_orders)
print(total_simulation_time)
print(total_orders_per_hour)
print(time_per_order)
print(total_noise)
print(avg_distance)
print(max_noise)
print(mean_noise)
print(std_noise)

#plt.figure()
#plt.xlabel('Delivery time (s)')
#plt.ylabel('Noise max (dB)')
#plt.plot(list(time_per_order.values()), list(max_noise.values()), '.-')
#plt.show()

plt.figure()
plt.xlabel('Delivery time (s)')
plt.ylabel('Regional-noise stddev (dB)')
plt.plot(list(time_per_order.values()), list(std_noise.values()), '.-')
plt.tight_layout()
plt.savefig('tradeoff-time-stddev.pdf')
plt.savefig('tradeoff-time-stddev.png')
plt.show()

plt.figure()
plt.xlabel('P')
plt.ylabel('Regional-noise stddev (dB)')
plt.plot(list(std_noise.keys()), list(std_noise.values()), '.-')
plt.tight_layout()
plt.savefig('p-stddev.pdf')
plt.savefig('p-stddev.png')
plt.show()

#plt.figure()
#plt.xlabel('P')
#plt.ylabel('Noise max (dB)')
#plt.plot(list(max_noise.keys()), list(max_noise.values()), '.-')
#plt.show()

#plt.figure()
#plt.xlabel('P')
#plt.ylabel('Average regional noise (dB)')
#plt.errorbar(list(mean_noise.keys()), list(mean_noise.values()), yerr=list(std_noise.values()))
#plt.show()

