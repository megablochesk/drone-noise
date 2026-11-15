"""The published configurations over their first 15 simulated minutes reproduce the stored reference slices.

The slices are written by generate_published_slices.py through the runners that the full-day tests check
against the manuscript (test_published_results.py, test_published_noise_aware_result.py), at a commit where
those tests pass. A slice therefore stands for the published result over that period.
"""
import pytest

from tests.regression.published_runs import (
    PUBLISHED_NOISE_AWARE_CONFIGURATION,
    PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS,
    SLICE_SIMULATION_END_S,
    describe,
    load_reference_headline,
    load_reference_map,
    per_cell_map,
    run_published_configuration,
    summarise_energy_sum_runner,
    summarise_published_runner,
)

REFERENCE_TOLERANCE = 1e-9
PER_CELL_TOLERANCE_DB = 1e-9
# The two runners fly the same drones and sum the same energy in a different order.
RUNNER_AGREEMENT_RELATIVE = 1e-9
HEADLINE_KEYS = ["delivered_orders", "mean_noise_increase_db", "newly_exposed_population"]
ALL_CONFIGURATIONS = [*PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS, PUBLISHED_NOISE_AWARE_CONFIGURATION]


def test_reference_slices_cover_the_period_the_tests_run_and_deliver_orders():
    """At the closest stocking drones are back from deliveries within the slice; at the furthest none is yet."""
    headlines = {describe(configuration): load_reference_headline(configuration) for configuration in ALL_CONFIGURATIONS}

    assert {headline["simulation_end_s"] for headline in headlines.values()} == {SLICE_SIMULATION_END_S}
    assert all(
        headline["published_runner"]["delivered_orders"] > 0
        for name, headline in headlines.items() if name.startswith("closest")
    )


@pytest.mark.parametrize("configuration", ALL_CONFIGURATIONS, ids=describe)
def test_published_runner_reproduces_the_reference_slice(configuration):
    reference = load_reference_headline(configuration)["published_runner"]
    current = summarise_published_runner(configuration, SLICE_SIMULATION_END_S)

    assert current["delivered_orders"] == reference["delivered_orders"]
    assert current == pytest.approx(reference, rel=REFERENCE_TOLERANCE)


@pytest.mark.parametrize("configuration", ALL_CONFIGURATIONS, ids=describe)
def test_per_cell_map_matches_the_reference_slice(configuration):
    current = per_cell_map(run_published_configuration(configuration, SLICE_SIMULATION_END_S))
    reference = load_reference_map(configuration)

    assert current.index.equals(reference.index)
    assert (current - reference).abs().max().max() < PER_CELL_TOLERANCE_DB


@pytest.mark.parametrize("configuration", PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS, ids=describe)
def test_energy_sum_runner_reproduces_the_reference_slice_and_agrees_with_the_published_runner(configuration):
    reference = load_reference_headline(configuration)
    current = summarise_energy_sum_runner(configuration, SLICE_SIMULATION_END_S)
    published_runner = reference["published_runner"]

    assert current == pytest.approx(reference["energy_sum_runner"], rel=REFERENCE_TOLERANCE)
    assert {key: current[key] for key in HEADLINE_KEYS} == pytest.approx(published_runner, rel=RUNNER_AGREEMENT_RELATIVE)
