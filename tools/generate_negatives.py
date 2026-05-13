#!/usr/bin/env python3
"""Mechanically generate "missing required field" negative fixtures.

For each codified class in `compiled/json-schema/core/`, walks the schema's
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

ROOT = Path(__file__).resolve().parent.parent
COMPILED_DIR = ROOT / "compiled" / "json-schema" / "core"
FIXTURES_DIR = ROOT / "fixtures"
OUT_DIR = FIXTURES_DIR / "negatives"


# Class @type IRI → positive fixture stem (relative to fixtures/).
# Many classes share schema files; the mapping is from class name to the
# fixture filename without the .jsonld extension.
_CLASS_TO_FIXTURE: dict[str, str] = {
    "Artifact": "artifact-eli-positive",
    "SourceFragment": "sourcefragment-oa-textquote-positive",
    "EvidenceBinding": "evidencebinding-positive",
    "Warrant": "warrant-legal-positive",
    "ConfidenceRecord": "confidencerecord-calibrated-positive",
    "AccessScope": "accessscope-public-positive",
    "AILineage": "ailineage-positive",
    "Assertion": None,                         # no standalone Assertion positive — appears inside @graph elsewhere
    "RetentionPolicy": "retentionpolicy-positive",
    "MappingState": "mappingstate-positive",
    "Workspace": "workspace-positive",
    "Authority": "authority-positive",
    "Attestation": "attestation-positive",
    "LocalAdoption": "localadoption-positive",
    "ApplicabilityScope": "applicabilityscope-positive",
    "EffectivePeriod": "effectiveperiod-positive",
    "LifecycleEvent": "lifecycleevent-positive",
    "RegisteredConcept": "concept-registered-positive",
    "LocalConcept": None,                      # shares schema with RegisteredConcept; covered by that one
    "ConceptMapping": "conceptmapping-positive",
    "MappingApplicabilityContext": None,       # shares schema with ConceptMapping
    "ConceptResolutionResult": "conceptresolutionresult-positive",
    "BridgeValidationResult": "bridgevalidationresult-positive",
    "BridgeConsumerRegistration": "bridgeconsumerregistration-positive",
    "RegistryConflict": "registryconflict-positive",
    "Justification": "justification-positive",
}


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


def generate_for_class(class_name: str, schema_path: Path, dry_run: bool) -> list[Path]:
    """Generate one negative fixture per required field of `class_name`."""
    schema = json.loads(schema_path.read_text())
    cls = schema.get("$defs", {}).get(class_name)
    if not isinstance(cls, dict):
        return []
    required = cls.get("required", [])
    if not required:
        return []

    fixture_stem = _CLASS_TO_FIXTURE.get(class_name)
    if fixture_stem is None:
        return []
    positive_path = FIXTURES_DIR / f"{fixture_stem}.jsonld"
    if not positive_path.is_file():
        print(f"  [SKIP] {class_name}: no positive fixture at {positive_path.relative_to(ROOT)}",
              file=sys.stderr)
        return []
    target_type = f"rkaf:{class_name}"
    original = json.loads(positive_path.read_text())
    target_node = _find_target_node(original, target_type)
    if target_node is None:
        print(f"  [SKIP] {class_name}: no @type={target_type} node in fixture",
              file=sys.stderr)
        return []

    written: list[Path] = []
    for field in required:
        if field == "@type":
            continue  # stripping @type would change the document into a non-Rulespec node
        modified = _strip_field_from_node(target_node, field)
        new_doc = _rewrap(original, modified, target_type)
        slug = _safe_filename(field)
        cls_slug = re.sub(r"([A-Z])", r"-\1", class_name).lower().lstrip("-")
        out_path = OUT_DIR / f"{cls_slug}-missing-{slug}-negative.jsonld"
        if dry_run:
            print(f"  [DRY ] {out_path.relative_to(ROOT)}")
        else:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(new_doc, indent=2) + "\n")
            print(f"  [WROTE] {out_path.relative_to(ROOT)}")
        written.append(out_path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be generated without writing")
    args = ap.parse_args()

    total = 0
    for class_name, fixture_stem in _CLASS_TO_FIXTURE.items():
        # Find the schema file: try the class-named schema, else the shared schema.
        candidates = [
            COMPILED_DIR / f"{_safe_filename(class_name)}.schema.json",
            COMPILED_DIR / "concept.schema.json"
                if class_name in ("RegisteredConcept", "LocalConcept") else None,
            COMPILED_DIR / "concept-mapping.schema.json"
                if class_name in ("ConceptMapping", "MappingApplicabilityContext") else None,
        ]
        schema_path = None
        for c in candidates:
            if c and c.is_file():
                schema_path = c
                break
        # Fallback: scan all schemas for a $defs entry with this class name.
        if schema_path is None:
            for p in COMPILED_DIR.glob("*.schema.json"):
                schema = json.loads(p.read_text())
                if class_name in schema.get("$defs", {}):
                    schema_path = p
                    break
        if schema_path is None:
            print(f"  [SKIP] {class_name}: no schema file found", file=sys.stderr)
            continue
        written = generate_for_class(class_name, schema_path, args.dry_run)
        total += len(written)

    print(f"\nGenerated {total} negative fixtures{' (dry-run)' if args.dry_run else ''}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
