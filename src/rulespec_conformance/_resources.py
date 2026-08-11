"""Where the conformance data lives.

Two layouts, separated by one test: `_data/` exists only in a built wheel,
where the build backend force-includes `compiled/`, `shapes/`, `fixtures/`
and the JSON-LD context into it. In a source tree it is absent and the
repository root is used, so the tooling under `tools/` reads the same files
the compiler writes. Nothing is copied into the source tree.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGED_DATA = Path(__file__).resolve().parent / "_data"


def data_root() -> Path:
    """The directory holding `compiled/`, `shapes/` and `fixtures/`."""
    if _PACKAGED_DATA.is_dir():
        return _PACKAGED_DATA
    # src/rulespec_conformance/_resources.py -> src/rulespec_conformance -> src -> repo
    return Path(__file__).resolve().parents[2]
