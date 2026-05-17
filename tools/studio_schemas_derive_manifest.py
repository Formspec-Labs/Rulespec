#!/usr/bin/env python3
"""Orchestrate policy-studio ``schemas-derived/`` from ``schemas-derive-manifest.json``.

Each manifest output declares **provenance** (honest SoT):
  - ``curated`` / ``passthrough_explicit``: read ``source`` (relative to profile dir),
    apply ``x-lm`` → ``x-rkaf-llmHint`` migration, write under ``schemas-derived/<path>``.
  - ``passthrough_explicit`` MUST include ``rationale`` (audit trail).
  - ``fragment_merge`` / ``cue_constraints``: reserved — fail until implemented.

SHA256SUMS: sorted ``path`` keys, one line per file ``<sha256>  ./<relposix>\\n``.

Used by ``policy-studio/profiles/studio/studio_profile_derive.py`` (importlib) when
Rulespec is available as a sibling checkout or configured repository root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROVENANCE_CURATED = "curated"
PROVENANCE_PASSTHROUGH = "passthrough_explicit"
PROVENANCE_FRAGMENT = "fragment_merge"
PROVENANCE_CUE = "cue_constraints"

ALLOWED_PROVENANCE = frozenset(
    {
        PROVENANCE_CURATED,
        PROVENANCE_PASSTHROUGH,
        PROVENANCE_FRAGMENT,
        PROVENANCE_CUE,
    }
)


def _migrate_x_lm(obj: Any) -> Any:
    """Single implementation of Studio ``x-lm`` → ``x-rkaf-llmHint`` (policy-studio imports this module)."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "x-lm":
                out["x-rkaf-llmHint"] = _migrate_x_lm(v)
            else:
                out[k] = _migrate_x_lm(v)
        return out
    if isinstance(obj, list):
        return [_migrate_x_lm(x) for x in obj]
    return obj


def load_manifest(profile_dir: Path) -> dict[str, Any]:
    path = profile_dir / "schemas-derive-manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"unsupported manifest version: {data.get('version')!r}")
    outputs = data.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("manifest.outputs must be a non-empty list")
    return data


def _validate_entry(profile_dir: Path, entry: dict[str, Any], index: int) -> None:
    path = entry.get("path")
    prov = entry.get("provenance")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"outputs[{index}].path must be a non-empty string")
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"outputs[{index}].path must be a relative POSIX path: {path!r}")
    if prov not in ALLOWED_PROVENANCE:
        raise ValueError(f"outputs[{index}].invalid provenance: {prov!r}")

    if prov in (PROVENANCE_FRAGMENT, PROVENANCE_CUE):
        raise NotImplementedError(
            f"outputs[{index}] provenance {prov!r} is not implemented yet "
            "(add orchestration before using in manifest)"
        )

    src = entry.get("source")
    if not isinstance(src, str) or not src.strip():
        raise ValueError(f"outputs[{index}].source required for provenance {prov}")
    sp = Path(src)
    if sp.is_absolute() or ".." in sp.parts:
        raise ValueError(f"outputs[{index}].source must be relative to profile dir: {src!r}")

    if prov == PROVENANCE_PASSTHROUGH:
        rat = entry.get("rationale")
        if not isinstance(rat, str) or not rat.strip():
            raise ValueError(
                f"outputs[{index}].rationale required for passthrough_explicit"
            )

    full = (profile_dir / src).resolve()
    base = profile_dir.resolve()
    try:
        full.relative_to(base)
    except ValueError as e:
        raise ValueError(f"outputs[{index}].source escapes profile dir: {src!r}") from e


def compute_derived(profile_dir: Path) -> tuple[dict[str, bytes], str]:
    """Return (relposix → utf-8 file body, SHA256SUMS body)."""
    profile_dir = profile_dir.resolve()
    data = load_manifest(profile_dir)
    outputs = data["outputs"]
    files: dict[str, bytes] = {}
    seen_paths: set[str] = set()

    for i, raw in enumerate(outputs):
        if not isinstance(raw, dict):
            raise ValueError(f"outputs[{i}] must be an object")
        _validate_entry(profile_dir, raw, i)
        out_rel = raw["path"]
        if out_rel in seen_paths:
            raise ValueError(f"duplicate manifest path: {out_rel!r}")
        seen_paths.add(out_rel)

        src_path = profile_dir / raw["source"]
        if not src_path.is_file():
            raise FileNotFoundError(f"outputs[{i}] missing source file: {src_path}")

        schema = json.loads(src_path.read_text(encoding="utf-8"))
        body = json.dumps(_migrate_x_lm(schema), indent=2, ensure_ascii=False) + "\n"
        files[out_rel] = body.encode("utf-8")

    lines = []
    for rel in sorted(files.keys()):
        digest = hashlib.sha256(files[rel]).hexdigest()
        lines.append(f"{digest}  ./{rel}")
    sums = "\n".join(lines) + "\n"
    return files, sums


def write_derived(profile_dir: Path, files: dict[str, bytes], sums: str) -> None:
    import shutil

    derived = profile_dir / "schemas-derived"
    if derived.exists():
        shutil.rmtree(derived)
    derived.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        dest = derived / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    (derived / "SHA256SUMS").write_text(sums, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Studio schemas-derived manifest orchestrator")
    parser.add_argument("--profile-dir", type=Path, required=True)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write schemas-derived/ (default if neither --check nor --print-count)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare computed bytes to committed schemas-derived/; exit 1 on drift",
    )
    parser.add_argument(
        "--print-count",
        action="store_true",
        help="Print number of manifest outputs to stdout (for sanity checks)",
    )
    args = parser.parse_args()
    profile_dir = args.profile_dir.resolve()

    try:
        files, expected_sums = compute_derived(profile_dir)
    except (FileNotFoundError, ValueError, NotImplementedError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.print_count:
        print(len(files))
        return 0

    if args.check:
        derived = profile_dir / "schemas-derived"
        if not derived.is_dir():
            print(f"missing {derived}", file=sys.stderr)
            return 1
        for rel, content in files.items():
            path = derived / rel
            if not path.is_file():
                print(f"missing derived file {rel}", file=sys.stderr)
                return 1
            if path.read_bytes() != content:
                print(f"drift in {rel}", file=sys.stderr)
                return 1
        for path in derived.rglob("*.schema.json"):
            rel = path.relative_to(derived).as_posix()
            if rel not in files:
                print(f"unexpected file {rel}", file=sys.stderr)
                return 1
        sums_path = derived / "SHA256SUMS"
        if not sums_path.is_file() or sums_path.read_text(encoding="utf-8") != expected_sums:
            print("SHA256SUMS drift", file=sys.stderr)
            return 1
        return 0

    if args.write or (not args.check and not args.print_count):
        write_derived(profile_dir, files, expected_sums)
        print(f"wrote {len(files)} files → {profile_dir / 'schemas-derived'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
