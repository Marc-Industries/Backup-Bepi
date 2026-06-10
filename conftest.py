import os
import sys

# Tests import the `bepi` package from src/. Put it on the path so `pytest`
# works from the repo root without needing PYTHONPATH=src.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
