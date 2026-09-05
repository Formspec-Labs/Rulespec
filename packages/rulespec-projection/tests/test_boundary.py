"""Freeze the outbound import boundary of ``rulespec_projection``.

The package's price was "zero new dependencies": nothing outside the standard
library, and nothing from the producer it was moved out of. spicy-regs kept
that surface quotable with a frozen list of outbound imports
(``tests/test_rkaf_projection_boundary.py`` at ``8d9e7a2``); this is the same
freeze with the list collapsed to what the port promises, which is nothing.

Outbound means any import whose root package is not in the standard library
and not this package. Relative imports stay inside the package by construction
and are checked to resolve to a sibling module; dynamic imports are refused
because they cross the boundary without naming it.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "rulespec_projection"
MODULES = sorted(PACKAGE_DIR.glob("*.py"))

FROZEN_OUTBOUND_IMPORTS: tuple[tuple[str, tuple[str, ...]], ...] = ()

_FREEZE_RULE = (
    "rulespec_projection is priced at zero dependencies: nothing outside the standard "
    "library, nothing from spicy_regs. Changing that is a deliberate act: decide the "
    "boundary move first, then update FROZEN_OUTBOUND_IMPORTS and the package's "
    "pyproject dependencies in the same change. Do not edit the freeze to make a red "
    "test go green."
)


def _outbound_imports(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    outbound: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            outbound.extend(
                (alias.name, ())
                for alias in node.names
                if alias.name.partition(".")[0] not in sys.stdlib_module_names
            )
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.partition(".")[0] not in sys.stdlib_module_names:
                outbound.append((node.module, tuple(sorted(alias.name for alias in node.names))))
    return sorted(outbound)


class BoundaryTests(unittest.TestCase):
    def test_the_package_has_modules_to_freeze(self) -> None:
        self.assertTrue(MODULES, f"no modules under {PACKAGE_DIR}")

    def test_no_module_imports_outside_the_standard_library(self) -> None:
        actual = sorted(entry for module in MODULES for entry in _outbound_imports(module))
        self.assertEqual(actual, sorted(FROZEN_OUTBOUND_IMPORTS), _FREEZE_RULE)

    def test_relative_imports_name_a_sibling_module(self) -> None:
        names = {path.stem for path in MODULES}
        for module in MODULES:
            tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    with self.subTest(module=module.name, line=node.lineno):
                        self.assertEqual(node.level, 1, "only one level of relative import exists here")
                        self.assertIn(node.module, names, f"{module.name} imports a module that is not in the package")

    def test_no_dynamic_imports(self) -> None:
        for module in MODULES:
            tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
            dynamic = [
                f"line {node.lineno}"
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and (
                    (isinstance(node.func, ast.Attribute) and node.func.attr in {"import_module", "__import__"})
                    or (isinstance(node.func, ast.Name) and node.func.id in {"__import__", "import_module"})
                )
            ]
            with self.subTest(module=module.name):
                self.assertEqual(dynamic, [], _FREEZE_RULE)

    def test_importing_the_package_loads_no_third_party_module(self) -> None:
        script = (
            "import sys; import rulespec_projection; "
            "print(sorted(name for name in sys.modules "
            "if name.partition('.')[0] not in sys.stdlib_module_names "
            "and not name.startswith('rulespec_projection') and not name.startswith('_')))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONPATH": str(PACKAGE_DIR.parent), "PYTHONSAFEPATH": "1"},
        )
        self.assertEqual(completed.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
