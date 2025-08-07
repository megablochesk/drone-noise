"""Configuration constants for visualisation charts."""

# Order in which datasets appear in charts
DATASET_TYPE_BAR_ORDER = ["furthest", "closest", "random"]

# Human readable labels for datasets
DATASET_TYPE_TO_LEGEND = {
    "furthest": "worst",
    "closest": "best",
    "random": "random",
}

__all__ = ["DATASET_TYPE_BAR_ORDER", "DATASET_TYPE_TO_LEGEND"]
