import shutil
import subprocess
from pathlib import Path

import pytest

from datasets.data_catalogue import DATA_CATALOGUE
from experiments.revision.run_guard import (
    DirtyWorkingTreeError,
    FailingTestSuiteError,
    RepositoryChangedError,
    ensure_clean_working_tree,
    ensure_fast_suite_passes,
    ensure_ready_to_run,
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
    (tmp_path / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    run_git(tmp_path, "add", "tracked.txt", ".gitignore")
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


def test_ready_repository_returns_the_commit_to_cite(repository):
    """Clean tree and passing suite: the returned hash is HEAD."""
    (repository / "test_passing.py").write_text("def test_truth():\n    assert True\n")
    run_git(repository, "add", "test_passing.py")
    run_git(repository, "commit", "--quiet", "-m", "add a passing test")
    assert ensure_ready_to_run(repository) == run_git(repository, "rev-parse", "HEAD")


def test_commit_made_while_the_suite_runs_is_refused(repository):
    """The cited commit must be the code that was checked: if HEAD moves during the checks, refuse."""
    (repository / "test_commits.py").write_text(
        "import subprocess\n\n"
        "def test_moves_head():\n"
        "    subprocess.run(['git', 'commit', '--quiet', '--allow-empty', '-m', 'sneaky'], check=True)\n"
    )
    run_git(repository, "add", "test_commits.py")
    run_git(repository, "commit", "--quiet", "-m", "add a test that commits")
    with pytest.raises(RepositoryChangedError):
        ensure_ready_to_run(repository)


def test_file_created_while_the_suite_runs_is_refused(repository):
    """Likewise an edit that appears during the checks leaves the tree dirty and must be refused."""
    (repository / "test_writes.py").write_text(
        "from pathlib import Path\n\n"
        "def test_leaves_a_file():\n"
        "    Path('left_behind.txt').write_text('x')\n"
    )
    run_git(repository, "add", "test_writes.py")
    run_git(repository, "commit", "--quiet", "-m", "add a test that writes")
    with pytest.raises(DirtyWorkingTreeError, match="left_behind.txt"):
        ensure_ready_to_run(repository)


REPOSITORY_GITIGNORE = Path(__file__).resolve().parents[2] / ".gitignore"
FILES_A_CLUSTER_CHECKOUT_HOLDS_BESIDE_THE_CODE = (
    *(f"src/{data_file.relative_path}" for data_file in DATA_CATALOGUE),
    "src/recourses/data/noise_graph_navigation/warehouse_paths_cache__mixed__a_0_25__dist_distance__noise_noise__hnib_0.pkl",
    "results/artifacts/runs/0123456789abcdef.json",
    "results/artifacts/runs/0123456789abcdef_drone_levels.npz",
    "results/artifacts/runs/0123456789abcdef_trips.parquet",
    "results/artifacts/grids/0123456789abcdef.npz",
    "results/artifacts/order_pools/destinations_population_seed31_n650000.parquet",
    "slurm-123456_17.out",
    "src/experiments/revision/__pycache__/run_fine_grid_task.cpython-312.pyc",
)


@pytest.fixture
def fresh_clone(tmp_path):
    """A repository that has only the tracked ignore rules: a clone has no .git/info/exclude of this machine."""
    run_git(tmp_path, "init", "--quiet")
    run_git(tmp_path, "config", "user.email", "tester@example.org")
    run_git(tmp_path, "config", "user.name", "Tester")
    run_git(tmp_path, "config", "core.excludesFile", "/dev/null")
    shutil.copy(REPOSITORY_GITIGNORE, tmp_path / ".gitignore")
    run_git(tmp_path, "add", ".gitignore")
    run_git(tmp_path, "commit", "--quiet", "-m", "initial")
    return tmp_path


def test_a_clone_with_input_data_results_and_job_logs_counts_as_clean(fresh_clone):
    """Cluster tasks refuse a dirty tree, so the input files copied in, the runs they store and their Slurm logs
    must all be ignored by the rules that travel with the repository."""
    for relative_path in FILES_A_CLUSTER_CHECKOUT_HOLDS_BESIDE_THE_CODE:
        path = fresh_clone / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n")

    ensure_clean_working_tree(fresh_clone)
