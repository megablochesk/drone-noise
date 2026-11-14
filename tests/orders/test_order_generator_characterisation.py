import random

from orders import order_generator
from tests.legacy_reference import load_legacy_order_generator

LEGACY_ORDER_GENERATOR = load_legacy_order_generator()


def test_population_based_points_match_the_published_generator():
    """Characterisation: same global seed, same points as the generator at the published baseline commit."""
    random.seed(20240117)
    current_points = [order_generator.generate_random_population_based_point() for _ in range(60)]
    random.seed(20240117)
    legacy_points = [LEGACY_ORDER_GENERATOR.generate_random_population_based_point() for _ in range(60)]
    assert current_points == legacy_points
