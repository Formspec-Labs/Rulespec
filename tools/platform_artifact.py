"""Shim: the implementation is `rulespec_conformance.platform_artifact`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rulespec_conformance import platform_artifact as _impl  # noqa: E402

sys.modules[__name__] = _impl
