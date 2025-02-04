from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH, PLOT_STATISTICS
from simulation.center import Center
from stats.statistics import (
    calculate_delivery_distance_statistics, plot_graphs,
    plot_noise_difference_colormap, plot_noise_change_barchart
)

if __name__ == '__main__':
    center = Center(TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH)

    center.run_center()

    if PLOT_STATISTICS:
        plot_noise_difference_colormap(self.noise_impact)
        plot_noise_change_barchart(self.noise_impact)

        calculate_delivery_distance_statistics()
        plot_graphs()
