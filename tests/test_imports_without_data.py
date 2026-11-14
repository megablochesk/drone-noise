"""Importing the model must not read data files; only running something may.

Every library module is imported in a fresh interpreter started in an empty directory, where the relative
data paths of the model do not exist.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SOURCE_DIRECTORY = Path(__file__).resolve().parent.parent / "src"
# Scripts that run an experiment, open a window or change the working directory when imported.
SCRIPT_MODULE_PREFIXES = (
    "application",
    "noise_graph_routes_generator",
    "warehouse_voronoi_diagram_builder",
    "experiments.non_simulation_based_experiments",
    "experiments.simulation_based_experiments",
)
NON_PACKAGE_DIRECTORIES = ("recourses", "_recent", "figures", "__pycache__")
IMPORT_PROGRAM = """
import importlib, json, sys
failures = {}
for name in sys.argv[1:]:
    try:
        importlib.import_module(name)
    except BaseException as error:
        failures[name] = f"{type(error).__name__}: {error}"
print("FAILURES " + json.dumps(failures))
"""


def find_library_modules() -> list[str]:
    modules = []
    for path in sorted(SOURCE_DIRECTORY.rglob("*.py")):
        relative_path = path.relative_to(SOURCE_DIRECTORY)
        name = ".".join(relative_path.with_suffix("").parts)
        is_library_module = (
            path.stem != "__init__"
            and relative_path.parts[0] not in NON_PACKAGE_DIRECTORIES
            and not name.startswith(SCRIPT_MODULE_PREFIXES)
        )
        if is_library_module:
            modules.append(name)
    return modules


def test_library_modules_import_from_a_directory_without_data(tmp_path):
    modules = find_library_modules()
    completed = subprocess.run(
        [sys.executable, "-c", IMPORT_PROGRAM, *modules], cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(SOURCE_DIRECTORY), "DRONE_NOISE_MATPLOTLIB_BACKEND": "Agg"},
    )
    report = [line for line in completed.stdout.splitlines() if line.startswith("FAILURES ")]

    assert len(modules) > 80
    assert report, completed.stderr[-2000:]
    assert json.loads(report[-1].removeprefix("FAILURES ")) == {}
    assert list(tmp_path.iterdir()) == []
