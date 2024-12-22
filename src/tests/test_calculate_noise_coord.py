import math
import timeit
import unittest

from common.constants import M_2_LATITUDE, M_2_LONGITUDE
from common.configuration import DRONE_NOISE, DRONE_ALTITUTE
from common.coordinate import Coordinate, calculate_distance
from matrix.noise_math_utils import calculate_noise_at_distance
from parameterized import parameterized


class TestCalculateNoiseCoord(unittest.TestCase):

    @parameterized.expand([
        (Coordinate(0, 0), Coordinate(0, 0)),
        (Coordinate(0, 0), Coordinate(1000, 1000)),
        (Coordinate(0, 0), Coordinate(0.1, 0.1)),
        (Coordinate(0, 0), Coordinate(-1000, -1000)),
        (Coordinate(0, 0), Coordinate(-0.1, -0.1))
    ])
    def test_calculate_noise_coord_line_dist(self, coordinates1, coordinates2):
        la_distance, lo_distance = coordinates2 - coordinates1
        line_distance = calculate_distance(coordinates1, coordinates2)

        expected = TestCalculateNoiseCoord.calculate_expected_noise_coord(lo_distance, la_distance, DRONE_NOISE)

        result = calculate_noise_at_distance(line_distance)

        # print(result, expected)
        self.assertEqual(result, expected)


    @parameterized.expand([
        (Coordinate(0, 0), Coordinate(0, 0)),
        (Coordinate(0, 0), Coordinate(1000, 1000)),
        (Coordinate(0, 0), Coordinate(0.1, 0.1)),
        (Coordinate(0, 0), Coordinate(-1000, -1000)),
        (Coordinate(0, 0), Coordinate(-0.1, -0.1))
    ])
    def test_performance_comparison(self, coordinates1, coordinates2):
        la_distance, lo_distance = coordinates2 - coordinates1
        line_distance = calculate_distance(coordinates1, coordinates2)

        time_original = timeit.timeit(
            lambda: TestCalculateNoiseCoord.calculate_expected_noise_coord(lo_distance, la_distance, DRONE_NOISE),
            number=1000
        )

        time_optimized = timeit.timeit(
            lambda: calculate_noise_at_distance(line_distance),
            number=1000
        )

        print(f"Performance for x_dist={lo_distance}, y_dist={la_distance}:")
        print(f"Original function time: {time_original:.6f} seconds")
        print(f"Optimized function time: {time_optimized:.6f} seconds")

        # self.assertLess(time_optimized, time_original)


    @staticmethod
    def calculate_expected_noise_coord(x_dist, y_dist, central_noise):
        if math.fabs(x_dist) + math.fabs(y_dist) == 0:
            if DRONE_ALTITUTE <= 0:
                return central_noise
            else:
                return central_noise - math.fabs(10 * math.log10(math.pow(DRONE_ALTITUTE, 2)))
        else:
            return central_noise - math.fabs(10 * math.log10(math.pow(x_dist / M_2_LONGITUDE, 2) +
                                                             math.pow(y_dist / M_2_LATITUDE, 2) +
                                                             math.pow(DRONE_ALTITUTE, 2)))


if __name__ == '__main__':
    unittest.main()
