from cityMap.citymap import CityMap
from dispatchCenter.center import Center
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.configuration import WAREHOUSES, ORDERS, DRONES, LONDON_WAREHOUSES

if __name__ == '__main__':
    center = Center(warehouses=LONDON_WAREHOUSES,
                    city_map=CityMap(left=MAP_LEFT, right=MAP_RIGHT, bottom=MAP_BOTTOM, top=MAP_TOP),
                    num_orders=ORDERS,
                    num_drones=DRONES)
    center.run_center()
