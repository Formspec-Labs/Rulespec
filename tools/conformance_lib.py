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
COMPILED_ANALYSIS_JSON_SCHEMA_DIR = ROOT / "compiled" / "json-schema" / "analysis"
COMPILED_ANALYSIS_SHACL_DIR = ROOT / "compiled" / "shacl" / "analysis"
COMPILED_PROFILE_JSON_SCHEMA_ROOT = ROOT / "compiled" / "json-schema" / "profiles"
COMPILED_PROFILE_SHACL_ROOT = ROOT / "compiled" / "shacl" / "profiles"
HAND_AUTHORED_SHACL_DIR = ROOT / "shapes"

# Which `@type` prefixes the L2 dispatchers bind to a compiled class schema.
#
# `rkaf:` alone was wrong. Core §4.2 codifies two OA selector classes —
# `oa:TextQuoteSelector` and `oa:TextPositionSelector` — with compiled shapes of
# their own: required payload, offset ordering, and the coordinate system an
# offset counts in. Binding only `rkaf:` left both unregistered, so every L2
# gate reported `pass` on a selector with an inverted range or no declared unit
# and the SHACL layer was the only thing catching them. The set is deliberately
# explicit rather than "any prefix with a compiled schema": a class enters L2
# dispatch when Rulespec compiles a shape for it, and that is a decision to
# record here, not to infer.
L2_TYPE_PREFIXES: tuple[str, ...] = ("rkaf:", "oa:")


def is_dispatched_type(type_iri: object) -> bool:
    """True when `type_iri` names a class the L2 gates validate."""
    return isinstance(type_iri, str) and type_iri.startswith(L2_TYPE_PREFIXES)


def violates_order(lower: object, upper: object) -> bool:
    """True when a same-typed ordered pair is inverted.

    `x-rkaf-order` is the compiler's carrier for a CUE ordering branch, and the
    branch is type-agnostic: it guards `rkaf:commentPeriodStart` (an ISO date
    string) and `oa:start` (an integer offset) with the same expression. A
    string-only comparison therefore enforced the date intervals and silently
    skipped every numeric one, which made the JSON Schema target weaker than
    the SHACL `sh:lessThanOrEquals` compiled from the SAME source line.

    Mixed types are NOT compared: two values of different JSON types have no
    meaningful order here, and guessing one would invent a verdict the CUE does
    not state. Booleans are excluded explicitly because Python treats them as
    integers.

    This lives here rather than in one caller because the keyword is a JSON
    Schema EXTENSION: `jsonschema` ignores it, so every Python L2 gate has to
    apply it separately, and three private copies would drift. The Rust twin is
    `violates_order` in `crates/rkaf-validate/src/lib.rs`.
    """
    if isinstance(lower, str) and isinstance(upper, str):
        return lower > upper
    if isinstance(lower, bool) or isinstance(upper, bool):
        return False
    if isinstance(lower, (int, float)) and isinstance(upper, (int, float)):
        return lower > upper
    return False


def compiled_json_schema_paths() -> list[Path]:
    """Kernel schemas, then the analysis module, then each profile's overlays.

    Order is load-bearing: `schema_bindings()` resolves one schema per JSON-LD
    `@type`, and a profile overlay is a SUPERSET of the kernel shape it
    composes (it restates every kernel property and adds its own), so the more
    specific shape must win. See `schema_bindings`.

    The analysis module (`compiled/*/analysis/`) sits between them because it
    is neither: it declares its OWN classes and overlays nothing, so it can
    never displace a kernel binding, and a profile that later overlays an
    analysis class must still win. Grouping it with the kernel rather than with
    the profiles is what keeps the profile-collision rule meaningful — two
    analysis files binding one `@type` is a repo-shape bug, not a legitimate
    overlay.
    """
    paths = sorted(COMPILED_JSON_SCHEMA_DIR.glob("*.schema.json"))
    if COMPILED_ANALYSIS_JSON_SCHEMA_DIR.is_dir():
        paths.extend(sorted(COMPILED_ANALYSIS_JSON_SCHEMA_DIR.glob("*.schema.json")))
    if COMPILED_PROFILE_JSON_SCHEMA_ROOT.is_dir():
        paths.extend(sorted(COMPILED_PROFILE_JSON_SCHEMA_ROOT.glob("*/*.schema.json")))
    return paths


