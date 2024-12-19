from common.configuration import ORDERS, DRONES, LONDON_WAREHOUSES
from dispatchCenter.center import Center

if __name__ == '__main__':
    center = Center(warehouses=LONDON_WAREHOUSES,
                    number_of_orders=ORDERS,
                    number_of_drones=DRONES)

    center.run_center()
