"""Shim: the implementation is `rulespec_conformance.reference_release_digest`.

Aliases for the reason given in `tools/conformance_lib.py`.
"""

import sys

from rulespec_conformance import reference_release_digest as _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

sys.modules[__name__] = _impl
