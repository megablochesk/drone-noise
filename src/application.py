from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, LONDON_WAREHOUSES
from simulation.center import Center

if __name__ == '__main__':
    center = Center(warehouses=LONDON_WAREHOUSES,
                    number_of_orders=TOTAL_ORDER_NUMBER,
                    number_of_drones=TOTAL_DRONE_NUMBER)

    center.run_center()
