"""Shared discovery helpers for Rulespec conformance tooling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "fixtures"
COMPILED_JSON_SCHEMA_DIR = ROOT / "compiled" / "json-schema" / "core"
COMPILED_SHACL_DIR = ROOT / "compiled" / "shacl" / "core"
HAND_AUTHORED_SHACL_DIR = ROOT / "shapes"

CROSS_GATE_DIRS = {"projectors", "adversarial", "ai-extraction"}
# Reserved for future non-fixture siblings under fixtures/ that the conformance
# walker MUST skip (e.g., a shared local context, vocab manifests). Empty after
# the b6c24de cleanup — the legacy `context.jsonld` was removed; the canonical
# JSON-LD context lives at `context/rkaf-context.jsonld`.
NON_FIXTURE_NAMES: set[str] = set()


@dataclass(frozen=True)
class SchemaBinding:
    """A JSON-LD @type to compiled JSON Schema class binding."""

    type_iri: str
    schema_name: str
    class_name: str
    schema_path: Path
    required: tuple[str, ...]


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def iter_nodes(doc: dict, *, include_behavior_input: bool = True) -> Iterable[dict]:
    """Yield root, @graph, and optional BehaviorTestCase input nodes."""
    if "@graph" in doc and isinstance(doc["@graph"], list):
        yield from (n for n in doc["@graph"] if isinstance(n, dict))
    else:
        yield doc

    if not include_behavior_input:
        return

    nested = doc.get("rkaf:input")
    if isinstance(nested, dict):
        if "@graph" in nested and isinstance(nested["@graph"], list):
            yield from (n for n in nested["@graph"] if isinstance(n, dict))
        elif isinstance(nested.get("@type"), str):
            yield nested


def schema_bindings() -> dict[str, SchemaBinding]:
    """Discover every compiled class schema that declares a concrete @type."""
    bindings: dict[str, SchemaBinding] = {}
    for schema_path in sorted(COMPILED_JSON_SCHEMA_DIR.glob("*.schema.json")):
        doc = json.loads(schema_path.read_text())
        schema_name = schema_path.name.removesuffix(".schema.json")
        for class_name, class_schema in doc.get("$defs", {}).items():
            if not isinstance(class_schema, dict):
                continue
            type_iri = (
                class_schema.get("properties", {})
                .get("@type", {})
                .get("const")
            )
            if not isinstance(type_iri, str) or not type_iri.startswith("rkaf:"):
                continue
            # Some legacy schema files still duplicate a class. Keep the first
            # deterministic binding; the canonical file sorts before aliases.
            bindings.setdefault(
                type_iri,
                SchemaBinding(
                    type_iri=type_iri,
                    schema_name=schema_name,
                    class_name=class_name,
                    schema_path=schema_path,
                    required=tuple(class_schema.get("required", ())),
                ),
            )
    return bindings


def schema_bindings_by_class() -> dict[str, SchemaBinding]:
    return {binding.class_name: binding for binding in schema_bindings().values()}


def shacl_shape_paths() -> list[Path]:
    """Return the full SHACL suite: authored invariants plus compiled shapes."""
    paths = list(sorted(HAND_AUTHORED_SHACL_DIR.glob("*.ttl")))
    paths.extend(sorted(COMPILED_SHACL_DIR.glob("*.ttl")))
    return paths


def classify_fixture(name: str) -> str:
    n = name.lower()
    if n.startswith("behavior/"):
        return "behavior"
    if "-negative" in n:
        return "negative"
    if "-edge" in n:
        return "edge"
    return "positive"


def fixture_paths(*, include_cross_gate: bool = False) -> list[Path]:
    paths: list[Path] = []
    for path in FIXTURES_DIR.rglob("*.jsonld"):
        rel = path.relative_to(FIXTURES_DIR).as_posix()
        if rel in NON_FIXTURE_NAMES:
            continue
        parts = set(path.relative_to(FIXTURES_DIR).parts)
        if not include_cross_gate and parts & CROSS_GATE_DIRS:
            continue
        paths.append(path)
    return sorted(paths)


def fixture_name(path: Path) -> str:
    return path.relative_to(FIXTURES_DIR).as_posix()


def positive_fixture_paths() -> list[Path]:
    return [
        path
        for path in fixture_paths()
        if classify_fixture(fixture_name(path)) == "positive"
    ]


def negative_fixture_paths() -> list[Path]:
    return [
        path
        for path in fixture_paths()
        if classify_fixture(fixture_name(path)) == "negative"
    ]
