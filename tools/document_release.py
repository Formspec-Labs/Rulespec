"""Shim: the implementation is `rulespec_conformance.document_release`.

Aliases for the reason given in `tools/conformance_lib.py`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rulespec_conformance import document_release as _impl  # noqa: E402

sys.modules[__name__] = _impl
