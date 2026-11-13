"""Replication statistics on samples small enough for a hand calculation with printed t-tables.

Two-sided 95 % Student-t quantiles used below (standard tables): 2 degrees of freedom 4.303, 4 degrees 2.776,
79 degrees 1.9905, 80 degrees 1.9901.
"""
import math

import numpy as np
import pytest

from metrics.replication_statistics import (
    calculate_required_replicates,
    summarise_paired_differences,
    summarise_replicates,
)

KNOWN_SAMPLE = np.array([10.0, 12.0, 14.0, 16.0, 18.0])


def test_summary_of_a_known_sample():
    """Mean 14; squared deviations 16 + 4 + 0 + 4 + 16 = 40, variance 40 / 4 = 10, SD = 3.1623;
    CV = 3.1623 / 14 = 0.2259; half-width = 2.776 * 3.1623 / sqrt(5) = 3.926."""
    summary = summarise_replicates(KNOWN_SAMPLE)
    assert summary.number_of_replicates == 5
    assert summary.mean == pytest.approx(14.0)
    assert summary.standard_deviation == pytest.approx(math.sqrt(10.0))
    assert summary.coefficient_of_variation == pytest.approx(0.2259, abs=5e-5)
    assert summary.confidence_half_width == pytest.approx(3.926, abs=5e-4)


def test_required_replicates_for_a_five_percent_half_width():
    """Target half-width 0.05 * 14 = 0.7. With n = 80: 1.9905 * 3.1623 / sqrt(80) = 0.7038 (too wide);
    with n = 81: 1.9901 * 3.1623 / 9 = 0.6992 (narrow enough). So 81 replicates are needed."""
    assert calculate_required_replicates(KNOWN_SAMPLE, relative_half_width=0.05) == 81


def test_required_replicates_is_at_least_two_for_a_tight_sample():
    """SD 0.001 around a mean of 100: any n >= 2 meets a 5 % target, and a t-interval needs at least 2."""
    assert calculate_required_replicates(np.array([100.0, 100.001, 99.999]), relative_half_width=0.05) == 2


def test_constant_sample_has_zero_spread():
    """All values equal: SD, CV and half-width are exactly zero."""
    summary = summarise_replicates(np.full(4, 7.5))
    assert summary.standard_deviation == 0.0
    assert summary.coefficient_of_variation == 0.0
    assert summary.confidence_half_width == 0.0


def test_paired_differences_within_seed():
    """Differences 1, 2, 3: mean 2, SD 1, half-width 4.303 * 1 / sqrt(3) = 2.484."""
    summary = summarise_paired_differences(np.array([10.0, 12.0, 14.0]), np.array([9.0, 10.0, 11.0]))
    assert summary.mean == pytest.approx(2.0)
    assert summary.standard_deviation == pytest.approx(1.0)
    assert summary.confidence_half_width == pytest.approx(2.484, abs=5e-4)
