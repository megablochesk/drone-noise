"""Loads modules exactly as they were at the published baseline commit, for characterisation tests."""
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_BASELINE_COMMIT = "be58048"


def read_legacy_source(relative_source_path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{PUBLISHED_BASELINE_COMMIT}:src/{relative_source_path}"],
        cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True,
    )
    return completed.stdout


def load_legacy_module(relative_source_path: str, legacy_dependencies: dict[str, ModuleType] | None = None) -> ModuleType:
    """Executes the baseline source; `legacy_dependencies` maps import names to other legacy modules."""
    module = ModuleType("legacy_" + Path(relative_source_path).stem)
    compiled_source = compile(read_legacy_source(relative_source_path), f"legacy:{relative_source_path}", "exec")
    with patch.dict(sys.modules, legacy_dependencies or {}):
        exec(compiled_source, module.__dict__)
    return module
