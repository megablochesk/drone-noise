"""Loads modules exactly as they were at the published baseline commit, for characterisation tests."""
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from contextlib import contextmanager
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_BASELINE_COMMIT = "be58048"


def read_legacy_source(relative_source_path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{PUBLISHED_BASELINE_COMMIT}:src/{relative_source_path}"],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True,
    )
    return completed.stdout


@contextmanager
def substituted_modules(substitutes: dict[str, ModuleType]):
    """Swaps only the named entries of sys.modules; modules imported meanwhile stay registered.

    (patch.dict would also drop every module first imported inside the block, and C extensions such as
    matplotlib's cannot be imported twice.)
    """
    originals = {name: sys.modules.get(name) for name in substitutes}
    sys.modules.update(substitutes)
    try:
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original


def load_legacy_module(relative_source_path: str, legacy_dependencies: dict[str, ModuleType] | None = None) -> ModuleType:
    """Executes the baseline source; `legacy_dependencies` maps import names to other legacy modules."""
    module = ModuleType("legacy_" + Path(relative_source_path).stem)
    # Dataclasses look their module up by name while they are being defined.
    sys.modules[module.__name__] = module
    compiled_source = compile(read_legacy_source(relative_source_path), f"legacy:{relative_source_path}", "exec")
    with substituted_modules(legacy_dependencies or {}):
        exec(compiled_source, module.__dict__)
    return module


@lru_cache(maxsize=1)
def load_legacy_order_generator() -> ModuleType:
    """The published order generator together with the published MSOA module it reads its zones from."""
    legacy_msoa_data = load_legacy_module("census_analysis/msoa_data.py")
    return load_legacy_module(
        "orders/order_generator.py", legacy_dependencies={"census_analysis.msoa_data": legacy_msoa_data}
    )


@lru_cache(maxsize=1)
def load_legacy_fleet() -> ModuleType:
    """The published fleet together with the published planner and route cache it was written against."""
    legacy_route_cache = load_legacy_module("simulation/planned_route_cache.py")
    legacy_planner = load_legacy_module(
        "simulation/planner.py", legacy_dependencies={"simulation.planned_route_cache": legacy_route_cache}
    )
    return load_legacy_module(
        "simulation/fleet.py",
        legacy_dependencies={"simulation.planned_route_cache": legacy_route_cache, "simulation.planner": legacy_planner},
    )
