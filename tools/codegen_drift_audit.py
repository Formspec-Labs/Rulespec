#!/usr/bin/env python3
"""Codegen drift audit — Rust canonical tree must match CUE source.

Runs `tools/compile_all.sh` against current CUE source, then asserts that
`crates/rkaf-core/src/generated/` has no git-modified or git-untracked
files. A failure means: a CUE edit landed without its generated Rust
counterpart, or someone hand-edited a generated file. Either is a
release-gate failure.

Run from Rulespec repo root. Exits:
  0  generated tree matches CUE source — codegen is in lock-step
  1  drift detected — show diff stat for human triage
  2  setup error (compiler missing, git not available, etc.)

This audit is the safety net the duplicate `compiled/rust/core/` tree
masked for as long as it existed: two stale copies confirmed each other
while drifting from CUE.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

GENERATED_TREE = Path("crates/rkaf-core/src/generated")
DRIVER = Path("tools/compile_all.sh")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def main() -> int:
    if not DRIVER.exists():
        print(f"ERROR: missing {DRIVER}", file=sys.stderr)
        return 2
    if not shutil.which("git"):
        print("ERROR: git not on PATH", file=sys.stderr)
        return 2
    if not GENERATED_TREE.is_dir():
        print(f"ERROR: missing {GENERATED_TREE}", file=sys.stderr)
        return 2

    drive = _run(["bash", str(DRIVER)])
    if drive.returncode != 0:
        print("ERROR: compile_all.sh failed:", file=sys.stderr)
        sys.stderr.write(drive.stderr)
        return 2

    status = _run(["git", "status", "--porcelain", str(GENERATED_TREE)])
    if status.returncode != 0:
        print("ERROR: git status failed:", file=sys.stderr)
        sys.stderr.write(status.stderr)
        return 2

    drifted = status.stdout.strip()
    if not drifted:
        print(f"OK: codegen lock-step ({GENERATED_TREE}, no drift)")
        return 0

    print("DRIFT DETECTED — generated Rust tree does not match CUE source.\n")
    print("Files out of sync (git status --porcelain):")
    print(drifted)
    print()
    print("Resolution: commit the regenerated files, OR identify why the")
    print("compiler produced different output than the tracked version")
    print("(usually: a CUE edit forgot to regen, or a generated file was")
    print("hand-edited).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
