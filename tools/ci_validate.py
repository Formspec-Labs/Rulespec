"""Shim: the implementation is `rulespec_conformance.ci_validate`.

The supported entry point is the `rulespec-ci-validate` console script. This
path spelling stays because RefSpec's validator pin invokes
`python tools/ci_validate.py --json <graph>` inside a Rulespec checkout
(`refspec/release_graph.py`).
"""

import sys
from pathlib import Path

try:
    from rulespec_conformance import ci_validate as _impl
except ModuleNotFoundError:  # a checkout with nothing installed
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from rulespec_conformance import ci_validate as _impl

if __name__ == "__main__":
    _impl.main()
else:
    sys.modules[__name__] = _impl
