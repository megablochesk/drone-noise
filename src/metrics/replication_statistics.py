"""Summary statistics over replicate runs (seeds) of one configuration."""
from dataclasses import dataclass

import numpy as np
from scipy import stats

CONFIDENCE_LEVEL = 0.95
MINIMUM_REPLICATES_FOR_AN_INTERVAL = 2
MAXIMUM_REPLICATES_SEARCHED = 100_000


@dataclass(frozen=True)
class ReplicateSummary:
    number_of_replicates: int
    mean: float
    standard_deviation: float
    coefficient_of_variation: float
    confidence_half_width: float


def student_t_quantile(number_of_replicates: int) -> float:
    return stats.t.ppf(0.5 + CONFIDENCE_LEVEL / 2.0, df=number_of_replicates - 1)


def calculate_confidence_half_width(standard_deviation: float, number_of_replicates: int) -> float:
    return student_t_quantile(number_of_replicates) * standard_deviation / np.sqrt(number_of_replicates)


def summarise_replicates(values: np.ndarray) -> ReplicateSummary:
    mean = np.mean(values)
    standard_deviation = np.std(values, ddof=1)
    return ReplicateSummary(
        number_of_replicates=len(values),
        mean=mean,
        standard_deviation=standard_deviation,
        coefficient_of_variation=standard_deviation / abs(mean) if mean != 0 else np.nan,
        confidence_half_width=calculate_confidence_half_width(standard_deviation, len(values)),
    )


def summarise_paired_differences(first_values: np.ndarray, second_values: np.ndarray) -> ReplicateSummary:
    """Summary of first minus second, paired by position (the same seed in both configurations)."""
    return summarise_replicates(first_values - second_values)


def calculate_required_replicates(values: np.ndarray, relative_half_width: float) -> int:
    """Smallest n whose 95 % t-interval half-width is within the given fraction of the pilot mean.

    The pilot standard deviation and mean are taken as given; the t quantile is re-evaluated for each n.
    """
    target_half_width = relative_half_width * abs(np.mean(values))
    standard_deviation = np.std(values, ddof=1)

    for number_of_replicates in range(MINIMUM_REPLICATES_FOR_AN_INTERVAL, MAXIMUM_REPLICATES_SEARCHED + 1):
        if calculate_confidence_half_width(standard_deviation, number_of_replicates) <= target_half_width:
            return number_of_replicates

    raise ValueError(f"More than {MAXIMUM_REPLICATES_SEARCHED} replicates would be needed")
