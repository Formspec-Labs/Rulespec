"""Shim: the implementation is `rulespec_conformance.conformance_lib`.

Rebinds `sys.modules` rather than re-exporting names, so the two spellings are
one module object. `from X import *` would be a copy, and a test that patches
`conformance_lib.COMPILED_PROFILE_JSON_SCHEMA_ROOT` would then leave the
implementation reading its own unpatched global.
"""

import sys

from rulespec_conformance import conformance_lib as _impl

sys.modules[__name__] = _impl
