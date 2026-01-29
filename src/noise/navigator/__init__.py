from __future__ import annotations

from common.enum import NavigationType
from noise.navigator.cached_routes_navigator import CachedRoutesNavigator
from noise.navigator.cost_function_generator import WeightSpec, make_mixed_distance_noise_weight
from noise.navigator.navigator_base import BaseNavigator
from noise.navigator.warehouse_route_cache_generator import WarehouseRouteCacheGenerator


def _mixed_alpha_for_mode(mode: NavigationType) -> float:
    if mode == NavigationType.MIXED_A025:
        return 0.25
    if mode == NavigationType.MIXED_A050:
        return 0.50
    if mode == NavigationType.MIXED_A075:
        return 0.75
    if mode == NavigationType.MIXED_A100:
        return 1.00
    return 0.50


def _is_mixed_mode(mode: NavigationType) -> bool:
    return mode in {
        NavigationType.MIXED,
        NavigationType.MIXED_A025,
        NavigationType.MIXED_A050,
        NavigationType.MIXED_A075,
        NavigationType.MIXED_A100,
    }


def _default_mixed_weight_id(alpha: float, dist_key: str, noise_key: str, higher_noise_is_better: bool) -> str:
    return f"mixed__a={alpha:.2f}__dist={dist_key}__noise={noise_key}__hnib={int(higher_noise_is_better)}"


def get_navigator(
    mode: NavigationType = NavigationType.HEAVY_NOISE,
    dataset_path: str | None = None,
    weight: WeightSpec | None = None,
    weight_id: str | None = None,
    compute_on_miss: bool = False,
) -> BaseNavigator:
    if _is_mixed_mode(mode):
        alpha = _mixed_alpha_for_mode(mode)

        dist_key = "distance"
        noise_key = "noise"
        higher_noise_is_better = False

        if weight_id is None:
            weight_id = _default_mixed_weight_id(alpha, dist_key, noise_key, higher_noise_is_better)

        def builder(graph):
            return make_mixed_distance_noise_weight(
                graph=graph,
                alpha=alpha,
                dist_keys=(dist_key,),
                noise_keys=(noise_key,),
                higher_noise_is_better=higher_noise_is_better,
            )

        return WarehouseRouteCacheGenerator(weight_builder=builder, weight_id=weight_id)

    if mode == NavigationType.HEAVY_NOISE:
        return WarehouseRouteCacheGenerator(weight=weight, weight_id=weight_id)

    if mode == NavigationType.LIGHT_NOISE:
        return CachedRoutesNavigator(
            order_route_path=dataset_path,
            build_with_heavy=compute_on_miss,
            save_on_build=True,
            heavy=WarehouseRouteCacheGenerator(weight=weight, weight_id=weight_id) if compute_on_miss else None,
        )

    raise ValueError(f"Unknown navigator mode: {mode}")
