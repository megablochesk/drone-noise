from common.path_configs import MATPLOTLIB_BACKEND_ENVIRONMENT_VARIABLE, resolve_matplotlib_backend


def test_backend_defaults_to_the_interactive_backend_the_code_always_used():
    """Expected value: the literal "Qt5Agg" hard-coded in PathsConfiguration at commit be58048."""
    assert resolve_matplotlib_backend({}) == "Qt5Agg"


def test_backend_follows_the_environment_override():
    """Expected value: the override is returned unchanged (identity, by specification)."""
    environment = {MATPLOTLIB_BACKEND_ENVIRONMENT_VARIABLE: "Agg"}
    assert resolve_matplotlib_backend(environment) == "Agg"
