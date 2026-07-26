#!/usr/bin/env python3
"""Mechanically generate "missing required field" negative fixtures.

For each codified class discovered by `conformance_lib.schema_bindings()`
(kernel plus every compiled domain profile), walks the schema's
`required` list and emits one negative fixture per required field, with the
field stripped. Output: `fixtures/negatives/<class>-missing-<field>-negative.jsonld`.

Starting from a hand-authored positive fixture preserves the surrounding
context (other valid properties, plausible IRIs); we just remove the one
required field under test.

Usage:
  python3 tools/generate_negatives.py
  python3 tools/generate_negatives.py --dry-run

Exit codes:
  0  generated (or dry-run) successfully
  1  no positive fixture found for some class
  2  setup error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from conformance_lib import (
    FIXTURES_DIR,
    SchemaBinding,
    iter_nodes,
    load_json,
    positive_fixture_paths,
    schema_bindings,
)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = FIXTURES_DIR / "negatives"


def _safe_filename(field: str) -> str:
    """Convert `rkaf:hasArtifactIdentifier` → `has-artifact-identifier`."""
    s = re.sub(r"^[a-z]+:", "", field)
    s = re.sub(r"@", "", s)
    s = re.sub(r"([A-Z])", r"-\1", s).lower().lstrip("-")
    return re.sub(r"[^a-z0-9-]+", "-", s).strip("-")


def _strip_field_from_node(node: dict, field: str) -> dict:
    """Return a deep copy of `node` with `field` removed. Preserves all
    other fields."""
    result = {k: v for k, v in node.items() if k != field}
    return result


def _find_target_node(doc: dict, target_type: str) -> dict | None:
    """Locate the node in a fixture document whose `@type` matches
    `target_type`. Single-node fixtures return as-is; `@graph` envelopes
    return the first matching node."""
    if doc.get("@type") == target_type:
        return doc
    graph = doc.get("@graph")
    if isinstance(graph, list):
        for n in graph:
            if isinstance(n, dict) and n.get("@type") == target_type:
                return n
    return None


def _find_positive_fixture(target_type: str) -> Path | None:
    for path in positive_fixture_paths():
        doc = load_json(path)
        if not doc:
            continue
        if any(node.get("@type") == target_type for node in iter_nodes(doc, include_behavior_input=False)):
            return path
    return None


def _rewrap(original: dict, modified_node: dict, target_type: str) -> dict:
    """Reinsert `modified_node` back into the document structure (single-node
    or `@graph` envelope) without disturbing other content."""
    if original.get("@type") == target_type:
        # Single-node fixture; swap the document for the modified node, keeping
        # @context if it was at the root.
        new = dict(modified_node)
        if "@context" in original and "@context" not in new:
            new["@context"] = original["@context"]
        return new
    new_doc = {k: v for k, v in original.items() if k != "@graph"}
    new_graph = []
    for n in original.get("@graph", []):
        if isinstance(n, dict) and n.get("@type") == target_type:
            new_graph.append(modified_node)
        else:
            new_graph.append(n)
    new_doc["@graph"] = new_graph
    return new_doc


def generate_for_class(binding: SchemaBinding, dry_run: bool) -> tuple[list[Path], bool]:
    """Generate one negative fixture per required field of `class_name`."""
    schema = json.loads(binding.schema_path.read_text())
    cls = schema.get("$defs", {}).get(binding.class_name)
    if not isinstance(cls, dict):
        return [], False
    required = cls.get("required", [])
    if not required:
        return [], False

    target_type = binding.type_iri
    positive_path = _find_positive_fixture(target_type)
    if positive_path is None:
        print(f"  [MISSING] {binding.class_name}: no positive fixture with @type={target_type}",
              file=sys.stderr)
        return [], True
    original = json.loads(positive_path.read_text())
    target_node = _find_target_node(original, target_type)
    if target_node is None:
        print(f"  [MISSING] {binding.class_name}: no @type={target_type} node in fixture",
              file=sys.stderr)
        return [], True

    written: list[Path] = []
    missing = False
    for field in required:
        if field == "@type":
            continue  # stripping @type would change the document into a non-Rulespec node
        if field not in target_node:
            print(
                f"  [MISSING] {binding.class_name}: positive fixture "
                f"{positive_path.relative_to(ROOT)} lacks required field {field}",
                file=sys.stderr,
            )
            missing = True
            continue
        modified = _strip_field_from_node(target_node, field)
        new_doc = _rewrap(original, modified, target_type)
        slug = _safe_filename(field)
        # Slug from the JSON-LD `@type`, not the bound class name. The two agree
        # for kernel shapes, but a profile overlay binds a class of its own
        # (`USRegulatoryArtifact` for `rkaf:Artifact`) — slugging from the class
        # would mint a second, mis-named `u-s-regulatory-artifact-*` family
        # alongside the `artifact-*` fixtures already on disk. The fixture is
        # named for the class of document it is a negative FOR.
        cls_slug = _safe_filename(binding.type_iri)
        out_path = OUT_DIR / f"{cls_slug}-missing-{slug}-negative.jsonld"
        if dry_run:
            print(f"  [DRY ] {out_path.relative_to(ROOT)}")
        else:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(new_doc, indent=2) + "\n")
            print(f"  [WROTE] {out_path.relative_to(ROOT)}")
        written.append(out_path)
    return written, missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be generated without writing")
    args = ap.parse_args()

    total = 0
    missing = False
    for binding in sorted(schema_bindings().values(), key=lambda b: b.class_name):
        written, has_missing = generate_for_class(binding, args.dry_run)
        total += len(written)
        missing = missing or has_missing

    print(f"\nGenerated {total} negative fixtures{' (dry-run)' if args.dry_run else ''}.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
