from __future__ import annotations

from common.enum import NavigationType
from noise.navigator.cached_routes_navigator import CachedRoutesNavigator
from noise.navigator.cost_function_generator import WeightSpec, make_mixed_distance_noise_weight
from noise.navigator.navigator_base import BaseNavigator
from noise.navigator.warehouse_route_cache_generator import WarehouseRouteCacheGenerator

_NAV_CACHE: dict[tuple, BaseNavigator] = {}


def clear_navigator_cache():
    _NAV_CACHE.clear()


def _mixed_alpha_for_mode(mode: NavigationType):
    if mode == NavigationType.NOISE_A025:
        return 0.25
    if mode == NavigationType.NOISE_A050:
        return 0.50
    if mode == NavigationType.NOISE_A075:
        return 0.75
    if mode == NavigationType.NOISE_A100:
        return 1.00
    return NotImplementedError


def _is_mixed_mode(mode: NavigationType) -> bool:
    return mode in {
        NavigationType.NOISE_A025,
        NavigationType.NOISE_A050,
        NavigationType.NOISE_A075,
        NavigationType.NOISE_A100,
    }


def _default_mixed_weight_id(alpha: float, dist_key: str, noise_key: str, higher_noise_is_better: bool) -> str:
    return f"mixed__a={alpha:.2f}__dist={dist_key}__noise={noise_key}__hnib={int(higher_noise_is_better)}"


def _cache_get(key: tuple) -> BaseNavigator | None:
    return _NAV_CACHE.get(key)


def _cache_put(key: tuple, nav: BaseNavigator) -> BaseNavigator:
    _NAV_CACHE[key] = nav
    return nav


def get_navigator(
    mode: NavigationType,
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

        key = ("mixed", mode.name, weight_id)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        def builder(graph):
            return make_mixed_distance_noise_weight(
                graph=graph,
                alpha=alpha,
                dist_keys=(dist_key,),
                noise_keys=(noise_key,),
                higher_noise_is_better=higher_noise_is_better,
            )

        navigator = WarehouseRouteCacheGenerator(weight_builder=builder, weight_id=weight_id)
        return _cache_put(key, navigator)

    if mode == NavigationType.UNCACHED_NAVIGATOR:
        key = ("heavy", weight_id)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        navigator = WarehouseRouteCacheGenerator(weight=weight, weight_id=weight_id)
        return _cache_put(key, navigator)

    if mode == NavigationType.CACHED_NAVIGATOR:
        compute_routes = None
        if compute_on_miss:
            compute_routes = get_navigator(mode=NavigationType.UNCACHED_NAVIGATOR, weight=weight, weight_id=weight_id)

        key = ("light", dataset_path, bool(compute_on_miss), weight_id)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        navigator = CachedRoutesNavigator(
            order_route_path=dataset_path,
            build_with_heavy=compute_on_miss,
            save_on_build=True,
            heavy=compute_routes if compute_on_miss else None,
        )
        return _cache_put(key, navigator)

    raise ValueError(f"Unknown navigator mode: {mode}")
