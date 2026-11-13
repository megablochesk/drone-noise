"""Preconditions for starting experiments: committed code and a green fast test suite."""
import subprocess
import sys
from pathlib import Path


class DirtyWorkingTreeError(RuntimeError):
    pass


class FailingTestSuiteError(RuntimeError):
    pass


def run_git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=repository, capture_output=True, text=True, check=True)
    return completed.stdout


def read_git_hash(repository: Path) -> str:
    return run_git(repository, "rev-parse", "HEAD").strip()


def ensure_clean_working_tree(repository: Path):
    uncommitted_changes = run_git(repository, "status", "--porcelain").strip()
    if uncommitted_changes:
        raise DirtyWorkingTreeError(f"Commit or remove these changes before running experiments:\n{uncommitted_changes}")


def ensure_fast_suite_passes(repository: Path):
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x"], cwd=repository, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise FailingTestSuiteError(f"The fast test suite fails:\n{completed.stdout[-2000:]}")


def ensure_ready_to_run(repository: Path) -> str:
    """Returns the commit hash that the results of this batch must cite."""
    ensure_clean_working_tree(repository)
    ensure_fast_suite_passes(repository)
    return read_git_hash(repository)
