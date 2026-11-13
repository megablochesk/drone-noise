"""Mutation check: break each mathematical function once, confirm a test fails, restore the source.

Usage (from src/): python -m experiments.revision.run_mutation_checks
"""
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.revision.phase_outputs import write_phase_table
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIRECTORY = REPOSITORY_ROOT / "results"


@dataclass(frozen=True)
class Mutation:
    function_name: str
    source_path: str
    description: str
    original: str
    mutated: str
    test_paths: tuple[str, ...]


NOISE_MATH = "src/noise/noise_math_utils.py"
ENERGY_NOISE = "src/noise/energy_noise.py"
EXPOSURE = "src/metrics/exposure_metrics.py"
REPLICATION = "src/metrics/replication_statistics.py"
POSTPROCESSING = "src/metrics/map_postprocessing.py"
DIAGNOSTICS = "src/noise/energy_diagnostics.py"
PHASE8_TABLES = "src/experiments/revision/phase8_tables.py"

MUTATIONS = (
    Mutation("calculate_noise_at_distance", NOISE_MATH, "10*log10 of squared distance -> 20*log10",
             "noise_at_source_db - 10.0 * np.log10(squared_distance)", "noise_at_source_db - 20.0 * np.log10(squared_distance)",
             ("tests/noise/test_noise_math_oracles.py",)),
    Mutation("calculate_distance", NOISE_MATH, "drop the altitude term",
             "delta_northing ** 2 + delta_easting ** 2 + altitude ** 2", "delta_northing ** 2 + delta_easting ** 2",
             ("tests/noise/test_noise_math_oracles.py",)),
    Mutation("calculate_mixed_noise_level", NOISE_MATH, "10*log10 of the energy sum -> 20*log10",
             "return 10.0 * np.log10(linear_sum)", "return 20.0 * np.log10(linear_sum)",
             ("tests/noise/test_noise_math_oracles.py",)),
    Mutation("add_two_decibel_levels", NOISE_MATH, "10*log10 of the energy sum -> 20*log10",
             "return 10.0 * np.log10((10.0 ** (first_dbl_level", "return 20.0 * np.log10((10.0 ** (first_dbl_level",
             ("tests/noise/test_noise_math_oracles.py",)),
    Mutation("calculate_leq", NOISE_MATH, "energy mean -> energy sum",
             "np.mean(10.0 ** (noise_levels_db / 10.0))", "np.sum(10.0 ** (noise_levels_db / 10.0))",
             ("tests/noise/test_noise_math_oracles.py",)),
    Mutation("calculate_sound_exposure_level", NOISE_MATH, "drop the time step",
             "np.sum(10.0 ** (noise_levels_db / 10.0)) * time_step_s", "np.sum(10.0 ** (noise_levels_db / 10.0))",
             ("tests/noise/test_sound_exposure_level.py",)),
    Mutation("sum_inverse_squared_distances (altitude)", ENERGY_NOISE, "drop the altitude term",
             "delta_northing * delta_northing + delta_easting * delta_easting + sample_squared_altitudes_m2[sample]",
             "delta_northing * delta_northing + delta_easting * delta_easting",
             ("tests/noise/test_energy_noise.py",)),
    Mutation("sum_inverse_squared_distances (floor)", ENERGY_NOISE, "distance floor becomes a ceiling",
             "1.0 / max(squared_distance_m2, minimum_squared_distance_m2)",
             "1.0 / min(squared_distance_m2, minimum_squared_distance_m2)",
             ("tests/noise/test_energy_noise.py",)),
    Mutation("calculate_equivalent_levels_db", ENERGY_NOISE, "drop the division by the number of time steps",
             "np.log10(inverse_squared_distance_sums / number_of_time_steps)", "np.log10(inverse_squared_distance_sums)",
             ("tests/noise/test_energy_noise.py",)),
    Mutation("combine_levels_db", EXPOSURE, "10*log10 of the energy sum -> 20*log10",
             "return 10.0 * np.log10(10.0 ** (first_levels_db", "return 20.0 * np.log10(10.0 ** (first_levels_db",
             ("tests/metrics/test_exposure_metrics.py",)),
    Mutation("calculate_mean_noise_increase_db", EXPOSURE, "mean -> median",
             "return np.mean(combine_levels_db(", "return np.median(combine_levels_db(",
             ("tests/metrics/test_exposure_metrics.py",)),
    Mutation("find_newly_exposed_cells", EXPOSURE, "drop the 'baseline below threshold' condition",
             "return (combined_levels_db > threshold_db) & (baseline_levels_db < threshold_db)",
             "return combined_levels_db > threshold_db",
             ("tests/metrics/test_exposure_metrics.py",)),
    Mutation("calculate_population_inside_contour", EXPOSURE, ">= contour -> > contour",
             "drone_levels_db >= contour_level_db", "drone_levels_db > contour_level_db",
             ("tests/metrics/test_exposure_metrics.py",)),
    Mutation("summarise_replicates", REPLICATION, "sample SD (ddof=1) -> population SD (ddof=0)",
             "    standard_deviation = np.std(values, ddof=1)\n    return ReplicateSummary(",
             "    standard_deviation = np.std(values, ddof=0)\n    return ReplicateSummary(",
             ("tests/metrics/test_replication_statistics.py",)),
    Mutation("calculate_confidence_half_width", REPLICATION, "drop the division by sqrt(n)",
             "* standard_deviation / np.sqrt(number_of_replicates)", "* standard_deviation",
             ("tests/metrics/test_replication_statistics.py",)),
    Mutation("calculate_required_replicates", REPLICATION, "relative target applied to the SD instead of the mean",
             "target_half_width = relative_half_width * abs(np.mean(values))",
             "target_half_width = relative_half_width * abs(np.std(values, ddof=1))",
             ("tests/metrics/test_replication_statistics.py",)),
    Mutation("assign_warehouse_indices", "src/orders/seeded_order_pool.py", "closest uses argmax",
             "warehouses).argmin(axis=1)", "warehouses).argmax(axis=1)",
             ("tests/orders/test_seeded_order_pool.py",)),
    Mutation("summarise_run (utilisation)", "src/simulation/run_statistics.py", "drop the duration from the denominator",
             "(sum(drones_by_warehouse.values()) * simulated_duration_s)", "(sum(drones_by_warehouse.values()))",
             ("tests/simulation/test_run_statistics.py",)),
    Mutation("allocate_fleet_in_proportion_to_orders", "src/simulation/fleet_allocation.py", "floor of the quota -> ceil",
             "drones = [math.floor(quota) for quota in quotas]", "drones = [math.ceil(quota) for quota in quotas]",
             ("tests/simulation/test_fleet_allocation.py",)),
    Mutation("place_depots_on_ring", "src/depots/depot_layouts.py", "northing uses cos instead of sin",
             "northing=centre.northing + radius_m * math.sin(bearing_rad)",
             "northing=centre.northing + radius_m * math.cos(bearing_rad)",
             ("tests/depots/test_depot_layouts.py",)),
    Mutation("calculate_population_weighted_centre", "src/depots/depot_layouts.py", "unweighted easting",
             "easting=np.average(eastings, weights=population)", "easting=np.average(eastings)",
             ("tests/depots/test_depot_layouts.py",)),
    Mutation("StraightLinePlanner.plan_route", "src/route_planner/straight_line_planner.py", "time = distance * speed",
             "total_time = distance / self.speed_mps", "total_time = distance * self.speed_mps",
             ("tests/route_planner/test_straight_line_planner.py",)),
    Mutation("ModelConfig.intermediate_altitudes_ascending", "src/common/model_configs.py", "ladder spacing h/(n+1)",
             "return [h * (i / n) for i in range(0, n)]", "return [h * (i / (n + 1)) for i in range(0, n)]",
             ("tests/route_planner/test_landing_planner.py",)),
    Mutation("rebase_baseline_default", POSTPROCESSING, "shift the mapped share instead of the unmapped share",
             "(new_default_db - PUBLISHED_BASELINE_DEFAULT_DB) * (1.0 - mapped_share)",
             "(new_default_db - PUBLISHED_BASELINE_DEFAULT_DB) * mapped_share",
             ("tests/metrics/test_map_postprocessing.py",)),
    Mutation("summarise_per_thousand_deliveries", POSTPROCESSING, "drop the factor 1,000",
             "value * DELIVERIES_PER_REPORTING_UNIT / delivered_orders", "value / delivered_orders",
             ("tests/metrics/test_map_postprocessing.py",)),
    Mutation("summarise_exposure_by_distance_band", POSTPROCESSING, "'within' selects cells beyond the limit",
             '(("within", distances_to_centre_m <= distance_limit_m)', '(("within", distances_to_centre_m >= distance_limit_m)',
             ("tests/metrics/test_map_postprocessing.py",)),
    Mutation("calculate_low_altitude_energy_shares", DIAGNOSTICS, "select samples above the altitude limit",
             "samples.altitudes_m < altitude_limit_m", "samples.altitudes_m > altitude_limit_m",
             ("tests/noise/test_energy_diagnostics.py",)),
    Mutation("calculate_event_exposure_levels_db", DIAGNOSTICS, "drop the time step",
             "np.log10(energy_sums * time_step_s)", "np.log10(energy_sums)",
             ("tests/noise/test_energy_diagnostics.py",)),
    Mutation("summarise_straight_pass", "src/experiments/revision/single_event_checks.py",
             "energy mean over receivers -> arithmetic mean of decibels",
             "10.0 * np.log10(np.mean(10.0 ** (levels_db / 10.0)))", "np.mean(levels_db)",
             ("tests/experiments/test_single_event_checks.py",)),
    Mutation("summarise_round_trip_times", PHASE8_TABLES, "seconds per delivery uses a product",
             'runs["airborne_drone_seconds"] / runs["delivered_orders"]', 'runs["airborne_drone_seconds"] * runs["delivered_orders"]',
             ("tests/experiments/test_phase8_tables.py",)),
    Mutation("compare_time_steps", PHASE8_TABLES, "recommend when the run time ratio is above the limit",
             'table["wall_time_ratio"] < MAXIMUM_WALL_TIME_RATIO', 'table["wall_time_ratio"] > MAXIMUM_WALL_TIME_RATIO',
             ("tests/experiments/test_phase8_tables.py",)),
    Mutation("compare_variants_with_baseline", "src/experiments/revision/reduced_design.py", "change = variant + baseline",
             'paired[metric] - paired[f"{metric}_baseline"]', 'paired[metric] + paired[f"{metric}_baseline"]',
             ("tests/experiments/test_reduced_design.py",)),
    Mutation("snap_inside_boundary", "src/depots/depot_layouts.py", "inset pushes the depot outwards",
             "line_from_centre.interpolate(exit_distance_m - inset_m)", "line_from_centre.interpolate(exit_distance_m + inset_m)",
             ("tests/depots/test_depot_layouts.py",)),
)


