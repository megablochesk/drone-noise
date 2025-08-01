from .base import BaseNavigator
from .heavy import HeavyNavigator
from .light import LightNavigator

def get_navigator(mode: str = "heavy", pickle_path: str | None = None) -> BaseNavigator:
    if mode == "heavy":
        return HeavyNavigator()

    if mode == "light":
        return LightNavigator(pickle_path)

    raise ValueError(f"Unknown navigator mode: {mode}")
