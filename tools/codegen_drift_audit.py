#!/usr/bin/env python3
"""Codegen drift audit — Rust canonical tree must match CUE source.

Snapshots `crates/rkaf-core/src/generated/`, runs `tools/compile_all.sh`
against current CUE source, and compares the resulting bytes with the
snapshot. A failure means a CUE edit has not been regenerated or a generated
file was hand-edited. Legitimate uncommitted CUE plus generated changes pass
when they are already in lock-step.

Run from Rulespec repo root. Exits:
  0  generated tree matches CUE source — codegen is in lock-step
  1  drift detected — show diff stat for human triage
  2  setup error (compiler missing, git not available, etc.)

This audit is the safety net the duplicate `compiled/rust/core/` tree
masked for as long as it existed: two stale copies confirmed each other
while drifting from CUE.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

GENERATED_TREE = Path("crates/rkaf-core/src/generated")
DRIVER = Path("tools/compile_all.sh")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _snapshot() -> dict[Path, bytes]:
    return {
        path.relative_to(GENERATED_TREE): path.read_bytes()
        for path in sorted(GENERATED_TREE.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    if not DRIVER.exists():
        print(f"ERROR: missing {DRIVER}", file=sys.stderr)
        return 2
    if not GENERATED_TREE.is_dir():
        print(f"ERROR: missing {GENERATED_TREE}", file=sys.stderr)
        return 2

    before = _snapshot()
    drive = _run(["bash", str(DRIVER)])
    if drive.returncode != 0:
        print("ERROR: compile_all.sh failed:", file=sys.stderr)
        sys.stderr.write(drive.stderr)
        return 2
    after = _snapshot()

    changed = sorted(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )
    if not changed:
        print(f"OK: codegen lock-step ({GENERATED_TREE}, no drift)")
        return 0

    print("DRIFT DETECTED — generated Rust tree does not match CUE source.\n")
    print("Files changed by regeneration:")
    for path in changed:
        if path not in before:
            status = "A"
        elif path not in after:
            status = "D"
        else:
            status = "M"
        print(f"{status} {GENERATED_TREE / path}")
    print()
    print("Resolution: keep the regenerated files, review the diff, and rerun")
    print("this audit. The second run should pass when source and output agree.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
