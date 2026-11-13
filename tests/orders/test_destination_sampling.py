"""Building blocks of the vectorised destination sampling, on hand-built cases."""
import random
from bisect import bisect_left

import numpy as np
import pandas as pd
import pytest

from orders import destination_sampling, seeded_order_pool
from orders.destination_sampling import (
    UNRESOLVED,
    choose_zone_indices,
    continue_python_random_stream,
    follow_order_chain,
)
from orders.seeded_order_pool import generate_destinations
from tests.orders.test_destination_stream import SLIVER_ZONES, TWO_ATTEMPTS, ZONES, read_recorded_pool


def test_numpy_stream_continues_the_python_generator():
    """The next uniforms of both generators are the same numbers, also after part of the stream is used."""
    python_generator = random.Random("destinations-9")
    used_first = [python_generator.random() for _ in range(3)]
    numpy_stream = continue_python_random_stream(python_generator)

    assert numpy_stream.random_sample(700).tolist() == [python_generator.random() for _ in range(700)]
    assert len(set(used_first)) == 3


def test_zone_is_the_first_whose_cumulative_share_reaches_the_uniform():
    """Shares 0.25, 0.75, 1.0: 0.1 -> zone 0, exactly 0.25 -> zone 0, 0.5 -> zone 1, 0.9 -> zone 2."""
    cumulative_shares = np.array([0.25, 0.75, 1.0])
    uniforms = np.array([0.1, 0.25, 0.5, 0.9])
    assert choose_zone_indices(uniforms, cumulative_shares).tolist() == [0, 0, 1, 2]
    assert choose_zone_indices(uniforms, cumulative_shares).tolist() == [
        bisect_left(cumulative_shares.tolist(), uniform) for uniform in uniforms.tolist()
    ]


def test_uniform_above_the_last_share_falls_in_the_last_zone():
    """Rounding can leave the last cumulative share just below one."""
    assert choose_zone_indices(np.array([0.9999]), np.array([0.5, 0.999])).tolist() == [1]


def test_orders_are_found_by_following_the_start_positions():
    """Order 1 starts at 0 and ends before 3, order 2 runs from 3 to 4, order 3 from 4 to 9."""
    next_positions = np.array([3, 2, 5, 4, 9, 6, 7, 8, 9, 10])
    assert follow_order_chain(next_positions, 3).tolist() == [0, 3, 4]


def test_chain_reaching_an_unresolved_position_or_the_end_of_the_stream_is_reported():
    assert follow_order_chain(np.array([2, 3, UNRESOLVED, 4]), 2) is None
    assert follow_order_chain(np.array([2, 3, 4, 5]), 3) is None
    assert follow_order_chain(np.array([2, 3, 4, 5]), 2).tolist() == [0, 2]


@pytest.mark.parametrize("uniforms_read_at_once", [7, 50, 5_000])
def test_pool_does_not_depend_on_how_much_of_the_stream_is_read_at_once(monkeypatch, uniforms_read_at_once):
    """Orders cut off at the end of a block of uniforms must be completed once the stream is extended."""
    monkeypatch.setattr(destination_sampling, "UNIFORMS_PER_ORDER_ESTIMATE", 0)
    monkeypatch.setattr(destination_sampling, "MINIMUM_STREAM_EXTENSION", uniforms_read_at_once)
    recorded = read_recorded_pool("destinations_seed7_n1500.csv").head(300)
    pd.testing.assert_frame_equal(generate_destinations(7, 300, ZONES), recorded, check_exact=True)


def test_exhausted_attempts_cut_off_at_the_end_of_a_block_are_completed(monkeypatch):
    monkeypatch.setattr(seeded_order_pool, "MAXIMUM_SAMPLING_ATTEMPTS", TWO_ATTEMPTS)
    monkeypatch.setattr(destination_sampling, "UNIFORMS_PER_ORDER_ESTIMATE", 0)
    monkeypatch.setattr(destination_sampling, "MINIMUM_STREAM_EXTENSION", 3)
    recorded = read_recorded_pool("destinations_seed3_n400_two_attempts.csv").head(120)
    pd.testing.assert_frame_equal(generate_destinations(3, 120, SLIVER_ZONES), recorded, check_exact=True)
