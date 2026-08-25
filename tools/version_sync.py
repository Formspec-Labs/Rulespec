#!/usr/bin/env python3
"""Rulespec version sync.

`VERSION` is the single source of truth. This script propagates that value
into every other call site, or verifies they're already in sync.

Call sites kept in lock-step:
  - crates/Cargo.toml         (workspace.package.version)
  - crates/Cargo.lock         (every workspace member package)
  - context/rkaf-context.jsonld  (top-level "version" field)
  - pyproject.toml            (project.version, the rulespec-conformance wheel)

Rust source files and tests read `env!("CARGO_PKG_VERSION")` so they auto-track
the workspace version; they are not touched here.

CHANGELOG.md is human-narrated and not touched here.

Usage:
  python3 tools/version_sync.py --check    # exit 1 on any drift; CI gate
  python3 tools/version_sync.py --write    # rewrite call sites to match VERSION

Exit codes:
  0  all call sites match VERSION (or --write succeeded)
  1  drift detected (--check) or write failed (--write)
  2  setup error (missing VERSION, parse failure)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

# Regex anchored on the workspace.package block so we don't touch any nested
# `version = ...` lines elsewhere in the workspace TOML.
WORKSPACE_VERSION_RE = re.compile(
    r"(\[workspace\.package\][^\[]*?\nversion\s*=\s*)\"[^\"]*\"",
    re.DOTALL,
)

# The [project] table's span, then its `version` line within that span. Table
# headers are matched at line start rather than on any `[`, because a value in
# the table may itself be an array (`classifiers = [...]`) — a `[^\[]*?` guard
# stops at the first one and silently misses the version line beyond it.
PROJECT_TABLE_RE = re.compile(r"^\[project\][^\n]*\n(.*?)(?=^\[|\Z)", re.M | re.S)
PROJECT_VERSION_LINE_RE = re.compile(r"^(version\s*=\s*)\"([^\"]*)\"", re.M)


def read_truth() -> str:
    if not VERSION_FILE.is_file():
        print(f"setup: {VERSION_FILE} missing", file=sys.stderr)
        sys.exit(2)
    v = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not v:
        print(f"setup: {VERSION_FILE} is empty", file=sys.stderr)
        sys.exit(2)
    return v


def sync_cargo_toml(truth: str, write: bool) -> bool:
    path = ROOT / "crates" / "Cargo.toml"
    src = path.read_text(encoding="utf-8")
    m = WORKSPACE_VERSION_RE.search(src)
    if not m:
        print(f"  [SKIP] {path.relative_to(ROOT)} — no [workspace.package] version line", file=sys.stderr)
        return True
    current = re.search(r'"([^"]*)"', m.group(0)).group(1)
    if current == truth:
        return True
    if not write:
        print(f"  [DRIFT] {path.relative_to(ROOT)}: {current!r} != {truth!r}")
        return False
    new = WORKSPACE_VERSION_RE.sub(rf'\1"{truth}"', src, count=1)
    path.write_text(new, encoding="utf-8")
    print(f"  [WROTE] {path.relative_to(ROOT)}: {current!r} → {truth!r}")
    return True


def sync_jsonld_context(truth: str, write: bool) -> bool:
    path = ROOT / "context" / "rkaf-context.jsonld"
    if not path.is_file():
        return True
    src = path.read_text(encoding="utf-8")
    doc = json.loads(src)
    meta = doc.get("_meta")
    if not isinstance(meta, dict):
        print(f"  [SKIP] {path.relative_to(ROOT)} — no _meta block", file=sys.stderr)
        return True
    current = meta.get("version")
    expected = f"v{truth}"  # the jsonld context uses the `v`-prefixed form
    if current == expected:
        return True
    if not write:
        print(f"  [DRIFT] {path.relative_to(ROOT)} (_meta.version): {current!r} != {expected!r}")
        return False
    meta["version"] = expected
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  [WROTE] {path.relative_to(ROOT)}: {current!r} → {expected!r}")
    return True


def sync_pyproject(truth: str, write: bool) -> bool:
    """Keep the `rulespec-conformance` distribution on VERSION.

    The raw string propagates unchanged: PEP 440 normalises `0.2.0-pre.N` to
    `0.2.0rcN`, so no translation is needed here.
    """

    path = ROOT / "pyproject.toml"
    if not path.is_file():
        return True
    src = path.read_text(encoding="utf-8")
    # tomllib decides what the version IS; the regex only performs the rewrite.
    # Reading it with the regex alone meant any array before `version` inside
    # [project] produced a no-match, and a no-match that returns True is a gate
    # that reports "in sync" while the file drifts.
    current = tomllib.loads(src).get("project", {}).get("version")
    if not isinstance(current, str):
        print(f"  [FAIL] {path.relative_to(ROOT)} — no [project] version", file=sys.stderr)
        return False
    if current == truth:
        return True
    table = PROJECT_TABLE_RE.search(src)
    line = PROJECT_VERSION_LINE_RE.search(table.group(1)) if table else None
    if line is None or line.group(2) != current:
        print(
            f"  [FAIL] {path.relative_to(ROOT)} — cannot locate the version line to rewrite",
            file=sys.stderr,
        )
        return False
    if not write:
        print(f"  [DRIFT] {path.relative_to(ROOT)}: {current!r} != {truth!r}")
        return False
    start = table.start(1)
    updated = src[:start] + PROJECT_VERSION_LINE_RE.sub(
        rf'\1"{truth}"', src[start:table.end(1)], count=1
    ) + src[table.end(1):]
    path.write_text(updated, encoding="utf-8")
    print(f"  [WROTE] {path.relative_to(ROOT)}: {current!r} → {truth!r}")
    return True


def sync_cargo_lock(truth: str, write: bool) -> bool:
    """Keep every workspace member package in Cargo.lock on VERSION.

    Dependency versions remain untouched. The member list comes from the
    workspace manifest so a newly added in-tree crate automatically enters
    this gate.
    """

    manifest_path = ROOT / "crates" / "Cargo.toml"
    lock_path = ROOT / "crates" / "Cargo.lock"
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    members = {
        Path(member).name
        for member in manifest.get("workspace", {}).get("members", [])
        if isinstance(member, str)
    }
    src = lock_path.read_text(encoding="utf-8")
    block_re = re.compile(
        r'(\[\[package\]\]\nname = "([^"]+)"\nversion = ")([^"]+)(")',
    )
    drift: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        name, current = match.group(2), match.group(3)
        if name not in members or current == truth:
            return match.group(0)
        drift.append((name, current))
        return f"{match.group(1)}{truth}{match.group(4)}"

    updated = block_re.sub(replace, src)
    if not drift:
        return True
    if not write:
        for name, current in drift:
            print(f"  [DRIFT] crates/Cargo.lock ({name}): {current!r} != {truth!r}")
        return False
    lock_path.write_text(updated, encoding="utf-8")
    print(
        "  [WROTE] crates/Cargo.lock: "
        + ", ".join(f"{name} {current!r} → {truth!r}" for name, current in drift)
    )
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="exit 1 on any drift")
    mode.add_argument("--write", action="store_true", help="rewrite call sites to match VERSION")
    args = ap.parse_args()

    truth = read_truth()
    print(f"truth: VERSION = {truth!r}")

    syncs = [sync_cargo_toml, sync_cargo_lock, sync_jsonld_context, sync_pyproject]
    ok = True
    for fn in syncs:
        if not fn(truth, write=args.write):
            ok = False

    if args.check and not ok:
        print("\nDRIFT detected. Run `python3 tools/version_sync.py --write` to fix.", file=sys.stderr)
        return 1
    if args.write and not ok:
        return 1
    if args.check:
        print("\nAll call sites in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
