"""Loads modules exactly as they were at the published baseline commit, for characterisation tests."""
import subprocess
import sys
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
    compiled_source = compile(read_legacy_source(relative_source_path), f"legacy:{relative_source_path}", "exec")
    with substituted_modules(legacy_dependencies or {}):
        exec(compiled_source, module.__dict__)
    return module
