from common.enum import NavigationType
from .base import BaseNavigator
from .heavy import HeavyNavigator
from .light import LightNavigator

def get_navigator(mode: NavigationType = NavigationType.HEAVY_NOISE, dataset_path: str | None = None) -> BaseNavigator | None:
    navigators = {
        NavigationType.HEAVY_NOISE: lambda: HeavyNavigator(),
        NavigationType.LIGHT_NOISE: lambda: LightNavigator(dataset_path),
        NavigationType.STRAIGHT: lambda: None
    }

    try:
        return navigators[mode]()
    except KeyError:
        raise ValueError(f"Unknown navigator mode: {mode}")