def compiled_shacl_paths() -> list[Path]:
    """Every compiled SHACL file: kernel, analysis module, profile overlays."""
    paths = sorted(COMPILED_SHACL_DIR.glob("*.ttl"))
    if COMPILED_ANALYSIS_SHACL_DIR.is_dir():
        paths.extend(sorted(COMPILED_ANALYSIS_SHACL_DIR.glob("*.ttl")))
    if COMPILED_PROFILE_SHACL_ROOT.is_dir():
        paths.extend(sorted(COMPILED_PROFILE_SHACL_ROOT.glob("*/*.ttl")))
    return paths

CROSS_GATE_DIRS = {"projectors", "adversarial", "ai-extraction"}
# Reserved for future non-fixture siblings under fixtures/ that the conformance
# walker MUST skip (e.g., a shared local context, vocab manifests). Empty after
# the b6c24de cleanup — the legacy `context.jsonld` was removed; the canonical
# JSON-LD context lives at `context/rkaf-context.jsonld`.
NON_FIXTURE_NAMES: set[str] = set()


class DuplicateProfileBindingError(RuntimeError):
    """Two profile overlays claim the same JSON-LD `@type`.

    Exactly one schema validates a given `@type`. When two profiles overlay the
    same class there is no defensible winner: whichever loses stops being
    checked, and every gate stays green while the constraints it carried go
    unenforced. That is a repo-shape error the compiler cannot resolve, so it
    is raised rather than silently arbitrated.
    """


@dataclass(frozen=True)
class SchemaBinding:
    """A JSON-LD @type to compiled JSON Schema class binding."""

    type_iri: str
    schema_name: str
    class_name: str
    schema_path: Path
    required: tuple[str, ...]


def _repo_relative(path: Path) -> str:
    """Repo-relative display path, falling back to the absolute path."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
    """Discover every compiled class schema that declares a concrete @type.

    Exactly one schema validates a given `@type`. Within one tree the first
    deterministic binding wins (a legacy duplicate never displaces the
    canonical file, which sorts first). ACROSS trees a profile overlay
    deliberately displaces the kernel binding for the class it composes: the
    overlay restates every kernel property and adds the profile's own, so
    binding to it keeps the kernel's guarantees and adds the profile's. Binding
    to the kernel instead would silently stop checking the profile grammars on
    a repo that ships the profile.

    A SECOND profile overlay on an already-overlaid class is a hard error
    (`DuplicateProfileBindingError`): displacing the kernel is meaningful
    because the overlay is a superset of it, but two sibling profiles are not
    supersets of each other, so picking one would silently unbind the other's
    constraints while every gate stayed green.
    """
    bindings: dict[str, SchemaBinding] = {}
    kernel_bound: set[str] = set()
    profile_bound: dict[str, Path] = {}
    for schema_path in compiled_json_schema_paths():
        is_profile = COMPILED_PROFILE_JSON_SCHEMA_ROOT in schema_path.parents
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
            if not is_dispatched_type(type_iri):
                continue
            binding = SchemaBinding(
                type_iri=type_iri,
                schema_name=schema_name,
                class_name=class_name,
                schema_path=schema_path,
                required=tuple(class_schema.get("required", ())),
            )
            if is_profile:
                if (previous := profile_bound.get(type_iri)) is not None:
                    raise DuplicateProfileBindingError(
                        f"two profile overlays bind {type_iri}: "
                        f"{_repo_relative(previous)} and "
                        f"{_repo_relative(schema_path)}. Exactly one schema may "
                        f"validate a given @type — binding {type_iri} to either "
                        "one silently stops enforcing the other's constraints. "
                        "Give one overlay its own @type, or merge them into a "
                        "single profile shape."
                    )
                profile_bound[type_iri] = schema_path
                bindings[type_iri] = binding
                kernel_bound.discard(type_iri)
            elif type_iri not in bindings:
                bindings[type_iri] = binding
                kernel_bound.add(type_iri)
    return bindings


def schema_bindings_by_class() -> dict[str, SchemaBinding]:
    return {binding.class_name: binding for binding in schema_bindings().values()}


def shacl_shape_paths() -> list[Path]:
    """Return the full SHACL suite: authored invariants plus compiled shapes.

    Compiled shapes cover the kernel and every domain profile this repo ships.
    SHACL is conjunctive, so a profile overlay may only ADD constraints to a
    class the kernel also targets — it can never relax one.
    """
    paths = list(sorted(HAND_AUTHORED_SHACL_DIR.glob("*.ttl")))
    paths.extend(compiled_shacl_paths())
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
