from .base import BaseNavigator
from .heavy import HeavyNavigator
from .light import LightNavigator

def get_navigator(mode: str = "heavy", dataset_path: str | None = None) -> BaseNavigator | None:
    if mode == "heavy":
        return HeavyNavigator()

    if mode == "light":
        return LightNavigator(dataset_path)

    if mode == "straight":
        return None

    raise ValueError(f"Unknown navigator mode: {mode}")
