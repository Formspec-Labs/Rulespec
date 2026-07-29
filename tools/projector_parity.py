#!/usr/bin/env python3
"""Projector parity orchestrator (Rulespec Layer 4).

For every `round-trip-*.{jsonld,yaml}` fixture under
`fixtures/projectors/<target>/`, invoke the `projector-harness` CLI to
run Attach → Extract on the matching projector and assert that round-trip
identity holds. Then run the same valid and invalid
`ConceptResolutionResult` through every target's Validate operation so no
carrier can silently bypass the shared generated constraints.

Targets:
  - json-schema  (fixtures: *.jsonld)
  - json-ld      (fixtures: *.jsonld)
  - openapi      (fixtures: *.yaml)

Exit codes:
  0  every fixture round-trips
  1  ≥1 fixture failed round-trip
  2  setup error (harness binary missing, etc.)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "crates/target/debug/projector-harness"

TARGETS = {
    "json-schema": ("jsonld",),
    "json-ld":     ("jsonld",),
    "openapi":     ("yaml",),
}


def ensure_harness() -> int | None:
    if HARNESS.exists():
        return None
    print(f"setup: harness binary not found at {HARNESS}", file=sys.stderr)
    print("       run: cargo build --manifest-path crates/Cargo.toml -p projector-harness",
          file=sys.stderr)
    return 2


def run_round_trip(target: str, fixture: Path) -> bool:
    res = subprocess.run(
        [str(HARNESS), "--target", target, "round-trip", "--fixture", str(fixture)],
        capture_output=True,
        cwd=ROOT,
    )
    return res.returncode == 0


def run_validate(target: str, fixture: Path) -> bool:
    res = subprocess.run(
        [str(HARNESS), "--target", target, "validate", "--fixture", str(fixture)],
        capture_output=True,
        cwd=ROOT,
    )
    return res.returncode == 0


def main() -> int:
    err = ensure_harness()
    if err is not None:
        return err

    fails = 0
    total = 0
    for target, exts in TARGETS.items():
        d = ROOT / "fixtures" / "projectors" / target
        if not d.is_dir():
            continue
        files: list[Path] = []
        for ext in exts:
            files.extend(sorted(d.glob(f"round-trip-*.{ext}")))
        for f in files:
            total += 1
            ok = run_round_trip(target, f)
            tag = "OK" if ok else "FAIL"
            print(f"  [{tag}] {target}/round-trip {f.name}")
            if not ok:
                fails += 1

    validation_cases = [
        (ROOT / "fixtures" / "conceptresolutionresult-positive.jsonld", True),
        (
            ROOT
            / "fixtures"
            / "negatives"
            / "concept-resolution-result-broad-resolved-negative.jsonld",
            False,
        ),
    ]
    for target in TARGETS:
        for fixture, expected_valid in validation_cases:
            total += 1
            actual_valid = run_validate(target, fixture)
            ok = actual_valid == expected_valid
            tag = "OK" if ok else "FAIL"
            expectation = "PASS" if expected_valid else "FAIL"
            print(
                f"  [{tag}] {target}/validate "
                f"{fixture.name} expected={expectation}"
            )
            if not ok:
                fails += 1

    print(f"\n{total - fails}/{total} projector parity checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