def apply_mutation(source_text: str, original: str, mutated: str) -> str:
    if source_text.count(original) != 1:
        raise ValueError(f"Expected exactly one occurrence of: {original}")
    return source_text.replace(original, mutated)


def run_tests(test_paths: tuple[str, ...]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *test_paths], cwd=REPOSITORY_ROOT, capture_output=True, text=True
    )


def count_failed_tests(pytest_output: str) -> int:
    return sum(1 for line in pytest_output.splitlines() if line.startswith(("FAILED", "ERROR")))


def check_mutation(mutation: Mutation) -> dict:
    source_file = REPOSITORY_ROOT / mutation.source_path
    original_text = source_file.read_text()
    source_file.write_text(apply_mutation(original_text, mutation.original, mutation.mutated))
    try:
        completed = run_tests(mutation.test_paths)
    finally:
        source_file.write_text(original_text)

    return {
        "function": mutation.function_name, "file": mutation.source_path, "mutation": mutation.description,
        "tests_run": " ".join(mutation.test_paths),
        "outcome": "killed" if completed.returncode != 0 else "SURVIVED",
        "failing_tests": count_failed_tests(completed.stdout),
    }


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    rows = []
    for mutation in MUTATIONS:
        rows.append({**check_mutation(mutation), "git_hash": git_hash})
        print(f"{rows[-1]['outcome']:8s} {mutation.function_name}: {mutation.description}", flush=True)

    ensure_clean_working_tree(REPOSITORY_ROOT)
    write_phase_table(pd.DataFrame(rows), RESULTS_DIRECTORY, "mutation_checks.csv")


if __name__ == "__main__":
    main()
