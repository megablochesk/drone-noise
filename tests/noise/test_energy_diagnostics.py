"""Energy-share diagnostics and single-event levels on hand-built samples above one receiver."""
import numpy as np
import pytest

from noise.energy_diagnostics import (
    calculate_event_exposure_levels_db,
    calculate_low_altitude_energy_shares,
    calculate_nearby_energy_shares,
)
from noise.energy_noise import FlightSamples

RECEIVER_NORTHINGS = np.array([0.0])
RECEIVER_EASTINGS = np.array([0.0])


def overhead_samples(altitudes_m: list[float]) -> FlightSamples:
    return FlightSamples(
        northings=np.zeros(len(altitudes_m)), eastings=np.zeros(len(altitudes_m)),
        altitudes_m=np.array(altitudes_m, dtype=np.float64),
    )


def test_low_altitude_share_of_one_ground_level_and_one_cruise_sample():
    """Energies 1/5^2 = 0.04 and 1/100^2 = 0.0001: the sample below 10 m carries 0.04 / 0.0401 = 99.75 %."""
    shares = calculate_low_altitude_energy_shares(
        RECEIVER_NORTHINGS, RECEIVER_EASTINGS, overhead_samples([5.0, 100.0]), altitude_limit_m=10.0
    )
    assert shares[0] == pytest.approx(0.04 / 0.0401, rel=1e-12)


def test_low_altitude_share_is_zero_without_low_samples():
    """Samples at 30 m and 100 m: nothing below 10 m."""
    shares = calculate_low_altitude_energy_shares(
        RECEIVER_NORTHINGS, RECEIVER_EASTINGS, overhead_samples([30.0, 100.0]), altitude_limit_m=10.0
    )
    assert shares[0] == 0.0


def test_nearby_share_counts_samples_within_the_slant_distance():
    """Samples 30 m and 100 m overhead, 50 m limit: (1/900) / (1/900 + 1/10000) = 91.74 %."""
    shares = calculate_nearby_energy_shares(
        RECEIVER_NORTHINGS, RECEIVER_EASTINGS, overhead_samples([30.0, 100.0]), slant_distance_limit_m=50.0
    )
    assert shares[0] == pytest.approx((1 / 900) / (1 / 900 + 1 / 10_000), rel=1e-12)


def test_event_exposure_level_of_ten_seconds_overhead():
    """Ten 1 s samples of a 90 dB source 100 m overhead: 50 dB for 10 s is 50 + 10 = 60 dB SEL."""
    levels = calculate_event_exposure_levels_db(
        RECEIVER_NORTHINGS, RECEIVER_EASTINGS, overhead_samples([100.0] * 10), noise_at_source_db=90.0, time_step_s=1.0
    )
    assert levels[0] == pytest.approx(60.0, abs=1e-9)


def test_event_exposure_level_scales_with_the_time_step():
    """One 30 s sample at 50 dB: 50 + 10*log10(30) = 64.77 dB SEL."""
    levels = calculate_event_exposure_levels_db(
        RECEIVER_NORTHINGS, RECEIVER_EASTINGS, overhead_samples([100.0]), noise_at_source_db=90.0, time_step_s=30.0
    )
    assert levels[0] == pytest.approx(64.77, abs=0.005)
