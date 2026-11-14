"""Fine-grid runs next to the coarse runs of the same seeds, on a hand-built table."""
import pandas as pd
import pytest

from experiments.revision.summarise_fine_grid import compare_fine_with_coarse


def build_runs(mean_increases_db: list[float], newly_exposed: list[float], delivered: list[int]) -> pd.DataFrame:
    """One configuration (1,250 drones, best stocking, terminal phases) for seeds 1 and 2."""
    return pd.DataFrame({
        "number_of_drones": 1250, "stocking": "closest", "terminal_phases": True, "seed": [1, 2],
        "mean_noise_increase_db": mean_increases_db, "newly_exposed_population_55db": newly_exposed,
        "delivered_orders": delivered,
    })


def test_configuration_means_and_seed_paired_changes():
    """Coarse seeds: 1.0 and 1.2 dB, 1,000 and 2,000 people, 100 and 200 deliveries. Fine seeds: 1.5 and 1.9 dB,
    1,500 and 2,400 people, 110 and 220 deliveries. Paired changes: +0.5 and +0.7 dB (mean +0.6); people
    +50 % and +20 % (mean +35 %); deliveries +10 % both."""
    coarse = build_runs([1.0, 1.2], [1_000.0, 2_000.0], [100, 200])
    fine = build_runs([1.5, 1.9], [1_500.0, 2_400.0], [110, 220])

    comparison = compare_fine_with_coarse(fine, coarse)

    assert len(comparison) == 1
    row = comparison.iloc[0]
    assert (row["number_of_drones"], row["stocking"], row["terminal_phases"], row["number_of_seeds"]) == (1250, "closest", True, 2)
    assert row["mean_noise_increase_db"] == pytest.approx(1.7)
    assert row["mean_noise_increase_db_reference"] == pytest.approx(1.1)
    assert row["mean_noise_increase_db_change"] == pytest.approx(0.6)
    assert row["newly_exposed_population_55db_relative_change"] == pytest.approx(0.35)
    assert row["delivered_orders_relative_change"] == pytest.approx(0.10)


def test_seeds_without_a_coarse_twin_are_left_out():
    coarse = build_runs([1.0, 1.2], [1_000.0, 2_000.0], [100, 200]).query("seed == 1")
    fine = build_runs([1.5, 1.9], [1_500.0, 2_400.0], [110, 220])
    assert compare_fine_with_coarse(fine, coarse).iloc[0]["number_of_seeds"] == 1


def test_two_variants_of_one_configuration_and_seed_are_refused():
    """Found in review: a table holding several routings per configuration would be averaged over the routings
    and the result labelled as seeds. Such a table has to be split by variant before it is compared."""
    fine = build_runs([1.0, 1.2], [100.0, 120.0], [10, 12])
    two_routings = pd.concat([fine, fine.assign(mean_noise_increase_db=2.0)])

    with pytest.raises(ValueError, match="more than one run"):
        compare_fine_with_coarse(two_routings, fine)
    with pytest.raises(ValueError, match="more than one run"):
        compare_fine_with_coarse(fine, two_routings)
