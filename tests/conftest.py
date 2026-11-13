import os
from pathlib import Path

SOURCE_DIRECTORY = Path(__file__).resolve().parent.parent / "src"

# The model resolves its data paths relative to src/ and reads several of them at import time.
os.chdir(SOURCE_DIRECTORY)
os.environ["DRONE_NOISE_MATPLOTLIB_BACKEND"] = "Agg"
