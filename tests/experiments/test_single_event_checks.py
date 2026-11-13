"""Single-event checks (Phase 8d): the model's own sampling of one pass and of one delivery.

Closed forms used as oracles. A level pass at speed v and height h sampled every a = v * dt metres has
exposure S * dt * sum_k 1 / (h^2 + (x - k*a)^2). Directly under a sample this is the continuous value times
coth(pi*h/a); half-way between samples, times tanh(pi*h/a); averaged over all receiver positions it equals
the continuous value S * pi / (v * h) exactly.
"""
import math

import numpy as np
import pytest

from common.coordinate import Coordinate
from common.model_configs import model_config
from experiments.revision.single_event_checks import (
    FEET_TO_METRES,
    place_receivers_across_track,
    simulate_single_delivery,
    summarise_straight_pass,
    summarise_terminal_event,
)

CLOSED_FORM_PASS_SEL_DB = 90.0 + 10.0 * math.log10(math.pi / (27.0 * 100.0))
SAMPLE_SPACING_AT_THIRTY_SECONDS_M = 27.0 * 30.0
PHASE_ERROR_DB = 10.0 * math.log10(1.0 / math.tanh(math.pi * 100.0 / SAMPLE_SPACING_AT_THIRTY_SECONDS_M))


def test_receivers_are_placed_at_right_angles_to_an_east_west_track():
    """Hand-built case: 10 m and 20 m from a destination at (1000 N, 2000 E) are 1010 N and 1020 N."""
    northings, eastings = place_receivers_across_track(Coordinate(northing=1_000.0, easting=2_000.0), [10.0, 20.0])
    np.testing.assert_allclose(northings, [1_010.0, 1_020.0])
    np.testing.assert_allclose(eastings, [2_000.0, 2_000.0])


def test_phase_error_of_the_thirty_second_step_is_about_four_decibels():
    """pi * 100 / 810 = 0.388; coth(0.388) = 2.70, i.e. +4.3 dB under a sample and -4.3 dB between samples."""
    assert PHASE_ERROR_DB == pytest.approx(4.3, abs=0.05)


def test_straight_pass_at_the_published_time_step_depends_on_the_receiver_position():
    """Closed form above: maximum = continuous + 4.3 dB, minimum = continuous - 4.3 dB, energy mean = continuous."""
    summary = summarise_straight_pass(model_config)
    assert summary["time_step_s"] == 30
    assert summary["maximum_sel_db"] == pytest.approx(CLOSED_FORM_PASS_SEL_DB + PHASE_ERROR_DB, abs=0.05)
    assert summary["minimum_sel_db"] == pytest.approx(CLOSED_FORM_PASS_SEL_DB - PHASE_ERROR_DB, abs=0.05)
    assert summary["energy_mean_sel_db"] == pytest.approx(CLOSED_FORM_PASS_SEL_DB, abs=0.05)
    assert summary["closed_form_sel_db"] == pytest.approx(60.66, abs=0.005)


def test_terminal_event_at_twenty_feet_matches_the_hand_calculation():
    """Stepping rule with a 60 s landing delay and 30 s steps: at the customer the drone is sampled at
    100, 50, 0 m (arrival), 0, 50, 100, 50, 0 m (delivery leg) and 0, 50, 100 m (departure).
    At 20 ft = 6.096 m: four ground samples 1/37.16 each, four 50 m samples 1/2537.16 each, three 100 m
    samples 1/10037.16 each -> sum 0.10952 m^-2; times 30 s -> 90 + 10*log10(3.2856) = 95.17 dBA."""
    delivery = simulate_single_delivery(model_config, terminal_phases=True)
    summary = summarise_terminal_event(delivery, horizontal_distances_ft=[20.0])
    assert FEET_TO_METRES == 0.3048
    assert summary["samples_at_destination"].iloc[0] == 11
    assert summary["terminal_event_sel_db"].iloc[0] == pytest.approx(95.17, abs=0.01)
    assert summary["whole_delivery_sel_db"].iloc[0] >= summary["terminal_event_sel_db"].iloc[0]
