from __future__ import annotations

import gc
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from threading import Event, Thread
from typing import Any

import pandas as pd
import psutil

from common.coordinate import Coordinate
from common.enum import NavigationType
from common.file_utils import load_dataframe_from_pickle, save_dataframe_to_pickle
from common.path_configs import get_experiment_results_full_file_path
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from noise.navigator import clear_navigator_cache
from simulation.planned_route_cache import PlannedRouteCache, PlannedRouteCacheStats
from simulation.simulator import Simulator
from visualiser.plot_utils import finalise_visualisation


@dataclass(frozen=True)
class DatasetExperimentGroupKey:
    dataset_name: str
    dataset_path: str
    drone_landing_enabled: bool


@dataclass(frozen=True)
class MemoryUsageSummary:
    start_rss_bytes: int
    end_rss_bytes: int
    peak_rss_bytes: int


class ProcessMemoryMonitor:
    def __init__(self, sampling_interval_seconds: float = 1.0):
        self._sampling_interval_seconds = sampling_interval_seconds
        self._process = psutil.Process() if psutil is not None else None
        self._stop_event = Event()
        self._monitor_thread: Thread | None = None
        self._start_rss_bytes = 0
        self._peak_rss_bytes = 0

    @property
    def enabled(self) -> bool:
        return self._process is not None

    def start(self):
        if not self.enabled:
            return

        self._stop_event.clear()
        self._start_rss_bytes = self._read_current_rss_bytes()
        self._peak_rss_bytes = self._start_rss_bytes
        self._monitor_thread = Thread(target=self._monitor_memory_usage, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> MemoryUsageSummary | None:
        if not self.enabled:
            return None

        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join()
            self._monitor_thread = None

        end_rss_bytes = self._read_current_rss_bytes()
        peak_rss_bytes = max(self._peak_rss_bytes, end_rss_bytes)
        return MemoryUsageSummary(
            start_rss_bytes=self._start_rss_bytes,
            end_rss_bytes=end_rss_bytes,
            peak_rss_bytes=peak_rss_bytes,
        )

    def _monitor_memory_usage(self):
        while not self._stop_event.wait(self._sampling_interval_seconds):
            self._peak_rss_bytes = max(self._peak_rss_bytes, self._read_current_rss_bytes())

    def _read_current_rss_bytes(self) -> int:
        return self._process.memory_info().rss


def run_complex_experiment(
    result_file_name,
    load_saved_results,
    experiment_function=None,
    visualisation_function=None,
    configs_with_names=None,
):
    if configs_with_names is not None:
        def wrapped_experiment():
            return _run_experiments_for_configs(configs_with_names)
        experiment_function = wrapped_experiment

    if experiment_function is None:
        raise ValueError("Either experiment_function or configs_with_names must be provided")

    results = _load_or_run_experiment(result_file_name, load_saved_results, experiment_function)
    _visualise_results(results, visualisation_function, result_file_name=result_file_name)


def _run_experiments_for_configs(configs_with_names):
    grouped_configs = _group_by_navigation_type_and_dataset(configs_with_names)

    results = []
    for navigation_type_name in sorted(grouped_configs.keys()):
        dataset_groups = grouped_configs[navigation_type_name]
        print(
            f"\n=== Running navigation type group: navigation_type={navigation_type_name} "
            f"(datasets={len(dataset_groups)}) ==="
        )

        for dataset_group_key in _sort_dataset_group_keys(dataset_groups):
            dataset_runs = dataset_groups[dataset_group_key]
            results.extend(
                _run_dataset_group(
                    navigation_type_name=navigation_type_name,
                    dataset_group_key=dataset_group_key,
                    runs=dataset_runs,
                )
            )

        _clear_navigation_level_caches(navigation_type_name)

    return results


def _group_by_navigation_type_and_dataset(configs_with_names):
    grouped_configs = defaultdict(lambda: defaultdict(list))

    for run_name, config in configs_with_names:
        navigation_type_name = _nav_to_name(config.navigator_type)
        dataset_group_key = DatasetExperimentGroupKey(
            dataset_name=_dataset_type_from_run_name(run_name),
            dataset_path=config.order_dataset_path,
            drone_landing_enabled=config.drone_landing,
        )
        grouped_configs[navigation_type_name][dataset_group_key].append((run_name, config))

    return {
        navigation_type_name: dict(dataset_groups)
        for navigation_type_name, dataset_groups in grouped_configs.items()
    }


def _sort_dataset_group_keys(dataset_groups):
    return sorted(
        dataset_groups.keys(),
        key=lambda dataset_group_key: (
            dataset_group_key.dataset_name,
            dataset_group_key.dataset_path,
            dataset_group_key.drone_landing_enabled,
        ),
    )


def _run_dataset_group(
    navigation_type_name: str,
    dataset_group_key: DatasetExperimentGroupKey,
    runs: list[tuple[str, SimulationConfig]],
):
    planned_route_cache = _create_planned_route_cache(navigation_type_name)
    ordered_runs = _sort_runs_by_descending_drone_count(runs)
    memory_monitor = ProcessMemoryMonitor()

    max_orders_to_process = max(config.orders_to_process for _, config in ordered_runs)
    active_warehouse_locations = _load_active_warehouse_locations(
        dataset_path=dataset_group_key.dataset_path,
        number_of_orders=max_orders_to_process,
    )

    print(
        f"\n--- Running dataset group: navigation_type={navigation_type_name}, "
        f"dataset={dataset_group_key.dataset_name}, drone_landing={dataset_group_key.drone_landing_enabled}, "
        f"runs={len(ordered_runs)}, "
        f"planned_route_cache={'enabled' if planned_route_cache is not None else 'disabled'}, "
        f"active_warehouses={len(active_warehouse_locations)} ---"
    )

    dataset_results = []
    memory_monitor.start()
    try:
        for run_name, config in ordered_runs:
            dataset_results.append(
                _run_atomic_experiment(
                    run_name=run_name,
                    config=config,
                    planned_route_cache=planned_route_cache,
                    warehouse_locations=active_warehouse_locations,
                )
            )
    finally:
        memory_usage_summary = memory_monitor.stop()
        cache_stats = _get_planned_route_cache_stats(planned_route_cache)
        _log_dataset_group_summary(
            navigation_type_name=navigation_type_name,
            dataset_group_key=dataset_group_key,
            cache_stats=cache_stats,
            memory_usage_summary=memory_usage_summary,
        )
        _clear_planned_route_cache(planned_route_cache)
        _log_memory_after_cache_cleanup(
            navigation_type_name=navigation_type_name,
            dataset_group_key=dataset_group_key,
        )

    return dataset_results


def _load_active_warehouse_locations(dataset_path: str, number_of_orders: int) -> list[Coordinate]:
    data_frame = pd.read_csv(
        dataset_path,
        usecols=["Start Northing", "Start Easting"],
        nrows=number_of_orders,
    )

    unique_pairs = (
        data_frame[["Start Northing", "Start Easting"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    warehouse_locations = [Coordinate(northing, easting) for northing, easting in unique_pairs]
    warehouse_locations.sort(key=lambda coordinate: (coordinate.northing, coordinate.easting))
    return warehouse_locations


def _create_planned_route_cache(navigation_type_name: str) -> PlannedRouteCache | None:
    if navigation_type_name == NavigationType.STRAIGHT.name:
        return None
    return PlannedRouteCache()


def _sort_runs_by_descending_drone_count(runs):
    return sorted(
        runs,
        key=lambda run: (-run[1].number_of_drones, run[0]),
    )


def _run_atomic_experiment(
    run_name: str,
    config: SimulationConfig,
    planned_route_cache: PlannedRouteCache | None = None,
    warehouse_locations=None,
):
    start_time = time.time()

    with use_simulation_config(config):
        simulator_after_run = _run_simulation(
            planned_route_cache=planned_route_cache,
            warehouse_locations=warehouse_locations,
        )

        elapsed_time = time.time() - start_time
        return _extract_experiment_results(
            simulator_after_run,
            run_name,
            elapsed_time,
            config,
        )


def _run_simulation(planned_route_cache: PlannedRouteCache | None = None, warehouse_locations=None):
    simulator = Simulator(
        planned_route_cache=planned_route_cache,
        warehouse_locations=warehouse_locations,
    )
    simulator.run()
    return simulator


def _extract_experiment_results(simulator_after_run, run_name, elapsed_time, config):
    dataset_type = _dataset_type_from_run_name(run_name)

    noise_impact_df = simulator_after_run.noise_monitor.impact
    avg_noise_difference = noise_impact_df["noise_difference"].mean()

    return {
        "dataset": dataset_type,
        "dataset_name": dataset_type,
        "run_name": run_name,
        "num_drones": config.number_of_drones,
        "num_orders": config.orders_to_process,
        "navigation_type": _nav_to_name(config.navigator_type),
        "avg_noise_diff": avg_noise_difference,
        "noise_impact_df": noise_impact_df,
        "delivered_orders_number": simulator_after_run.delivered_orders_number,
        "execution_time_seconds": elapsed_time,
    }


def _get_planned_route_cache_stats(planned_route_cache: PlannedRouteCache | None) -> PlannedRouteCacheStats | None:
    if planned_route_cache is None:
        return None

    return planned_route_cache.get_stats()


def _log_dataset_group_summary(
    navigation_type_name: str,
    dataset_group_key: DatasetExperimentGroupKey,
    cache_stats: PlannedRouteCacheStats | None,
    memory_usage_summary: MemoryUsageSummary | None,
):
    print(
        f"\nDataset group summary: navigation_type={navigation_type_name}, "
        f"dataset={dataset_group_key.dataset_name}, "
        f"drone_landing={dataset_group_key.drone_landing_enabled}"
    )

    if cache_stats is None:
        print("  Planned route cache: disabled")
    else:
        print(
            "  Planned route cache: "
            f"entries={cache_stats.entry_count}, "
            f"hits={cache_stats.hit_count}, "
            f"misses={cache_stats.miss_count}, "
            f"requests={cache_stats.request_count}, "
            f"hit_rate={cache_stats.hit_rate:.2%}"
        )

    if memory_usage_summary is None:
        print("  Memory usage: unavailable (psutil not installed)")
        return

    print(
        "  Memory usage: "
        f"start_rss={_format_bytes(memory_usage_summary.start_rss_bytes)}, "
        f"end_rss={_format_bytes(memory_usage_summary.end_rss_bytes)}, "
        f"peak_rss={_format_bytes(memory_usage_summary.peak_rss_bytes)}, "
        f"peak_growth={_format_bytes(memory_usage_summary.peak_rss_bytes - memory_usage_summary.start_rss_bytes)}"
    )


def _clear_planned_route_cache(planned_route_cache: PlannedRouteCache | None):
    if planned_route_cache is None:
        return

    planned_route_cache.clear()
    gc.collect()


def _log_memory_after_cache_cleanup(
    navigation_type_name: str,
    dataset_group_key: DatasetExperimentGroupKey,
):
    current_rss_bytes = _read_current_process_rss_bytes()
    if current_rss_bytes is None:
        return

    print(
        "  Memory after cache cleanup: "
        f"navigation_type={navigation_type_name}, "
        f"dataset={dataset_group_key.dataset_name}, "
        f"rss={_format_bytes(current_rss_bytes)}"
    )


def _clear_navigation_level_caches(navigation_type_name: str):
    clear_navigator_cache()
    gc.collect()

    current_rss_bytes = _read_current_process_rss_bytes()
    if current_rss_bytes is not None:
        print(
            f"Memory after navigator cleanup: navigation_type={navigation_type_name}, "
            f"rss={_format_bytes(current_rss_bytes)}"
        )


def _read_current_process_rss_bytes() -> int | None:
    if psutil is None:
        return None

    return psutil.Process().memory_info().rss


def _format_bytes(size_in_bytes: int) -> str:
    negative_prefix = "-" if size_in_bytes < 0 else ""
    absolute_size = abs(size_in_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while absolute_size >= 1024 and unit_index < len(units) - 1:
        absolute_size /= 1024
        unit_index += 1

    return f"{negative_prefix}{absolute_size:.2f} {units[unit_index]}"


def _load_or_run_experiment(result_file_name, load_saved_results, experiment_function):
    file_path = get_experiment_results_full_file_path(result_file_name)

    if load_saved_results:
        print(f"Loading results from file: {result_file_name}")
        return _load_results(file_path)

    print(f"Running experiment and saving results to: {result_file_name}")
    return _run_and_store_experiment(experiment_function, file_path)


def _load_results(file_path):
    df = load_dataframe_from_pickle(file_path)
    return _ensure_results_schema(df)


def _run_and_store_experiment(experiment_function, file_path):
    raw_results = experiment_function()
    results_df = _convert_results_to_dataframe(raw_results)
    results_df = _ensure_results_schema(results_df)

    save_dataframe_to_pickle(results_df, file_path)

    return results_df


def _convert_results_to_dataframe(results):
    if isinstance(results, dict):
        return pd.DataFrame([results])
    return pd.DataFrame(results)


def _visualise_results(results, visualisation_function=None, result_file_name: str | None = None):
    if visualisation_function is None:
        return

    print("Running visualisation on experiment results...")
    results = _ensure_results_schema(results)
    visualisation_function(results)

    output_directory = _build_experiment_figure_output_directory(result_file_name)
    finalise_visualisation(output_directory=output_directory)


def _build_experiment_figure_output_directory(result_file_name: str | None) -> str:
    if not result_file_name:
        return "figures"

    experiment_folder_name = _sanitize_experiment_folder_name(result_file_name)
    return os.path.join("figures", experiment_folder_name)


def _sanitize_experiment_folder_name(result_file_name: str) -> str:
    base_name = os.path.basename(str(result_file_name))
    name_without_extension, _ = os.path.splitext(base_name)

    normalized_name = name_without_extension.strip().replace(" ", "_")
    normalized_name = normalized_name.replace(os.sep, "_")
    if os.altsep:
        normalized_name = normalized_name.replace(os.altsep, "_")

    normalized_name = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized_name)
    normalized_name = re.sub(r"_+", "_", normalized_name).strip("_")
    return normalized_name or "experiment"


def _ensure_results_schema(df: pd.DataFrame) -> pd.DataFrame:
    normalized_results = df.copy()

    if "run_name" not in normalized_results.columns and "dataset_name" in normalized_results.columns:
        normalized_results["run_name"] = normalized_results["dataset_name"].astype(str)

    if "dataset_name" in normalized_results.columns:
        normalized_results["dataset_name"] = normalized_results["dataset_name"].map(_dataset_type_from_run_name)

    if "dataset" not in normalized_results.columns and "dataset_name" in normalized_results.columns:
        normalized_results["dataset"] = normalized_results["dataset_name"]

    if "navigation_type" in normalized_results.columns:
        normalized_results["navigation_type"] = normalized_results["navigation_type"].map(_nav_to_name)

    return normalized_results


def _dataset_type_from_run_name(run_name: Any) -> str:
    run_name_string = str(run_name)
    return run_name_string.split("_d", 1)[0]


def _nav_to_name(value: Any) -> str:
    if isinstance(value, Enum):
        return value.name
    if hasattr(value, "name"):
        name = getattr(value, "name")
        if isinstance(name, str):
            return name
    return str(value)