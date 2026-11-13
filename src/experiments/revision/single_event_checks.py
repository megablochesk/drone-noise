"""Phase 8d: sound exposure of one straight pass and of one delivery, as the model samples them."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from common.coordinate import Coordinate
from common.enum import NoiseCalculation
from common.model_configs import ModelConfig
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from noise.energy_diagnostics import calculate_event_exposure_levels_db, select_samples
from noise.energy_noise import FlightSamples
from orders.order import Order
from route_planner.straight_line_planner import StraightLinePlanner
from simulation.simulator import Simulator

FEET_TO_METRES = 0.3048
REFERENCE_WAREHOUSE = Coordinate(northing=182_049.78, easting=538_402.03)
PASS_INTERVALS = 100
DELIVERY_INTERVALS = 10
RECEIVER_SPACING_M = 1.0


@dataclass(frozen=True)
class SimulatedDelivery:
    samples: FlightSamples
    destination: Coordinate
    model: ModelConfig


def sample_spacing_m(model: ModelConfig) -> float:
    return model.drone.speed_mps * model.time.step_s


def destination_east_of_reference(distance_m: float) -> Coordinate:
    return Coordinate(northing=REFERENCE_WAREHOUSE.northing, easting=REFERENCE_WAREHOUSE.easting + distance_m)


def place_receivers_across_track(destination: Coordinate, horizontal_distances_m: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Receivers due north of the destination; the reference track runs east-west."""
    northings = destination.northing + np.array(horizontal_distances_m, dtype=np.float64)
    return northings, np.full(len(horizontal_distances_m), destination.easting)


def simulate_single_delivery(model: ModelConfig, terminal_phases: bool) -> SimulatedDelivery:
    """One drone flies one order with the real simulator; returns every position it was sampled at."""
    destination = destination_east_of_reference(DELIVERY_INTERVALS * sample_spacing_m(model))
    order = Order(order_id=1, start_location=REFERENCE_WAREHOUSE, end_location=destination)
    config = SimulationConfig(
        number_of_drones=1, print_model_stats=False, drone_landing=terminal_phases,
        noise_calculation=NoiseCalculation.ENERGY_SUM, model=model,
    )
    with use_simulation_config(config):
        simulator = Simulator(warehouse_locations=[REFERENCE_WAREHOUSE], orders=[order])
        simulator.run()
    return SimulatedDelivery(simulator.noise_monitor.tracker.samples, destination, model)


def select_samples_at_destination(delivery: SimulatedDelivery) -> FlightSamples:
    at_destination = (
        (delivery.samples.northings == delivery.destination.northing)
        & (delivery.samples.eastings == delivery.destination.easting)
    )
    return select_samples(delivery.samples, at_destination)


def summarise_terminal_event(delivery: SimulatedDelivery, horizontal_distances_ft: list[float]) -> pd.DataFrame:
    """SEL at receivers beside the customer: from the samples at the customer only, and from the whole trip."""
    drone, time_step_s = delivery.model.drone, delivery.model.time.step_s
    distances_m = [distance_ft * FEET_TO_METRES for distance_ft in horizontal_distances_ft]
    northings, eastings = place_receivers_across_track(delivery.destination, distances_m)
    terminal_samples = select_samples_at_destination(delivery)
    return pd.DataFrame({
        "horizontal_distance_ft": horizontal_distances_ft,
        "horizontal_distance_m": distances_m,
        "samples_at_destination": len(terminal_samples.altitudes_m),
        "terminal_event_sel_db": calculate_event_exposure_levels_db(
            northings, eastings, terminal_samples, drone.noise_at_source_db, time_step_s
        ),
        "whole_delivery_sel_db": calculate_event_exposure_levels_db(
            northings, eastings, delivery.samples, drone.noise_at_source_db, time_step_s
        ),
    })


def sample_straight_pass(model: ModelConfig) -> FlightSamples:
    """Waypoints of one long straight leg as planned by the model, all at cruise altitude."""
    with use_simulation_config(SimulationConfig(model=model)):
        route = StraightLinePlanner().plan_route(
            REFERENCE_WAREHOUSE, destination_east_of_reference(PASS_INTERVALS * sample_spacing_m(model))
        )
    return FlightSamples(
        northings=np.array([waypoint.northing for waypoint in route]),
        eastings=np.array([waypoint.easting for waypoint in route]),
        altitudes_m=np.full(len(route), model.drone.flight_altitude_m),
    )


def summarise_straight_pass(model: ModelConfig) -> dict:
    """SEL under the track for receivers spread over one sample spacing in the middle of the leg."""
    spacing_m = sample_spacing_m(model)
    middle_easting = REFERENCE_WAREHOUSE.easting + (PASS_INTERVALS // 2) * spacing_m
    receiver_eastings = middle_easting + np.arange(0.0, spacing_m, RECEIVER_SPACING_M)
    receiver_northings = np.full(len(receiver_eastings), REFERENCE_WAREHOUSE.northing)
    levels_db = calculate_event_exposure_levels_db(
        receiver_northings, receiver_eastings, sample_straight_pass(model),
        model.drone.noise_at_source_db, model.time.step_s,
    )
    return {
        "time_step_s": model.time.step_s,
        "sample_spacing_m": spacing_m,
        "minimum_sel_db": levels_db.min(),
        "maximum_sel_db": levels_db.max(),
        "energy_mean_sel_db": 10.0 * np.log10(np.mean(10.0 ** (levels_db / 10.0))),
        "closed_form_sel_db": model.drone.noise_at_source_db + 10.0 * math.log10(
            math.pi / (model.drone.speed_mps * model.drone.flight_altitude_m)
        ),
    }
