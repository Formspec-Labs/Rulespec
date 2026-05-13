#!/usr/bin/env python3
"""Projector parity orchestrator (Rulespec Layer 4).

For every `round-trip-*.{jsonld,yaml}` fixture under
`fixtures/v0.2/projectors/<target>/`, invoke the `projector-harness` CLI to
run Attach → Extract on the matching projector and assert that round-trip
identity holds.

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


def main() -> int:
    err = ensure_harness()
    if err is not None:
        return err

    fails = 0
    total = 0
    for target, exts in TARGETS.items():
        d = ROOT / "fixtures" / "v0.2" / "projectors" / target
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

    print(f"\n{total - fails}/{total} round-trip fixtures passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
