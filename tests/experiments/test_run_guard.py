import subprocess

import pytest

from experiments.revision.run_guard import (
    DirtyWorkingTreeError,
    FailingTestSuiteError,
    ensure_clean_working_tree,
    ensure_fast_suite_passes,
    read_git_hash,
)


def run_git(repository, *arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=repository, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path):
    run_git(tmp_path, "init", "--quiet")
    run_git(tmp_path, "config", "user.email", "tester@example.org")
    run_git(tmp_path, "config", "user.name", "Tester")
    (tmp_path / "tracked.txt").write_text("first version\n")
    run_git(tmp_path, "add", "tracked.txt")
    run_git(tmp_path, "commit", "--quiet", "-m", "initial")
    return tmp_path


def test_git_hash_is_the_head_commit(repository):
    """Expected value: `git rev-parse HEAD` asked directly."""
    assert read_git_hash(repository) == run_git(repository, "rev-parse", "HEAD")
    assert len(read_git_hash(repository)) == 40


def test_clean_tree_is_accepted(repository):
    ensure_clean_working_tree(repository)


def test_modified_tracked_file_is_refused(repository):
    (repository / "tracked.txt").write_text("second version\n")
    with pytest.raises(DirtyWorkingTreeError, match="tracked.txt"):
        ensure_clean_working_tree(repository)


def test_untracked_file_is_refused(repository):
    (repository / "new_module.py").write_text("VALUE = 1\n")
    with pytest.raises(DirtyWorkingTreeError, match="new_module.py"):
        ensure_clean_working_tree(repository)


def test_passing_suite_is_accepted(repository):
    (repository / "test_passing.py").write_text("def test_truth():\n    assert True\n")
    ensure_fast_suite_passes(repository)


def test_failing_suite_is_refused(repository):
    (repository / "test_failing.py").write_text("def test_falsehood():\n    assert False\n")
    with pytest.raises(FailingTestSuiteError):
        ensure_fast_suite_passes(repository)
