"""Shim: the implementation is `rulespec_conformance.reference_release_digest`.

Aliases for the reason given in `tools/conformance_lib.py`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rulespec_conformance import reference_release_digest as _impl  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(_impl.cli())

sys.modules[__name__] = _impl
