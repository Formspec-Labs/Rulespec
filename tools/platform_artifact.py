"""Source-checkout shim for the standalone ``rulespec_artifacts`` package."""

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "packages"
        / "rulespec-artifacts"
        / "src"
    ),
)

import rulespec_artifacts as _impl  # noqa: E402

sys.modules[__name__] = _impl
