import csv
import os

from common.configuration import RESULT_BASE_PATH


def define_results_path(order_number, drone_number):
    path = RESULT_BASE_PATH + '/' + f"stat_o{order_number}_d{drone_number}"

    if not os.path.exists(path):
        os.makedirs(path)

    return path


def save_drones_data(drones, path):
    drone_path = f"{path}/drone.csv"
    drone_fields = ['Drone ID', 'Total Step', 'Total Distance', 'Total Orders']
    drone_data = [
        [
            drone.drone_id,
            drone.tracker.total_step(),
            drone.tracker.total_distance(),
            drone.tracker.total_orders()
        ]
        for drone in drones
    ]

    write_csv(drone_path, drone_fields, drone_data, 'drones data')


def save_drone_noise_data(noise_tracker, iteration_count, path):
    matrix_path = f"{path}/noise.csv"
    matrix_fields = ['row', 'col', 'avg_noise', 'max_noise']
    matrix_data = [
        [
            i, j,
            noise_tracker.noise_matrix[i][j].total_noise / iteration_count,
            noise_tracker.noise_matrix[i][j].max_noise
        ]
        for i in range(noise_tracker.rows)
        for j in range(noise_tracker.cols)
    ]

    write_csv(matrix_path, matrix_fields, matrix_data, 'noise data')


def write_csv(file_path, headers, data, data_type):
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        print(f"Done writing {data_type}!")
        f.flush()
