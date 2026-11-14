"""requirements.txt must let a fresh clone install everything the code and the tests import."""
import ast
import sys
from importlib.metadata import version
from pathlib import Path

from packaging.requirements import Requirement

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_PATH = REPOSITORY_ROOT / "requirements.txt"
SOURCE_DIRECTORIES = [REPOSITORY_ROOT / "src", REPOSITORY_ROOT / "tests"]
DISTRIBUTION_BY_IMPORT_NAME = {"sklearn": "scikit-learn", "mpl_toolkits": "matplotlib", "PIL": "pillow"}


def normalise_distribution_name(name: str) -> str:
    """Distribution names compare case-insensitively with '-' and '_' treated alike (PEP 503)."""
    return name.lower().replace("_", "-")


def read_requirements() -> list[Requirement]:
    lines = REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
    return [Requirement(line) for line in lines if line.strip() and not line.startswith("#")]


def find_local_package_names() -> set[str]:
    local_names = {"tests"}
    for directory in SOURCE_DIRECTORIES:
        local_names |= {path.name for path in directory.iterdir() if path.is_dir()}
        local_names |= {path.stem for path in directory.glob("*.py")}
    return local_names


def find_imported_top_level_names() -> set[str]:
    names = set()
    for directory in SOURCE_DIRECTORIES:
        for path in directory.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names |= {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names.add(node.module.split(".")[0])
    return names


def find_third_party_distributions() -> set[str]:
    third_party_names = find_imported_top_level_names() - set(sys.stdlib_module_names) - find_local_package_names()
    return {normalise_distribution_name(DISTRIBUTION_BY_IMPORT_NAME.get(name, name)) for name in third_party_names}


def test_requirements_file_is_plain_utf8_text():
    text = REQUIREMENTS_PATH.read_bytes()
    assert not text.startswith((b"\xff\xfe", b"\xfe\xff"))
    assert b"\x00" not in text
    assert len(read_requirements()) > 0


def test_every_imported_third_party_package_is_required():
    required = {normalise_distribution_name(requirement.name) for requirement in read_requirements()}
    assert find_third_party_distributions() - required == set()


def test_installed_versions_satisfy_the_requirements():
    """The suite ran in this environment, so the file must describe it."""
    unsatisfied = {
        str(requirement): version(requirement.name)
        for requirement in read_requirements()
        if not requirement.specifier.contains(version(requirement.name))
    }
    assert unsatisfied == {}
