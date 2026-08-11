"""Shim: the implementation is `rulespec_conformance.conformance_lib`.

Rebinds `sys.modules` rather than re-exporting names, so the two spellings are
one module object. `from X import *` would be a copy, and a test that patches
`conformance_lib.COMPILED_PROFILE_JSON_SCHEMA_ROOT` would then leave the
implementation reading its own unpatched global.

`src/` goes on the path here rather than the package being installed: building
the distribution requires the generated `compiled/` tree, so making dependency
installation depend on a build would deadlock `make compile`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rulespec_conformance import conformance_lib as _impl  # noqa: E402

sys.modules[__name__] = _impl
