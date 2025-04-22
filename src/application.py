from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH, PLOT_STATISTICS
from simulation.center import Center
import stats.statistics as stats
from stats.plot_utils import plot_figures, save_figures
from stats.plot_noise_level_comparison import plot_noise_level_comparison
from stats.different_noise_map_experiment import run_different_dataset_noise_maps

if __name__ == '__main__':
    #center = Center(TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH)

    #center.run_center()

    #if PLOT_STATISTICS:
        # plot_noise_difference_colormap(center.noise_impact)
        # plot_noise_change_barchart(center.noise_impact)

        #plot_noise_level_comparison(center.noise_impact)

        #save_figures()

        #plot_figures()

    run_different_dataset_noise_maps()
