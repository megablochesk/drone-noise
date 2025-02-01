from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH
from simulation.center import Center

if __name__ == '__main__':
    center = Center(TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH)

    center.run_center()
