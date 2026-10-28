"""Expose sibling tools to unittest discovery without a repository-wide PYTHONPATH."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
