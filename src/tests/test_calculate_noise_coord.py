import unittest
import math
import timeit
from parameterized import parameterized

from common.constants import DRONE_ALTITUTE, M_2_LATITUDE, M_2_LONGITUDE, DRONE_NOISE
from common.math_utils import calculate_noise_coord


class TestCalculateNoiseCoord(unittest.TestCase):

    @parameterized.expand([
        (0, 0),
        (1000, 1000),
        (0.1, 0.1),
        (-1000, -1000),
        (-0.1, -0.1)
    ])
    def test_calculate_noise_coord(self, x_dist, y_dist):
        result = calculate_noise_coord(x_dist, y_dist, DRONE_NOISE)
        expected = TestCalculateNoiseCoord.calculate_expected_noise_coord(x_dist, y_dist, DRONE_NOISE)

        self.assertEqual(result, expected)

    """
    @parameterized.expand([
        (0, 0),
        (1000, 1000),
        (0.1, 0.1),
        (-1000, -1000),
        (-0.1, -0.1)
    ])
    def test_performance_comparison(self, x_dist, y_dist):
        # Measure time for the original function
        time_original = timeit.timeit(
            lambda: calculate_expected_noise_coord(x_dist, y_dist, DRONE_NOISE),
            number=1000
        )

        # Measure time for the optimized function
        time_optimized = timeit.timeit(
            lambda: calculate_noise_coord(x_dist, y_dist, DRONE_NOISE),
            number=1000
        )

        print(f"Performance for x_dist={x_dist}, y_dist={y_dist}:")
        print(f"Original function time: {time_original:.6f} seconds")
        print(f"Optimized function time: {time_optimized:.6f} seconds")

        # Assert that the optimized version is faster (you can adjust the factor based on expected speedup)
        # self.assertLess(time_optimized, time_original)
    """

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
