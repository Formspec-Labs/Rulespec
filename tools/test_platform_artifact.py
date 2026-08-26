"""Run the standalone artifact package's owner tests in the repository gate."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "rulespec-artifacts" / "src"))
sys.path.insert(0, str(_ROOT / "packages" / "rulespec-artifacts" / "tests"))

from test_artifact import *  # noqa: E402,F403
