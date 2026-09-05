"""Every ``rkaf:`` term rulespec-projection emits must exist in the term registry.

The projection writes RKAF by name: its vocabulary is string literals typed
into the package, not imports from the schema, because the package is priced
at zero dependencies and the contract module ships in the conformance wheel.
That leaves one silent failure: rename a term in the CUE and the producer keeps
emitting the old one with no error anywhere. This test is the error. It reads
the package's source, collects every ``rkaf:``-prefixed literal, and refuses
any that the generated contract registry (``contract.terms`` and
``contract.enums``, rebuilt by ``tools/build_contract_exports.py``) does not
declare.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rulespec_conformance.contract import enums, terms  # noqa: E402

PACKAGE = ROOT / "packages" / "rulespec-projection" / "src" / "rulespec_projection"
LITERAL = re.compile(r'"(rkaf:[A-Za-z][A-Za-z0-9-]*)"')


def registry() -> frozenset[str]:
    declared: set[str] = set()
    for module in (terms, enums):
        for name in dir(module):
            value = getattr(module, name)
            if isinstance(value, str) and value.startswith("rkaf:"):
                declared.add(value)
            elif isinstance(value, (tuple, list, frozenset, set)):
                declared.update(item for item in value if isinstance(item, str) and item.startswith("rkaf:"))
    return frozenset(declared)


def emitted() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for module in sorted(PACKAGE.glob("*.py")):
        for line_number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            for term in LITERAL.findall(line):
                found.setdefault(term, []).append(f"{module.name}:{line_number}")
    return found


class ProjectionTermTests(unittest.TestCase):
    def test_the_package_emits_terms(self) -> None:
        self.assertGreater(len(emitted()), 50)

    def test_every_emitted_term_is_declared_by_the_contract(self) -> None:
        declared = registry()
        self.assertGreater(len(declared), 500)
        unknown = {term: sites for term, sites in emitted().items() if term not in declared}
        self.assertEqual(
            unknown,
            {},
            "rulespec-projection emits rkaf: terms the contract registry does not declare; "
            "either the term moved in the CUE (update the package) or the registry is stale "
            "(rerun tools/build_contract_exports.py)",
        )


if __name__ == "__main__":
    unittest.main()
