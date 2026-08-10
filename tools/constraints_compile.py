#!/usr/bin/env python3
"""Rulespec Layer 2 constraint compiler.

CUE source-of-truth → multiple compilation targets:
  - JSON Schema 2020-12 (MUST)
  - Rust validator code  (MUST)
  - TypeScript validator code (MUST)
  - SHACL Turtle Pattern C only (MUST for CUE-expressible constraints)
  - Rego (closed-enum + cardinality only)

The compiler reads CUE files as text and extracts the regular structure that
Rulespec CUE follows (defined in constraints/core/, constraints/adversarial/,
constraints/ai-extraction/):

  - `#Name: "lit" | "lit" | "lit"`          → closed enum
  - `#Whole: #PartA | #PartB`                → closed enum assembled from parts
                                               that may live in other files
  - `#Name: string & =~"..." & !~"..."`     → reusable scalar string carrier
  - `#Name: { "field": #TypeRef, ... }`     → shape with typed properties
  - `#Map: struct.MinFields(1) & {`
    `  [language=<BCP47>]: string | [...string] }`
                                              → named JSON-LD language map
  - `#Literal: { "@value": string,`
    `             "@type": <absolute IRI> }` → named typed-literal object
  - `"field": #T | ([...#T] & list.MinItems(1))`
                                              → named one-or-many carrier
  - `"field": { "@value": string, "@type": #D }` → JSON-LD value object
                                               (typed literal; see below)
  - `#Name: { #Base, ... }`                  → shape composed from `#Base`
  - `#Name: #Base & { ... }`                 → shape composed from `#Base`
  - `#Name: (#Base & {...}) | (#Base & {...})` → composed disjunction
  - `if X["x"] == "v" { "y": T }`           → conditional branch
  - `if X["start"] > X["end"] { _|_ }`       → ordered-field invariant
  - `{...} | {...}`                          → disjunction branch
  - `list.MinItems(N)` / `list.MaxItems(N)`  → list cardinality
  - `@rkafStrictList()`                      → preserve array-only authoring
  - `if !list.UniqueItems(X["x"]) { _|_ }`   → unique list members
  - `string & =~"..." & !~"..."`             → allowed + forbidden pattern
  - `time.Format("2006-01-02")`              → JSON Schema/SHACL date

Composed shapes are flattened before any emitter runs, unifying the base with
the derived body facet by facet (see "Shape composition" below). Composition may
de-duplicate but never loosen: an unresolvable base, a composition cycle, or a
facet conflict the flat AST cannot carry is a compile error (exit 1), never a
silently weaker target.

This is NOT a full CUE parser — it handles the regular patterns Rulespec uses.
The CUE source is the authoritative spec; this compiler is a deterministic
projection. The CUE compiler proper (`.tools/cue vet`) validates source syntax;
this tool projects validated source to other carriers.

Usage:
  python3 tools/constraints_compile.py --in <file.cue> --target <name> --out <path>

Targets: json-schema | rust | typescript | shacl | rego

Exit codes:
  0  success
  1  compile error
  2  setup error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


# ---- AST types -----------------------------------------------------------

@dataclass
class EnumDef:
    name: str
    values: list[str]  # literal string values

@dataclass
class EnumUnion:
    """A closed-enum union built from other enum refs: `#A | #B | #C`."""
    name: str
    refs: list[str]  # names of referenced enums


@dataclass
class ScalarTypeDef:
    """A reusable constrained scalar such as the shared BCP 47 language tag."""

    name: str
    value: "PropDef"


@dataclass
class PropDef:
    name: str
    type_ref: str             # "string" | "int" | "float" | "bool" | "enum" | "named" | "enum_union" | "list"
    enum_ref: Optional[str] = None
    named_ref: Optional[str] = None
    list_inner_enum: Optional[str] = None
    list_inner_named: Optional[str] = None
    list_min_items: int = 0
    list_max_items: Optional[int] = None
    list_unique_items: bool = False
    # Most Rulespec lists accept JSON-LD's scalar shorthand in projections.
    # `@rkafStrictList()` keeps an authoring form array-only when the
    # specification requires the literal JSON array (notation and lifecycle
    # participants).
    list_allow_scalar: bool = True
    list_of_string: bool = False
    optional: bool = False
    fixed_value: Optional[str] = None
    pattern: Optional[str] = None
    forbidden_pattern: Optional[str] = None
    string_format: Optional[str] = None
    min_inclusive: Optional[float] = None
    max_inclusive: Optional[float] = None
    inline_enum_values: Optional[list[str]] = None
    enum_union_refs: Optional[list[str]] = None
    # Members of an inline nested object (`type_ref == "value_object"`). The
    # only nested object the projector carries is a JSON-LD value object — a
    # struct declaring `@value` — because that is the wire form of a typed
    # literal. See `_validate_value_object`.
    object_properties: Optional[list["PropDef"]] = None
    # A value object may have mutually exclusive RDF 1.1 wire branches:
    # typed literal (`@value` + `@type`) or language-tagged string
    # (`@value` + `@language`). Each branch is a closed object.
    object_alternatives: Optional[list[list["PropDef"]]] = None


@dataclass
class ConditionalBranch:
    when_property: str
    when_equals: Optional[str]
    then_require: list[PropDef]
    when_not_equals: bool = False
    then_forbid: list[str] = field(default_factory=list)


@dataclass
class OrderConstraint:
    lower_property: str
    upper_property: str


@dataclass
class NotEqualConstraint:
    left_property: str
    right_property: str


@dataclass
class DisjunctionBranch:
    properties: list[PropDef]


@dataclass
class ShapeDef:
    name: str
    type_iri: Optional[str]
    properties: list[PropDef] = field(default_factory=list)
    conditionals: list[ConditionalBranch] = field(default_factory=list)
    orders: list[OrderConstraint] = field(default_factory=list)
    not_equals: list[NotEqualConstraint] = field(default_factory=list)
    disjunctions: list[list[DisjunctionBranch]] = field(default_factory=list)
    # Names of shapes this shape is composed from (`#Base` embedded in the
    # body, or `#Base & {...}`). Resolved into `properties` / `conditionals` /
    # `orders` / `not_equals` / `disjunctions` by
    # `_resolve_shape_compositions` so that every emitter sees one flat,
    # fully-composed shape.
    base_refs: list[str] = field(default_factory=list)


@dataclass
class PatternMapDef:
    """A named CUE map whose string keys and values are constrained.

    Rulespec uses this generic carrier for JSON-LD language maps. The compiler
    does not key behavior on SKOS property names: any field may reference the
    named map, and every target receives the same key/value constraints.
    """

    name: str
    key: PropDef
    value: PropDef
    min_properties: int = 0


@dataclass
class ObjectTypeDef:
    """A closed named object used as a property value rather than an RDF node."""

    name: str
    properties: list[PropDef] = field(default_factory=list)


@dataclass
class ConstraintDoc:
    package: str
    # Keep the authoritative CUE source attached to parsed documents so every
    # emitter can resolve sibling-file scalar/map/object definitions even when
    # a caller invokes the emitter directly. CLI compilation already passed a
    # registry explicitly; compiler tests and library callers did not, which
    # made the same parsed document depend on the call path.
    source_file: Optional[Path] = None
    enums: list[EnumDef] = field(default_factory=list)
    enum_unions: list[EnumUnion] = field(default_factory=list)
    scalar_types: list[ScalarTypeDef] = field(default_factory=list)
    pattern_maps: list[PatternMapDef] = field(default_factory=list)
    object_types: list[ObjectTypeDef] = field(default_factory=list)
    shapes: list[ShapeDef] = field(default_factory=list)


# ---- Parser --------------------------------------------------------------

ENUM_LINE_RE = re.compile(
    r'^#(\w+):\s*("[^"]+"(?:\s*\|\s*"[^"]+")*)\s*$'
)
ENUM_MULTI_RE = re.compile(r'"([^"]+)"')
# Closed-enum-of-refs: `#Name: #A | #B | #C`, or a bare single-reference alias
# `#Name: #A` (the degenerate one-part case — a reference to another enum's
# value set, never a copy of it; see #WarrantKindV02 in
# constraints/adversarial/enum-drift.cue).
ENUM_UNION_RE = re.compile(r'^#(\w+):\s*((?:#\w+\s*\|\s*)*#\w+)\s*$')
ENUM_UNION_REFS_RE = re.compile(r'#(\w+)')
SCALAR_TYPE_RE = re.compile(
    r'^#(\w+):\s*(string(?:\s*&\s*=~"[^"]+")?'
    r'(?:\s*&\s*!~"[^"]+")?)\s*$'
)


# Shape composition spellings. `#Name: {` + an embedded `#Base` line is handled
# by `parse_shape_body`; these two cover the expression forms.
SHAPE_CONJUNCTION_RE = re.compile(r"^#(\w+):\s*#(\w+)\s*&\s*(?:\w+=)?\{$")
COMPOSED_DISJUNCTION_OPEN_RE = re.compile(
    r"^#(\w+):\s*\(\s*#(\w+)\s*&\s*(?:\w+=)?\{$"
)
COMPOSED_DISJUNCTION_NEXT_RE = re.compile(
    r"^\}\)\s*\|\s*\(\s*#(\w+)\s*&\s*(?:\w+=)?\{$"
)
EMBEDDED_BASE_RE = re.compile(r"^#(\w+)$")

# `"rkaf:assertsValue": {` — a property whose value is an inline nested struct.
NESTED_OBJECT_OPEN_RE = re.compile(r'^"([^"]+)"(\?)?:\s*\{$')

# A named pattern-keyed map. `struct.MinFields` is part of the source meaning:
# without it an optional SKOS language-map property could be present as `{}` and
# disappear during JSON-LD expansion.
PATTERN_MAP_OPEN_RE = re.compile(
    r"^#(\w+):\s*struct\.MinFields\((\d+)\)\s*&\s*\{$"
)
PATTERN_MAP_FIELD_RE = re.compile(
    r"^\[(?:\w+=)?(.+)\]:\s*(.+)$"
)

# JSON-LD reserves exactly these members for a value object (JSON-LD 1.1
# §4.2.1). `@value` is what MAKES a struct a value object, so the projector
# recognizes the nested struct by that member rather than by a marker name.
VALUE_OBJECT_MEMBERS = {"@value", "@type", "@language"}


def parse_cue_file(path: Path, *, resolve_composition: bool = True) -> ConstraintDoc:
    """Parse one CUE constraint file into the projector's flat AST.

    `resolve_composition=False` returns shapes with their `base_refs` still
    unresolved. It exists so the cross-file shape registry can be built without
    recursing back into composition resolution.
    """
    src = path.read_text()

    doc = ConstraintDoc(package=path.stem, source_file=path.resolve())

    # Pre-pass: join any line that ends with `|` into the next line (CUE
    # disjunction continuation). This works for both top-level enum unions and
    # in-shape property assignments whose RHS spans multiple lines.
    raw_lines = src.split("\n")
    joined_pre: list[str] = []
    buf = ""
    for raw in raw_lines:
        no_comment = raw.split("//")[0].rstrip()
        stripped = no_comment.rstrip()
        if buf:
            buf += " " + stripped.lstrip()
        else:
            buf = stripped
        # Continue if line ends with `|` (CUE disjunction continuation)
        if buf.rstrip().endswith("|"):
            continue
        joined_pre.append(buf)
        buf = ""
    if buf:
        joined_pre.append(buf)
    lines = joined_pre

    # Phase 1: collect top-level `#Name: ...` definitions.
    # Multi-line enums (over backslash or `|` continuation) are joined first.
    joined_lines: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.split("//")[0].rstrip()
        if not stripped.strip():
            i += 1
            continue
        # Multi-line enum (string literal): collect continuation lines starting with whitespace + `"`
        if re.match(r"^#\w+:\s*\"", stripped) and "{" not in stripped:
            buf = stripped
            j = i + 1
            while j < len(lines):
                nxt = lines[j].split("//")[0].rstrip()
                if re.match(r"^\s+\"", nxt) and ("|" in nxt or buf.endswith("|")):
                    buf += " " + nxt.strip()
                    j += 1
                elif buf.endswith("|"):
                    buf += " " + nxt.strip()
                    j += 1
                else:
                    break
            joined_lines.append((i, buf))
            i = j
            continue
        # Multi-line enum-union (#A | #B | continuation #C)
        if re.match(r"^#\w+:\s*#\w+", stripped) and "{" not in stripped:
            buf = stripped
            j = i + 1
            while j < len(lines):
                nxt = lines[j].split("//")[0].rstrip()
                if re.match(r"^\s+#\w+", nxt) and ("|" in nxt or buf.endswith("|")):
                    buf += " " + nxt.strip()
                    j += 1
                elif buf.endswith("|"):
                    buf += " " + nxt.strip()
                    j += 1
                else:
                    break
            joined_lines.append((i, buf))
            i = j
            continue
        joined_lines.append((i, stripped))
        i += 1

    # Phase 2: walk joined_lines to extract enums and shape definitions.
    idx = 0
    while idx < len(joined_lines):
        _, line = joined_lines[idx]
        # Enum on single (joined) line — string literals
        em = ENUM_LINE_RE.match(line)
        if em:
            name = em.group(1)
            values = ENUM_MULTI_RE.findall(em.group(2))
            doc.enums.append(EnumDef(name=name, values=values))
            idx += 1
            continue
        # Enum-union (#A | #B | #C)
        um = ENUM_UNION_RE.match(line)
        if um:
            name = um.group(1)
            refs = ENUM_UNION_REFS_RE.findall(um.group(2))
            doc.enum_unions.append(EnumUnion(name=name, refs=refs))
            idx += 1
            continue
        # Reusable constrained scalar. The shared language-tag grammar is the
        # motivating case: language maps and JSON-LD value objects must not
        # carry separate copies of the same BCP 47 regular expression.
        scalar = SCALAR_TYPE_RE.match(line)
        if scalar:
            value = parse_property_line(f'"__value": {scalar.group(2)}')
            if value is None or value.type_ref != "string":
                raise CompileError(
                    f"scalar type #{scalar.group(1)} is not a projectable string"
                )
            doc.scalar_types.append(
                ScalarTypeDef(name=scalar.group(1), value=value)
            )
            idx += 1
            continue
        # Named pattern-keyed map:
        #
        #   #PrefLabelMap: struct.MinFields(1) & {
        #       [language=string & =~"..." & !~"^@none$"]: string
        #   }
        #
        # The value expression may instead be one-or-many strings. Keeping
        # this as a named type lets any vocabulary property reuse it without
        # teaching the compiler field-name exceptions.
        mm = PATTERN_MAP_OPEN_RE.match(line)
        if mm:
            map_def, consumed = parse_pattern_map_body(
                joined_lines,
                idx + 1,
                name=mm.group(1),
                min_properties=int(mm.group(2)),
            )
            doc.pattern_maps.append(map_def)
            idx += 1 + consumed
            continue
        # Shape opening: `#Name: {` or `#Name: Alias={`
        sm = re.match(r"^#(\w+):\s*(?:\w+=)?\{$", line)
        if sm:
            shape_name = sm.group(1)
            shape, consumed = parse_shape_body(joined_lines, idx + 1)
            shape.name = shape_name
            # A top-level JSON-LD value object is a named property carrier, not
            # an RDF node shape. Resource shapes may compose other shapes and
            # normally carry a fixed class-valued `@type`; a named typed
            # literal instead carries `@value` plus a pattern-constrained
            # datatype `@type`.
            if any(prop.name == "@value" for prop in shape.properties):
                object_type = ObjectTypeDef(
                    name=shape_name,
                    properties=shape.properties,
                )
                doc.object_types.append(object_type)
            else:
                doc.shapes.append(shape)
            idx += 1 + consumed
            continue
        # Shape composition by conjunction: `#Name: #Base & { ... }`.
        cj = SHAPE_CONJUNCTION_RE.match(line)
        if cj:
            shape, consumed = parse_shape_body(joined_lines, idx + 1)
            shape.name = cj.group(1)
            shape.base_refs.insert(0, cj.group(2))
            doc.shapes.append(shape)
            idx += 1 + consumed
            continue
        # Shape composition by disjunction:
        #   `#Name: (#Base & {...}) | (#Base & {...})`
        # The shared base is composed into the shape; each parenthesized
        # overlay becomes one alternative of a single disjunction group.
        cd = COMPOSED_DISJUNCTION_OPEN_RE.match(line)
        if cd:
            shape = ShapeDef(name=cd.group(1), type_iri=None)
            shape.base_refs.append(cd.group(2))
            branches, consumed = parse_composed_disjunction(
                joined_lines, idx + 1, shape
            )
            if branches:
                shape.disjunctions.append(branches)
            doc.shapes.append(shape)
            idx += 1 + consumed
            continue
        idx += 1

    _classify_local_named_references(doc)
    for pattern_map in doc.pattern_maps:
        _validate_pattern_map(pattern_map, allow_unresolved=True)
    for object_type in doc.object_types:
        _validate_named_value_object(object_type)
    _validate_document_value_objects(doc, allow_unresolved=True)
    if resolve_composition:
        _resolve_shape_compositions(doc, path)
    return doc


def parse_pattern_map_body(
    lines: list[tuple[int, str]],
    start: int,
    *,
    name: str,
    min_properties: int,
) -> tuple[PatternMapDef, int]:
    """Parse the single pattern field inside a named CUE map definition."""
    entries: list[tuple[PropDef, PropDef]] = []
    i = start
    while i < len(lines):
        line = lines[i][1].strip()
        if line == "}":
            i += 1
            break
        match = PATTERN_MAP_FIELD_RE.match(line)
        if match:
            key = parse_property_line(f'"__key": {match.group(1)}')
            value = parse_property_line(f'"__value": {match.group(2)}')
            if key is None or value is None:
                raise CompileError(
                    f"named map #{name} contains an unprojectable pattern field"
                )
            entries.append((key, value))
        elif line:
            raise CompileError(
                f"named map #{name} contains an unsupported member: {line}"
            )
        i += 1
    if len(entries) != 1:
        raise CompileError(
            f"named map #{name} MUST declare exactly one pattern field; "
            f"found {len(entries)}"
        )
    key, value = entries[0]
    if min_properties < 1:
        raise CompileError(
            f"named map #{name} MUST require at least one language entry"
        )
    return (
        PatternMapDef(
            name=name,
            key=key,
            value=value,
            min_properties=min_properties,
        ),
        i - start,
    )


def _validate_pattern_map(definition: PatternMapDef, *, allow_unresolved: bool) -> None:
    """Prove that a named map key is the shared BCP 47 scalar grammar."""
    key = definition.key
    value = definition.value
    if value.type_ref != "string" and not (
        value.type_ref == "list" and value.list_of_string
    ):
        if not (
            allow_unresolved
            and (
                (value.type_ref == "enum" and value.enum_ref)
                or (
                    value.type_ref == "list"
                    and value.list_inner_enum
                )
            )
        ):
            raise CompileError(
                f"named map #{definition.name} values MUST be strings or "
                "one-or-many strings"
            )
    if value.type_ref == "list" and value.list_min_items < 1:
        raise CompileError(
            f"named map #{definition.name} list values MUST contain at least "
            "one string"
        )
    if key.type_ref != "string" or not key.pattern:
        if allow_unresolved and key.type_ref == "enum" and key.enum_ref:
            return
        raise CompileError(
            f"named map #{definition.name} MUST constrain string keys with a pattern"
        )
    try:
        key_pattern = re.compile(key.pattern)
        forbidden_key_pattern = (
            re.compile(key.forbidden_pattern)
            if key.forbidden_pattern
            else None
        )
    except re.error as exc:
        raise CompileError(
            f"named map #{definition.name} has an invalid key pattern: {exc}"
        ) from exc
    valid_language_tags = ("en", "es", "zh-Hant", "und")
    invalid_language_tags = ("", "@none", "en_US", "en--US")
    if any(
        key_pattern.fullmatch(tag) is None
        or (
            forbidden_key_pattern is not None
            and forbidden_key_pattern.search(tag) is not None
        )
        for tag in valid_language_tags
    ) or any(
        key_pattern.fullmatch(tag) is not None
        and not (
            forbidden_key_pattern is not None
            and forbidden_key_pattern.search(tag) is not None
        )
        for tag in invalid_language_tags
    ):
        raise CompileError(
            f"named map #{definition.name} key constraints MUST accept BCP 47 "
            "language tags including script subtags and `und`, and reject "
            "`@none` and malformed tags"
        )


def parse_composed_disjunction(
    lines: list[tuple[int, str]], start: int, shape: ShapeDef
) -> tuple[list[DisjunctionBranch], int]:
    """Parse the alternatives of `(#Base & {...}) | (#Base & {...})`.

    `start` is the first line inside the opening alternative. Returns the
    branches and the number of lines consumed; base references discovered on
    later alternatives are appended to `shape.base_refs`.
    """
    branches: list[DisjunctionBranch] = []
    current: list[PropDef] = []
    i = start
    while i < len(lines):
        line = lines[i][1].strip()
        nxt = COMPOSED_DISJUNCTION_NEXT_RE.match(line)
        if nxt:
            branches.append(DisjunctionBranch(properties=current))
            current = []
            if nxt.group(1) not in shape.base_refs:
                shape.base_refs.append(nxt.group(1))
            i += 1
            continue
        if line == "})":
            branches.append(DisjunctionBranch(properties=current))
            i += 1
            break
        prop = parse_property_line(line)
        if prop:
            current.append(prop)
        i += 1
    return branches, i - start


def parse_shape_body(lines: list[tuple[int, str]], start: int) -> tuple[ShapeDef, int]:
    """Parse the body of `#Name: { ... }` starting at `start`. Returns (shape, lines_consumed).

    Walks line-by-line. Recognized constructs:
      - Top-level property: `"name": <type-expr>`
      - Conditional: `if X["x"] == "v" { props }`
      - Ordering: `if X["start"] > X["end"] { _|_ }`
      - Disjunction marker: a line that is exactly `{` or `} |` or `} | {` is part
        of a sibling-block disjunction. We scan such blocks character-by-character
        via parse_disjunction_block_text.
    """
    shape = ShapeDef(name="", type_iri=None)
    depth = 1
    i = start
    while i < len(lines) and depth > 0:
        _, raw = lines[i]
        line = raw.strip()
        if line == "}":
            depth -= 1
            if depth == 0:
                # End of shape body
                break
            i += 1
            continue
        # CUE enforces member uniqueness directly. Carry the same rule into
        # JSON Schema and TypeScript before JSON-LD expansion deduplicates RDF
        # triples and makes duplicate source members impossible to observe.
        unique = re.match(
            r'^if\s+!list\.UniqueItems\(\w+\["([^"]+)"\]\)\s*'
            r'\{\s*_\|_\s*\}$',
            line,
        )
        if unique is None:
            unique = re.match(
                r'^if\s+\w+\["([^"]+)"\]\s*!=\s*_\|_\s*\{\s*'
                r'if\s+!list\.UniqueItems\(\w+\["\1"\]\)\s*'
                r'\{\s*_\|_\s*\}\s*\}$',
                line,
            )
        if unique:
            property_name = unique.group(1)
            prop = next(
                (
                    candidate
                    for candidate in shape.properties
                    if candidate.name == property_name
                ),
                None,
            )
            if prop is None or prop.type_ref != "list":
                raise CompileError(
                    "list.UniqueItems references non-list property "
                    f"{property_name!r}"
                )
            prop.list_unique_items = True
            i += 1
            continue
        # Cross-field inequality. The optional presence guard keeps a missing
        # right-hand property valid; when both scalar properties exist, equal
        # values make the CUE branch bottom.
        not_equal_match = re.match(
            r'^if\s+(?:\w+\["[^"]+"\]\s*!=\s*_\|_\s*&&\s*)?'
            r'\w+\["([^"]+)"\]\s*==\s*\w+\["([^"]+)"\]\s*'
            r'\{\s*_\|_\s*\}$',
            line,
        )
        if not_equal_match:
            left_property, right_property = not_equal_match.groups()
            by_name = {prop.name: prop for prop in shape.properties}
            for property_name in (left_property, right_property):
                prop = by_name.get(property_name)
                if prop is None or prop.type_ref == "list":
                    raise CompileError(
                        "cross-field inequality references missing or "
                        f"non-scalar property {property_name!r}"
                    )
            if left_property == right_property:
                raise CompileError(
                    "cross-field inequality must name two different properties"
                )
            shape.not_equals.append(
                NotEqualConstraint(
                    left_property=left_property,
                    right_property=right_property,
                )
            )
            i += 1
            continue
        # Cross-field ordering. The CUE branch makes values where lower >
        # upper bottom; projections carry the equivalent lower <= upper rule.
        order_match = re.match(
            r'^if\s+\w+\["([^"]+)"\]\s*>\s*\w+\["([^"]+)"\]\s*\{',
            line,
        )
        if order_match:
            shape.orders.append(
                OrderConstraint(
                    lower_property=order_match.group(1),
                    upper_property=order_match.group(2),
                )
            )
            j = i + 1
            while j < len(lines) and lines[j][1].strip() != "}":
                j += 1
            i = j + 1
            continue
        # Conditional
        if line.startswith("if ") and "{" in line:
            mc = re.match(
                r'^if\s+\w+\["([^"]+)"\]\s*(==|!=)\s*"([^"]+)"\s*\{',
                line,
            )
            not_equals = False
            if mc is None:
                # Backward-compatible parser for the repository's early
                # condition spelling. New CUE must use the alias form above.
                mc = re.match(r'^if\s+"([^"]+)"\s*==\s*"([^"]+)"\s*\{', line)
            if mc:
                if len(mc.groups()) == 3:
                    when_prop, operator, when_eq = mc.groups()
                    not_equals = operator == "!="
                else:
                    when_prop, when_eq = mc.group(1), mc.group(2)
                req_props: list[PropDef] = []
                forbidden_props: list[str] = []
                j = i + 1
                while j < len(lines):
                    _, l2_raw = lines[j]
                    l2 = l2_raw.strip()
                    if l2 == "}":
                        break
                    nested = NESTED_OBJECT_OPEN_RE.match(l2)
                    if nested:
                        inner: list[PropDef] = []
                        j += 1
                        while j < len(lines):
                            nested_line = lines[j][1].strip()
                            if nested_line == "}":
                                break
                            inner_prop = parse_property_line(nested_line)
                            if inner_prop:
                                inner.append(inner_prop)
                            j += 1
                        prop = PropDef(
                            name=nested.group(1),
                            type_ref="value_object",
                            optional=nested.group(2) == "?",
                            object_properties=inner,
                            object_alternatives=[inner],
                        )
                        req_props.append(prop)
                        j += 1
                        continue
                    forbidden = re.match(r'^"([^"]+)"\?:\s*_\|_\s*$', l2)
                    if forbidden:
                        forbidden_props.append(forbidden.group(1))
                        j += 1
                        continue
                    p = parse_property_line(l2)
                    if p:
                        req_props.append(p)
                    j += 1
                shape.conditionals.append(ConditionalBranch(
                    when_property=when_prop,
                    when_equals=when_eq,
                    then_require=req_props,
                    when_not_equals=not_equals,
                    then_forbid=forbidden_props,
                ))
                i = j + 1
                continue
            present = re.match(
                r'^if\s+\w+\["([^"]+)"\]\s*!=\s*_\|_\s*\{',
                line,
            )
            if present:
                req_props = []
                j = i + 1
                while j < len(lines):
                    _, l2_raw = lines[j]
                    l2 = l2_raw.strip()
                    if l2 == "}":
                        break
                    p = parse_property_line(l2)
                    if p:
                        req_props.append(p)
                    j += 1
                shape.conditionals.append(
                    ConditionalBranch(
                        when_property=present.group(1),
                        when_equals=None,
                        then_require=req_props,
                        then_forbid=[],
                    )
                )
                i = j + 1
                continue
        # Disjunction line(s)
        if line == "{":
            branches: list[DisjunctionBranch] = []
            current: list[PropDef] = []
            local_depth = 1
            j = i + 1
            while j < len(lines):
                _, l2_raw = lines[j]
                l2 = l2_raw.strip()
                lopens = l2.count("{")
                lcloses = l2.count("}")
                if local_depth == 1 and re.match(r"^\}\s*\|", l2):
                    branches.append(DisjunctionBranch(properties=current))
                    current = []
                    j += 1
                    continue
                if local_depth == 1 and l2 == "}":
                    branches.append(DisjunctionBranch(properties=current))
                    j += 1
                    break
                local_depth += lopens - lcloses
                p = parse_property_line(l2)
                if p:
                    current.append(p)
                j += 1
            if branches:
                shape.disjunctions.append(branches)
            i = j
            continue
        # Inline nested object: `"name"?: {` … `}`. The projector carries one
        # nested-object kind FAITHFULLY — the JSON-LD value object, i.e. the
        # wire form of a typed literal — because that is the only nested struct
        # whose meaning every target can express (object schema, `sh:datatype`
        # closure, typed Rust/TypeScript carrier).
        #
        # A value object whose `@type` is not a closed enum is a `CompileError`
        # (see `_validate_value_object`): without a closed set SHACL would have
        # nothing to close over.
        #
        # Any OTHER nested struct is NOT rejected. It keeps the pre-existing
        # lossy hoist described at the fall-through below, which is a known
        # degradation, not a guardrail — see
        # `test_non_value_object_nested_struct_hoists_and_is_documented_lossy`.
        nested = NESTED_OBJECT_OPEN_RE.match(line)
        if nested:
            inner: list[PropDef] = []
            alternatives: list[list[PropDef]] = []
            j = i + 1
            while j < len(lines):
                _, l2_raw = lines[j]
                l2 = l2_raw.strip()
                if l2 == "}":
                    break
                if l2 == "{":
                    branches: list[list[PropDef]] = []
                    current: list[PropDef] = []
                    j += 1
                    while j < len(lines):
                        _, branch_raw = lines[j]
                        branch_line = branch_raw.strip()
                        if re.match(r"^\}\s*\|\s*\{$", branch_line):
                            branches.append(current)
                            current = []
                            j += 1
                            continue
                        if branch_line == "}":
                            branches.append(current)
                            j += 1
                            break
                        branch_prop = parse_property_line(branch_line)
                        if branch_prop:
                            current.append(branch_prop)
                        j += 1
                    alternatives = [[*inner, *branch] for branch in branches]
                    # The next `}` closes the outer value object.
                    continue
                inner_prop = parse_property_line(l2)
                if inner_prop:
                    inner.append(inner_prop)
                j += 1
            value_branches = alternatives or [inner]
            if any(
                member.name == "@value"
                for branch in value_branches
                for member in branch
            ):
                prop = PropDef(
                    name=nested.group(1),
                    type_ref="value_object",
                    optional=nested.group(2) == "?",
                    object_properties=value_branches[0],
                    object_alternatives=value_branches,
                )
                shape.properties.append(prop)
                i = j + 1
                continue
            # Not a value object. Fall through to the pre-existing handling,
            # which hoists the inner fields onto the outer shape and types the
            # outer property as a plain string. That projection is lossy, but
            # it is the behavior the adversarial corpus was authored against
            # (constraints/adversarial/access-scope-leakage.cue), so tightening
            # it belongs to whichever change re-authors those sources — not to
            # the one adding typed literals.
            #
            # KNOWN HAZARD, not a guardrail. The hoist is field-wise, so an
            # inner `"@type"` OVERWRITES the outer shape's class discriminator:
            # a `#Bad` carrying a nested `{"@type": "rkaf:Inner"}` compiles to a
            # schema whose `@type` is `const: "rkaf:Inner"`, and a binding
            # minted from it would validate the WRONG CLASS. Anyone inlining a
            # struct here (an inline EvidenceBinding, an inline selector) gets a
            # silently wrong artifact. Pinned by
            # `test_non_value_object_nested_struct_hoists_and_is_documented_lossy`
            # so a future tightening surfaces as a test change, not a silent
            # behavior swap.
        # Embedded base shape: a bare `#Base` line composes `#Base` into this
        # shape (CUE struct embedding). Recorded now, merged after parsing.
        embed = EMBEDDED_BASE_RE.match(line)
        if embed:
            if embed.group(1) not in shape.base_refs:
                shape.base_refs.append(embed.group(1))
            i += 1
            continue
        # Property line
        p = parse_property_line(line)
        if p:
            if p.name == "@type" and p.fixed_value:
                shape.type_iri = p.fixed_value
            else:
                shape.properties.append(p)
        i += 1
    return shape, i - start + 1


PROP_RE = re.compile(r'^"([^"]+)"(\?)?:\s*(.+)\s*$')


def _decode_cue_string(value: str) -> str:
    """Decode escapes captured from a CUE quoted string."""
    return json.loads(f'"{value}"')


def parse_property_line(line: str) -> Optional[PropDef]:
    line = line.strip().rstrip(",")
    if not line:
        return None
    m = PROP_RE.match(line)
    if not m:
        return None
    name = m.group(1)
    optional = m.group(2) == "?"
    rhs = m.group(3).rstrip()

    p = PropDef(name=name, type_ref="string", optional=optional)
    if rhs.endswith("@rkafStrictList()"):
        p.list_allow_scalar = False
        rhs = rhs[: -len("@rkafStrictList()")].rstrip()

    # JSON-LD one-or-many reference. The source explicitly admits the scalar
    # spelling and a non-empty array spelling; all generated carriers preserve
    # that union. Reference classification (closed enum versus named object)
    # happens after the complete document has been parsed.
    one_or_many_ref = re.match(
        r"^#(\w+)\s*\|\s*\(\s*\[\.\.\.#\1\]\s*&\s*"
        r"list\.MinItems\((\d+)\)\s*\)$",
        rhs,
    )
    if one_or_many_ref:
        p.type_ref = "list"
        p.list_inner_enum = one_or_many_ref.group(1)
        p.list_min_items = int(one_or_many_ref.group(2))
        return p
    # JSON-LD one-or-many string. This is the value range of the reusable
    # multi-valued language-map carrier.
    one_or_many_string = re.match(
        r"^string\s*\|\s*\(\s*\[\.\.\.string\]\s*&\s*"
        r"list\.MinItems\((\d+)\)\s*\)$",
        rhs,
    )
    if one_or_many_string:
        p.type_ref = "list"
        p.list_of_string = True
        p.list_min_items = int(one_or_many_string.group(1))
        return p
    # Fixed string literal: `"v"`
    lit = re.match(r'^"([^"]+)"$', rhs)
    if lit:
        p.type_ref = "string"
        p.fixed_value = lit.group(1)
        return p
    # Enum reference: `#EnumName`
    em = re.match(r"^#(\w+)$", rhs)
    if em:
        p.type_ref = "enum"
        p.enum_ref = em.group(1)
        return p
    # Strict or JSON-LD-one-or-many list. Bounds may appear in either order;
    # an explicit maximum is required for exact lifecycle cardinalities.
    list_match = re.match(
        r'^\[\.\.\.(#\w+|string|\(string\s*&\s*=~"[^"]+"\))\](.*)$',
        rhs,
    )
    if list_match:
        item = list_match.group(1)
        tail = list_match.group(2)
        bounds = re.findall(
            r'\s*&\s*list\.(Min|Max)Items\((\d+)\)',
            tail,
        )
        consumed = "".join(
            f" & list.{kind}Items({value})" for kind, value in bounds
        )
        if re.sub(r"\s+", "", consumed) != re.sub(r"\s+", "", tail):
            return p
        p.type_ref = "list"
        if item.startswith("#"):
            p.list_inner_enum = item[1:]
        else:
            p.list_of_string = True
            pattern = re.match(r'^\(string\s*&\s*=~"([^"]+)"\)$', item)
            if pattern:
                p.pattern = _decode_cue_string(pattern.group(1))
        for kind, value in bounds:
            if kind == "Min":
                p.list_min_items = int(value)
            else:
                p.list_max_items = int(value)
        if (
            p.list_max_items is not None
            and p.list_max_items < p.list_min_items
        ):
            raise CompileError(
                f'property "{name}" has list.MaxItems below list.MinItems'
            )
        return p
    # Bare list bounds with no item-type constraint. Items may be any JSON
    # value. This preserves the SourceFragment selector carrier behavior.
    bare_bounds = re.findall(
        r'(?:^|\s*&\s*)list\.(Min|Max)Items\((\d+)\)',
        rhs,
    )
    if bare_bounds:
        consumed = " & ".join(
            f"list.{kind}Items({value})" for kind, value in bare_bounds
        )
        if re.sub(r"\s+", "", consumed) == re.sub(r"\s+", "", rhs):
            p.type_ref = "list"
            for kind, value in bare_bounds:
                if kind == "Min":
                    p.list_min_items = int(value)
                else:
                    p.list_max_items = int(value)
            return p
    # `>=N.M & <=N.M`
    nm = re.match(r"^>=\s*(-?[\d.]+)\s*&\s*<=\s*(-?[\d.]+)$", rhs)
    if nm:
        p.type_ref = "float"
        p.min_inclusive = float(nm.group(1))
        p.max_inclusive = float(nm.group(2))
        return p
    # `>=N`
    gm = re.match(r"^>=\s*(-?[\d.]+)$", rhs)
    if gm:
        p.type_ref = "int" if "." not in gm.group(1) else "float"
        p.min_inclusive = float(gm.group(1))
        return p
    # `bool`
    if rhs == "bool":
        p.type_ref = "bool"
        return p
    # `int`
    if rhs == "int":
        p.type_ref = "int"
        return p
    # `string & =~"allowed" & !~"forbidden"`
    pm_both = re.match(
        r'^string\s*&\s*=~"([^"]+)"\s*&\s*!~"([^"]+)"$',
        rhs,
    )
    if pm_both:
        p.type_ref = "string"
        p.pattern = _decode_cue_string(pm_both.group(1))
        p.forbidden_pattern = _decode_cue_string(pm_both.group(2))
        return p
    # `string & =~"pattern"`
    pm = re.match(r'^string\s*&\s*=~"([^"]+)"$', rhs)
    if pm:
        p.type_ref = "string"
        p.pattern = _decode_cue_string(pm.group(1))
        return p
    # `=~"pattern"`
    pm2 = re.match(r'^=~"([^"]+)"$', rhs)
    if pm2:
        p.type_ref = "string"
        p.pattern = _decode_cue_string(pm2.group(1))
        return p
    # `string`
    if rhs == "string":
        p.type_ref = "string"
        return p
    # CUE's strict calendar-date format.
    if rhs == 'time.Format("2006-01-02")':
        p.type_ref = "string"
        p.string_format = "date"
        return p
    # Inline closed enum: `"a" | "b" | "c"`
    if re.match(r'^"[^"]+"\s*\|', rhs) or (rhs.startswith('"') and "|" in rhs):
        vals = ENUM_MULTI_RE.findall(rhs)
        if vals and len(vals) > 1:
            p.type_ref = "string"
            p.inline_enum_values = vals  # consumed by codegen
            return p
    # Inline enum-of-refs: `#A | #B`
    if re.match(r"^#\w+\s*\|", rhs):
        refs = ENUM_UNION_REFS_RE.findall(rhs)
        if refs and len(refs) > 1:
            p.type_ref = "enum_union"
            p.enum_union_refs = refs
            return p
    return p


def _all_document_properties(doc: ConstraintDoc) -> list[PropDef]:
    """Every property occurrence that can reference a named carrier."""
    properties: list[PropDef] = []
    for shape in doc.shapes:
        properties.extend(shape.properties)
        properties.extend(
            prop
            for conditional in shape.conditionals
            for prop in conditional.then_require
        )
        properties.extend(
            prop
            for disjunction in shape.disjunctions
            for branch in disjunction
            for prop in branch.properties
        )
    for object_type in doc.object_types:
        properties.extend(object_type.properties)
    for pattern_map in doc.pattern_maps:
        properties.extend((pattern_map.key, pattern_map.value))
    return properties


def _classify_local_named_references(doc: ConstraintDoc) -> None:
    """Distinguish enum refs from refs to reusable map/object carrier types.

    CUE uses the same `#Name` syntax for both. Parsing the full document before
    classification avoids brittle field-name rules and lets any resource
    property reuse any named carrier.
    """
    named = {
        definition.name
        for definition in [
            *doc.scalar_types,
            *doc.pattern_maps,
            *doc.object_types,
        ]
    }
    scalars = {definition.name: definition for definition in doc.scalar_types}
    if not named:
        return
    for prop in _all_document_properties(doc):
        if prop.type_ref == "enum" and prop.enum_ref in named:
            scalar = scalars.get(prop.enum_ref)
            if scalar is not None:
                replacement = replace(
                    scalar.value,
                    name=prop.name,
                    optional=prop.optional,
                )
                prop.__dict__.update(replacement.__dict__)
                continue
            prop.type_ref = "named"
            prop.named_ref = prop.enum_ref
            prop.enum_ref = None
        if prop.type_ref == "list" and prop.list_inner_enum in named:
            scalar = scalars.get(prop.list_inner_enum)
            if scalar is not None:
                prop.list_of_string = True
                prop.pattern = scalar.value.pattern
                prop.forbidden_pattern = scalar.value.forbidden_pattern
                prop.list_inner_enum = None
                continue
            prop.list_inner_named = prop.list_inner_enum
            prop.list_inner_enum = None
        if prop.type_ref == "value_object":
            for branch in _value_object_branches(prop):
                for inner in branch:
                    if inner.type_ref == "enum" and inner.enum_ref in named:
                        inner.type_ref = "named"
                        inner.named_ref = inner.enum_ref
                        inner.enum_ref = None


def _classify_global_named_references(
    doc: ConstraintDoc, registry: dict[str, object]
) -> None:
    """Resolve scalar/map/object carrier references declared in sibling files."""
    for prop in _all_document_properties(doc):
        if prop.type_ref == "enum" and prop.enum_ref:
            definition = registry.get(prop.enum_ref)
            if isinstance(definition, ScalarTypeDef):
                replacement = replace(
                    definition.value,
                    name=prop.name,
                    optional=prop.optional,
                )
                prop.__dict__.update(replacement.__dict__)
            elif isinstance(definition, (PatternMapDef, ObjectTypeDef)):
                prop.type_ref = "named"
                prop.named_ref = prop.enum_ref
                prop.enum_ref = None
        if prop.type_ref == "list" and prop.list_inner_enum:
            definition = registry.get(prop.list_inner_enum)
            if isinstance(definition, ScalarTypeDef):
                prop.list_of_string = True
                prop.pattern = definition.value.pattern
                prop.forbidden_pattern = definition.value.forbidden_pattern
                prop.list_inner_enum = None
            elif isinstance(definition, (PatternMapDef, ObjectTypeDef)):
                prop.list_inner_named = prop.list_inner_enum
                prop.list_inner_enum = None
        if prop.type_ref == "value_object":
            for branch in _value_object_branches(prop):
                for inner in branch:
                    if inner.type_ref != "enum" or not inner.enum_ref:
                        continue
                    definition = registry.get(inner.enum_ref)
                    if isinstance(definition, ScalarTypeDef):
                        replacement = replace(
                            definition.value,
                            name=inner.name,
                            optional=inner.optional,
                        )
                        inner.__dict__.update(replacement.__dict__)
                    elif isinstance(definition, (PatternMapDef, ObjectTypeDef)):
                        inner.type_ref = "named"
                        inner.named_ref = inner.enum_ref
                        inner.enum_ref = None


def _prepare_named_references(
    doc: ConstraintDoc,
    registry: Optional[dict],
    source_file: Optional[Path] = None,
) -> None:
    if source_file is None:
        source_file = doc.source_file
    if registry is None and source_file is not None:
        registry = _scan_global_enum_registry(source_file)
    if registry:
        _classify_global_named_references(doc, registry)
    for pattern_map in doc.pattern_maps:
        _validate_pattern_map(pattern_map, allow_unresolved=False)
    _validate_document_value_objects(doc, allow_unresolved=False)


def _validate_named_value_object(definition: ObjectTypeDef) -> None:
    """Validate the closed named typed-literal carrier.

    The public CUE syntax is a normal named object. It becomes this carrier
    only when it declares `@value`, so the behavior follows JSON-LD semantics
    rather than a vocabulary field name.
    """
    by_name = {prop.name: prop for prop in definition.properties}
    unknown = sorted(set(by_name) - {"@value", "@type"})
    if unknown:
        raise CompileError(
            f"named value object #{definition.name} declares unsupported "
            f"member(s) {unknown}; typed literals contain only @value and @type"
        )
    if set(by_name) != {"@value", "@type"}:
        raise CompileError(
            f"named value object #{definition.name} MUST carry exactly "
            "`@value` and `@type`"
        )
    lexical = by_name["@value"]
    datatype = by_name["@type"]
    if (
        lexical.optional
        or lexical.type_ref != "string"
        or lexical.fixed_value is not None
    ):
        raise CompileError(
            f"named value object #{definition.name} MUST require a string "
            "`@value`"
        )
    if (
        datatype.optional
        or datatype.type_ref != "string"
        or not datatype.pattern
    ):
        raise CompileError(
            f"named value object #{definition.name} MUST require `@type` "
            "with an absolute-datatype-IRI pattern"
        )
    try:
        compiled = re.compile(datatype.pattern)
    except re.error as exc:
        raise CompileError(
            f"named value object #{definition.name} has an invalid datatype "
            f"pattern: {exc}"
        ) from exc
    if (
        compiled.fullmatch("https://example.org/datatype") is None
        or compiled.fullmatch("urn:example:datatype") is None
        or compiled.fullmatch("relative/type") is not None
    ):
        raise CompileError(
            f"named value object #{definition.name} `@type` pattern MUST "
            "accept arbitrary absolute IRIs and reject relative IRIs"
        )


def _validate_value_object(
    prop: PropDef, *, allow_unresolved: bool = False
) -> None:
    """Reject an inline nested object that is not a JSON-LD value object.

    A value object is a struct whose `@value` holds the lexical form and whose
    `@type` names the datatype IRI. That is the ONE nested shape every target
    can carry faithfully: JSON Schema as an object schema, SHACL as a literal
    with a closed `sh:datatype` set, Rust/TypeScript as a typed carrier. Any
    other nested struct would have to degrade to "some JSON", which is exactly
    the silent weakening `CompileError` exists to prevent.
    """
    branches = _value_object_branches(prop)
    for branch in branches:
        members = [inner.name for inner in branch]
        if "@value" not in members:
            raise CompileError(
                f'property "{prop.name}" declares a value-object branch that '
                "does not carry `@value`."
            )
        unknown = sorted(set(members) - VALUE_OBJECT_MEMBERS)
        if unknown:
            raise CompileError(
                f'value object "{prop.name}" declares non-JSON-LD member(s) '
                f"{unknown}. A JSON-LD value object holds only @value, @type, "
                "and @language."
            )
        datatype = _branch_member(branch, "@type")
        language = _branch_member(branch, "@language")
        if (datatype is None) == (language is None):
            raise CompileError(
                f'value object "{prop.name}" branch MUST carry exactly one of '
                "`@type` or `@language`."
            )
        if datatype is not None and datatype.enum_ref is None:
            raise CompileError(
                f'value object "{prop.name}" does not type its `@type` member '
                "with a closed datatype enum."
            )
        if language is not None and not language.pattern:
            if (
                allow_unresolved
                and language.type_ref == "enum"
                and language.enum_ref
            ):
                continue
            raise CompileError(
                f'value object "{prop.name}" does not validate its `@language` '
                "member as a BCP 47 language tag."
            )


def _validate_document_value_objects(
    doc: ConstraintDoc, *, allow_unresolved: bool
) -> None:
    for prop in _all_document_properties(doc):
        if prop.type_ref == "value_object":
            _validate_value_object(
                prop,
                allow_unresolved=allow_unresolved,
            )


def _value_object_branches(prop: PropDef) -> list[list[PropDef]]:
    return prop.object_alternatives or [prop.object_properties or []]


def _branch_member(branch: list[PropDef], name: str) -> Optional[PropDef]:
    for inner in branch:
        if inner.name == name:
            return inner
    return None


def _value_object_member(prop: PropDef, name: str) -> Optional[PropDef]:
    """The `@value` / `@type` / `@language` member of a value-object property."""
    for branch in _value_object_branches(prop):
        member = _branch_member(branch, name)
        if member is not None:
            return member
    return None


# ---- Shape composition ---------------------------------------------------
#
# CUE composes shapes by unification; the projector composes them by flattening
# the base into the derived shape before any target emitter runs. Every target
# therefore sees one complete shape, and the ontology never has to duplicate an
# envelope to work around a projector limitation.
#
# Governing rule: composition may DE-DUPLICATE, never LOOSEN. Whatever `cue vet`
# enforces on a composed shape must still be enforced by every compiled target.
# Anything the projector cannot express faithfully is a `CompileError`, never a
# silently weaker artifact.

# Sibling CUE files parsed with composition left unresolved. Building the shape
# registry re-reads every file under `constraints/`; the cache keeps the
# repeated scans (one per target per primitive) cheap.
_UNRESOLVED_DOC_CACHE: dict[Path, ConstraintDoc] = {}


class CompileError(Exception):
    """A CUE source the projector cannot project without losing semantics.

    Raised in place of a silent degradation: dropping an unresolvable base, a
    file that failed to parse, or a conflicting facet would make the compiled
    JSON Schema / SHACL / Rust / TypeScript accept values that `cue vet`
    rejects. Surfacing the failure keeps the carriers honest.
    """


def _constraints_root(source_file: Path) -> Optional[Path]:
    resolved = source_file.resolve()
    for ancestor in (resolved.parent, *resolved.parents):
        if ancestor.name == "constraints":
            return ancestor
    return None


def _shape_registry(source_file: Path) -> dict[str, ShapeDef]:
    """Every shape defined under `constraints/`, keyed by CUE definition name.

    Composition crosses files — `#RelationshipAssertion` composes the
    `#AssertionEnvelope` declared in `assertion.cue` — so bases resolve the same
    way cross-file enum references already do.

    A sibling file that fails to parse is fatal: skipping it shrinks the
    registry, and a base declared in the skipped file would then resolve to
    "missing" and drop the constraints it carries.
    """
    registry: dict[str, ShapeDef] = {}
    root = _constraints_root(source_file)
    if root is None:
        return registry
    for cue_file in sorted(root.rglob("*.cue")):
        key = cue_file.resolve()
        doc = _UNRESOLVED_DOC_CACHE.get(key)
        if doc is None:
            try:
                doc = parse_cue_file(cue_file, resolve_composition=False)
            except Exception as exc:  # noqa: BLE001 — re-raised as CompileError
                raise CompileError(
                    f"cannot build the shape registry for {source_file}: "
                    f"sibling constraint file {cue_file} failed to parse "
                    f"({type(exc).__name__}: {exc}). Any base shape it declares "
                    "would be silently lost from every compiled target."
                ) from exc
            _UNRESOLVED_DOC_CACHE[key] = doc
        for shape in doc.shapes:
            registry.setdefault(shape.name, shape)
    return registry


# Facets a property declaration can carry, with the value the parser leaves in
# place when the CUE text does not declare that facet. "Declared" means "differs
# from the default", which is what lets unification tell a derived narrowing
# (adds a facet) apart from a derived restatement (declares nothing new).
_PROPERTY_FACET_DEFAULTS: dict[str, object] = {
    "type_ref": "string",
    "enum_ref": None,
    "named_ref": None,
    "list_inner_enum": None,
    "list_inner_named": None,
    "list_min_items": 0,
    "list_max_items": None,
    "list_unique_items": False,
    "list_allow_scalar": True,
    "list_of_string": False,
    "fixed_value": None,
    "pattern": None,
    "forbidden_pattern": None,
    "string_format": None,
    "min_inclusive": None,
    "max_inclusive": None,
    "inline_enum_values": None,
    "enum_union_refs": None,
    "object_properties": None,
    "object_alternatives": None,
}

# Facets whose conjunction IS expressible in the flat AST, so two differing
# declarations narrow instead of raising: a bound unified with another bound is
# just the tighter bound, which every target already emits. Every other facet
# (pattern, enum ref, format, fixed value…) would need a real conjunction the
# flat PropDef cannot carry, so a genuine conflict there is a hard error.
_NARROWING_FACETS = {
    "min_inclusive": max,
    "list_min_items": max,
    "list_max_items": min,
    "list_unique_items": lambda base, derived: bool(base or derived),
    "list_allow_scalar": lambda base, derived: bool(base and derived),
    "max_inclusive": min,
}


def _copy_property(prop: PropDef) -> PropDef:
    """Detached copy, so composing a base never mutates the registry entry."""
    return replace(prop)


def _unify_property(
    base: PropDef, derived: PropDef, shape_name: str
) -> PropDef:
    """Unify two declarations of the same property, the way CUE would.

    Facet by facet: the merged property keeps the base's facet unless the
    derived declares that same facet, in which case the derived value narrows
    it. Required-ness is the OR of both — CUE unification cannot widen, so a
    base-required field stays required even if the derived spells it `?`.

    Two DIFFERENT values for the same facet unify conjunctively where the flat
    AST can carry the conjunction (numeric and cardinality bounds collapse to
    the tighter bound). Anything else — two patterns, two enum refs, two fixed
    values, two formats — would need a real conjunction PropDef cannot hold, so
    it raises rather than silently keeping one of them.
    """
    merged = PropDef(name=base.name, type_ref=base.type_ref)
    for facet, default in _PROPERTY_FACET_DEFAULTS.items():
        base_value = getattr(base, facet)
        derived_value = getattr(derived, facet)
        base_declared = base_value != default
        derived_declared = derived_value != default
        if base_declared and derived_declared and base_value != derived_value:
            narrow = _NARROWING_FACETS.get(facet)
            if narrow is None:
                raise CompileError(
                    f"unsupported composition in shape #{shape_name}: property "
                    f'"{base.name}" declares conflicting {facet} values '
                    f"({base_value!r} in the base, {derived_value!r} in the "
                    "derived body). CUE would unify these conjunctively; the "
                    "flat projector cannot carry both, and picking one would "
                    "loosen or contradict the source."
                )
            setattr(merged, facet, narrow(base_value, derived_value))
            continue
        setattr(merged, facet, derived_value if derived_declared else base_value)
    # Unification narrows: a field required by either declaration is required.
    merged.optional = base.optional and derived.optional
    return merged


def _upsert_property(
    properties: list[PropDef], prop: PropDef, shape_name: str
) -> None:
    """Unify `prop` into `properties`, keeping its inherited position."""
    for index, existing in enumerate(properties):
        if existing.name == prop.name:
            properties[index] = _unify_property(existing, prop, shape_name)
            return
    properties.append(_copy_property(prop))


def _unify_conditional(
    base: ConditionalBranch, derived: ConditionalBranch, shape_name: str
) -> ConditionalBranch:
    """Unify two branches guarded by the same condition.

    Same rule as properties: the merged branch requires the union of both
    requirement sets, and a property required by both is unified facet by facet
    so a derived restatement cannot drop the base's pattern.
    """
    then_require = [_copy_property(prop) for prop in base.then_require]
    for prop in derived.then_require:
        _upsert_property(then_require, prop, shape_name)
    then_forbid = list(dict.fromkeys([*base.then_forbid, *derived.then_forbid]))
    return ConditionalBranch(
        when_property=base.when_property,
        when_equals=base.when_equals,
        then_require=then_require,
        when_not_equals=base.when_not_equals,
        then_forbid=then_forbid,
    )


def _append_conditional(
    branches: list[ConditionalBranch],
    branch: ConditionalBranch,
    shape_name: str,
) -> None:
    key = (
        branch.when_property,
        branch.when_equals,
        branch.when_not_equals,
    )
    for index, existing in enumerate(branches):
        if (
            existing.when_property,
            existing.when_equals,
            existing.when_not_equals,
        ) == key:
            branches[index] = _unify_conditional(existing, branch, shape_name)
            return
    branches.append(
        ConditionalBranch(
            when_property=branch.when_property,
            when_equals=branch.when_equals,
            then_require=[_copy_property(p) for p in branch.then_require],
            when_not_equals=branch.when_not_equals,
            then_forbid=list(branch.then_forbid),
        )
    )


def _compose_shape(
    shape: ShapeDef,
    registry: dict[str, ShapeDef],
    stack: tuple[str, ...] = (),
) -> ShapeDef:
    """Return `shape` with every `base_refs` entry flattened into it.

    Bases contribute first (so inherited properties keep their declaration
    order); the derived body then unifies over them, narrowing inherited
    properties in place and appending its own.
    """
    if shape.name in stack:
        raise CompileError(
            "cyclic CUE shape composition: "
            + " -> ".join([*stack, shape.name])
            + ". Composing a cycle would emit partial, asymmetric shapes that "
            "differ per entry point."
        )
    if not shape.base_refs:
        return shape
    stack = (*stack, shape.name)
    merged = ShapeDef(name=shape.name, type_iri=None)
    for ref in shape.base_refs:
        base = registry.get(ref)
        if base is None:
            raise CompileError(
                f"shape #{shape.name} composes #{ref}, which no CUE file under "
                "constraints/ defines. Compiling it as-is would silently drop "
                "every constraint the base carries from the generated targets."
            )
        base = _compose_shape(base, registry, stack)
        for prop in base.properties:
            _upsert_property(merged.properties, prop, shape.name)
        for branch in base.conditionals:
            _append_conditional(merged.conditionals, branch, shape.name)
        merged.orders.extend(base.orders)
        for constraint in base.not_equals:
            if constraint not in merged.not_equals:
                merged.not_equals.append(constraint)
        merged.disjunctions.extend(base.disjunctions)
    # `type_iri` is deliberately NOT inherited. A shape's `@type` binds the
    # generated artifacts to an RDF class: inheriting it would make the derived
    # shape emit a second SHACL NodeShape targeting the base's class (colliding
    # with the hand-authored normative shape for that class) and a duplicate
    # `@type` const across two JSON Schema `$defs`. Composition reuses the
    # base's fields; it must not re-bind the base's class identity.
    merged.type_iri = shape.type_iri
    for prop in shape.properties:
        _upsert_property(merged.properties, prop, shape.name)
    for branch in shape.conditionals:
        _append_conditional(merged.conditionals, branch, shape.name)
    merged.orders.extend(shape.orders)
    for constraint in shape.not_equals:
        if constraint not in merged.not_equals:
            merged.not_equals.append(constraint)
    merged.disjunctions.extend(shape.disjunctions)
    return merged


def _resolve_shape_compositions(doc: ConstraintDoc, source_file: Path) -> None:
    if not any(shape.base_refs for shape in doc.shapes):
        return
    registry = _shape_registry(source_file)
    for shape in doc.shapes:
        registry[shape.name] = shape  # definitions in this file win
    doc.shapes = [_compose_shape(shape, registry) for shape in doc.shapes]


# ---- Value-set assembly --------------------------------------------------
#
# A closed value set may be assembled from more than one module: the kernel
# declares the values it owns, a profile declares its own, and a union
# (`#Whole: #KernelPart | #ProfilePart`) names the closed whole-contract set.
# CUE resolves those references across files inside one instance; the projector
# resolves them across files through the enum registry, so every target emits
# the SAME assembled set instead of silently dropping the half it cannot see.


def _resolve_enum_values(
    name: str,
    doc: ConstraintDoc,
    registry: Optional[dict] = None,
    _stack: tuple[str, ...] = (),
) -> list[str]:
    """Ordered literal values of an enum or enum-union, resolved across files.

    Definitions in `doc` win over the registry (same rule as shape
    composition), then the cross-file registry is consulted. Order is the
    declaration order of the union's refs, so the assembled set is
    deterministic and the contract digest does not depend on scan order.

    A reference that resolves nowhere raises rather than contributing zero
    values: a union that silently loses one of its parts compiles to a target
    that ACCEPTS FEWER values than the CUE, and a dropped `sh:in` / `enum`
    member is exactly the kind of quiet weakening `CompileError` exists for.

    The single exception is a caller that supplied NO registry asking for a
    top-level name this document does not declare: it has told the resolver it
    cannot see other files, so the honest answer is "no values known here"
    (the emitter then omits the closure entirely) rather than a fabricated
    partial set. Inside a union there is no such answer — a half-assembled
    union is a wrong closed set — so that always raises.
    """
    if name in _stack:
        raise CompileError(
            "cyclic enum union: " + " -> ".join([*_stack, name]) +
            ". A union that references itself has no fixed point; the "
            "assembled value set would depend on where resolution started."
        )
    stack = (*_stack, name)

    for enum in doc.enums:
        if enum.name == name:
            return list(enum.values)
    for union in doc.enum_unions:
        if union.name == name:
            values: list[str] = []
            for ref in union.refs:
                values.extend(_resolve_enum_values(ref, doc, registry, stack))
            return values

    entry = registry.get(name) if registry else None
    if isinstance(entry, EnumDef):
        return list(entry.values)
    if isinstance(entry, EnumUnion):
        values = []
        for ref in entry.refs:
            values.extend(_resolve_enum_values(ref, doc, registry, stack))
        return values

    if registry is None and not _stack:
        return []

    raise CompileError(
        f"enum reference #{name} resolves to no CUE definition"
        + (f" (referenced from #{_stack[-1]})" if _stack else "")
        + ". Emitting the value set without it would close the compiled target "
        "over FEWER values than the CUE source declares."
    )


# ---- JSON Schema target --------------------------------------------------

def _scan_global_enum_registry(source_file: Path) -> dict:
    """Scan sibling CUE files for globally reusable definitions.

    The historical function name remains for callers, but the registry now
    contains enums, enum unions, constrained scalars, pattern maps, and closed
    object carriers. Cross-file language carriage requires the same
    deterministic single-owner rule as cross-file value sets.
    """
    registry: dict = {}
    p = source_file.resolve()
    constraints_root = None
    for ancestor in [p.parent, *p.parents]:
        if ancestor.name == "constraints":
            constraints_root = ancestor
            break
    if constraints_root is None:
        return registry
    # Sorted, not raw `rglob`: the registry now feeds SHACL and Rego closures
    # as well as JSON Schema/Rust/TypeScript, so scan order would otherwise
    # decide which definition a name resolves to — and the contract digest with
    # it. A duplicate name is a hard error rather than first-wins for the same
    # reason: two files declaring one name means "which values does this
    # closure hold" has no single answer, and silently picking one ships a
    # compiled artifact that disagrees with the CUE half of the time.
    for cue_file in sorted(constraints_root.rglob("*.cue")):
        try:
            sibling = parse_cue_file(cue_file)
        except CompileError:
            # A composition the projector cannot project faithfully is a hard
            # error everywhere, including while scanning siblings.
            raise
        except Exception:
            continue
        package = cue_file.stem  # e.g. "usage-eligibility"
        relpath = cue_file.resolve().relative_to(constraints_root).with_suffix("")
        for definition in [
            *sibling.enums,
            *sibling.enum_unions,
            *sibling.scalar_types,
            *sibling.pattern_maps,
            *sibling.object_types,
        ]:
            name = definition.name
            if name in registry:
                raise CompileError(
                    f"definition #{name} is declared by both "
                    f"{_REGISTRY_RELPATHS[name]}.cue and {relpath.as_posix()}"
                    ".cue. A cross-file reference to #"
                    f"{name} would resolve to whichever file the scan reached "
                    "first, so the compiled value set — and the contract "
                    "digest — would depend on filesystem order. Rename one."
                )
            registry[name] = definition
            _REGISTRY_SOURCES[name] = package
            _REGISTRY_RELPATHS[name] = relpath.as_posix()
    return registry


def _source_relpath(source_file: Path) -> Optional[str]:
    """`constraints/`-relative, extension-free path of a CUE source file.

    `core/artifact`, `profiles/us-rulemaking/rulemaking`. This is what lets the
    Rust and TypeScript emitters address a cross-file enum that lives in a
    different constraint sub-tree — a profile shape composing a kernel shape is
    exactly that case.
    """
    root = _constraints_root(source_file)
    if root is None:
        return None
    return source_file.resolve().relative_to(root).with_suffix("").as_posix()


def _source_header(doc: ConstraintDoc, source_file: Optional[Path]) -> str:
    """The `Source:` provenance line every generated target carries.

    Names the REAL path under `constraints/`, so a profile output points at
    `constraints/profiles/us-rulemaking/rulemaking.cue` rather than a
    `constraints/rulemaking.cue` that does not exist. Falls back to the flat
    package name when the emitter was handed no source path (unit tests call
    the targets directly).
    """
    relpath = _source_relpath(source_file) if source_file is not None else None
    return f"constraints/{relpath or doc.package}.cue"


def range_registry_paths(constraints_root: Path) -> list[Path]:
    """Every `l0-ranges.cue` under `constraints/`, kernel first.

    The kernel declares the ranges of the properties it owns; each profile
    declares its own next to the shapes that use them. Ordering is deterministic
    so the contract digest and the emitted `sh:class` triples do not depend on
    filesystem traversal order.
    """
    return sorted(
        constraints_root.rglob("l0-ranges.cue"),
        key=lambda path: (
            0 if path.parent.parent.name == "constraints" else 1,
            path.as_posix(),
        ),
    )


def _scan_reference_class_registry(source_file: Path) -> dict[str, str]:
    """Load property range classes shared by L0 and SHACL projection.

    The range registry is the semantic source of truth for reference-valued
    predicates. Keeping SHACL generation on the same registry prevents the L0
    audit from declaring a class range that generated graph validation does
    not enforce.

    The registry is the union of every `l0-ranges.cue` under `constraints/`, so
    a profile that owns a reference-valued predicate owns its range too.
    """
    source = source_file.resolve()
    constraints_root = next(
        (ancestor for ancestor in (source.parent, *source.parents) if ancestor.name == "constraints"),
        None,
    )
    if constraints_root is None:
        return {}
    ranges: dict[str, str] = {}
    for range_path in range_registry_paths(constraints_root):
        for term, target in re.findall(
            r'^\s*"([^"]+)":\s*"([^"]+)"',
            range_path.read_text(),
            re.MULTILINE,
        ):
            ranges[term] = target
    return ranges


def target_json_schema(doc: ConstraintDoc, registry: Optional[dict] = None) -> str:
    _prepare_named_references(doc, registry)
    schemas: dict = {}
    for e in doc.enums:
        schemas[e.name] = {"type": "string", "enum": e.values}
    # Enum-unions: collapse to a single closed enum from the union of
    # referenced values. Refs may cross files (a profile assembling the closed
    # whole-contract set from the kernel's values plus its own).
    for u in doc.enum_unions:
        schemas[u.name] = {
            "type": "string",
            "enum": _resolve_enum_values(u.name, doc, registry),
        }
    for scalar in doc.scalar_types:
        schemas[scalar.name] = property_to_jsonschema(
            scalar.value, doc, registry
        )
    for map_def in doc.pattern_maps:
        schemas[map_def.name] = {
            "type": "object",
            "propertyNames": property_to_jsonschema(map_def.key, doc, registry),
            "additionalProperties": property_to_jsonschema(
                map_def.value, doc, registry
            ),
            "minProperties": map_def.min_properties,
        }
    for object_type in doc.object_types:
        object_properties = {
            prop.name: property_to_jsonschema(prop, doc, registry)
            for prop in object_type.properties
        }
        required = [
            prop.name for prop in object_type.properties if not prop.optional
        ]
        schema: dict = {
            "type": "object",
            "properties": object_properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        schemas[object_type.name] = schema

    # Inline cross-file enum definitions referenced by this doc's properties /
    # disjunctions / conditionals so the resulting schema is self-contained.
    # This makes embedded validators (rkaf-validate) able to resolve every
    # `$ref` without splicing in sibling schemas at load time.
    def _inline_cross_file(enum_name: str) -> None:
        if enum_name in schemas or registry is None:
            return
        if registry.get(enum_name) is None:
            return
        schemas[enum_name] = {
            "type": "string",
            "enum": _resolve_enum_values(enum_name, doc, registry),
        }

    def _inline_cross_file_carrier(name: str) -> None:
        if name in schemas or registry is None:
            return
        definition = registry.get(name)
        if isinstance(definition, ScalarTypeDef):
            schemas[name] = property_to_jsonschema(
                definition.value, doc, registry
            )
        elif isinstance(definition, PatternMapDef):
            schemas[name] = {
                "type": "object",
                "propertyNames": property_to_jsonschema(
                    definition.key, doc, registry
                ),
                "additionalProperties": property_to_jsonschema(
                    definition.value, doc, registry
                ),
                "minProperties": definition.min_properties,
            }
        elif isinstance(definition, ObjectTypeDef):
            properties = {
                prop.name: property_to_jsonschema(prop, doc, registry)
                for prop in definition.properties
            }
            schemas[name] = {
                "type": "object",
                "properties": properties,
                "required": [
                    prop.name
                    for prop in definition.properties
                    if not prop.optional
                ],
                "additionalProperties": False,
            }

    if registry:
        for s in doc.shapes:
            for p in s.properties:
                if p.type_ref == "named" and p.named_ref:
                    _inline_cross_file_carrier(p.named_ref)
                if p.type_ref == "list" and p.list_inner_named:
                    _inline_cross_file_carrier(p.list_inner_named)
                if p.type_ref == "enum" and p.enum_ref:
                    _inline_cross_file(p.enum_ref)
                if p.type_ref == "list" and p.list_inner_enum:
                    _inline_cross_file(p.list_inner_enum)
                if p.type_ref == "value_object":
                    for inner in p.object_properties or []:
                        if inner.type_ref == "enum" and inner.enum_ref:
                            _inline_cross_file(inner.enum_ref)
            for c in s.conditionals:
                for tp in c.then_require:
                    if tp.type_ref == "enum" and tp.enum_ref:
                        _inline_cross_file(tp.enum_ref)
            for disj in s.disjunctions:
                for br in disj:
                    for bp in br.properties:
                        if bp.type_ref == "enum" and bp.enum_ref:
                            _inline_cross_file(bp.enum_ref)
    for s in doc.shapes:
        props: dict = {}
        required: list[str] = []
        # Collect property names that appear in any disjunction branch — these
        # are alternatives, not always-required fields.
        disjunction_prop_names: set[str] = set()
        for disj in s.disjunctions:
            for br in disj:
                for bp in br.properties:
                    disjunction_prop_names.add(bp.name)
                    # Add to top-level props so anyOf can reference them
                    if bp.name not in props:
                        props[bp.name] = property_to_jsonschema(bp, doc, registry)
        if s.type_iri:
            props["@type"] = {"const": s.type_iri}
            required.append("@type")
        for p in s.properties:
            props[p.name] = property_to_jsonschema(p, doc, registry)
            if not p.optional and p.name not in disjunction_prop_names:
                required.append(p.name)
        # Conditional branches → JSON Schema `allOf` with `if/then`
        all_of: list[dict] = []
        for c in s.conditionals:
            then_props: dict = {}
            for tp in c.then_require:
                then_props[tp.name] = property_to_jsonschema(tp, doc, registry)
                if tp.name not in props:
                    props[tp.name] = property_to_jsonschema(tp, doc, registry)
            if c.when_equals is None:
                condition = {"required": [c.when_property]}
            else:
                equals_condition = {
                    "properties": {
                        c.when_property: {
                            "anyOf": [
                                {"const": c.when_equals},
                                {
                                    "type": "array",
                                    "contains": {"const": c.when_equals},
                                },
                            ]
                        }
                    },
                    "required": [c.when_property],
                }
                condition = (
                    {"not": equals_condition}
                    if c.when_not_equals
                    else equals_condition
                )
            then_schema: dict = {}
            if then_props:
                then_schema["properties"] = then_props
                then_schema["required"] = list(then_props.keys())
            if c.then_forbid:
                then_schema.setdefault("allOf", []).extend(
                    {"not": {"required": [name]}} for name in c.then_forbid
                )
            all_of.append({"if": condition, "then": then_schema})
        # Disjunction branches → anyOf — each branch requires its own properties
        any_of_groups: list[dict] = []
        for disj in s.disjunctions:
            alts = []
            for br in disj:
                br_props: dict = {}
                br_req: list[str] = []
                for bp in br.properties:
                    br_props[bp.name] = property_to_jsonschema(bp, doc, registry)
                    if not bp.optional:
                        br_req.append(bp.name)
                alts.append({"properties": br_props, "required": br_req})
            any_of_groups.append({"anyOf": alts})
        schema: dict = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        if all_of:
            schema["allOf"] = all_of
        if any_of_groups:
            schema.setdefault("allOf", []).extend(any_of_groups)
        if s.orders:
            schema["x-rkaf-order"] = [
                {
                    "lower": order.lower_property,
                    "upper": order.upper_property,
                }
                for order in s.orders
            ]
        if s.not_equals:
            schema["x-rkaf-not-equal"] = [
                {
                    "left": constraint.left_property,
                    "right": constraint.right_property,
                }
                for constraint in s.not_equals
            ]
        schemas[s.name] = schema

    envelope = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://rulespec.org/jsonschema/{doc.package}.json",
        "title": doc.package,
        "$defs": schemas,
    }
    return json.dumps(envelope, indent=2)


def property_to_jsonschema(
    p: PropDef, doc: ConstraintDoc, registry: Optional[dict] = None
) -> dict:
    if p.type_ref == "value_object":
        # JSON-LD value objects are mutually exclusive closed branches:
        # typed literal or RDF 1.1 language-tagged string.
        alternatives: list[dict] = []
        for branch in _value_object_branches(p):
            obj_props: dict = {}
            obj_required: list[str] = []
            for inner in branch:
                obj_props[inner.name] = property_to_jsonschema(
                    inner, doc, registry
                )
                if not inner.optional:
                    obj_required.append(inner.name)
            obj: dict = {
                "type": "object",
                "properties": obj_props,
                "additionalProperties": False,
            }
            if obj_required:
                obj["required"] = obj_required
            alternatives.append(obj)
        return alternatives[0] if len(alternatives) == 1 else {"oneOf": alternatives}
    if p.fixed_value is not None:
        return {"const": p.fixed_value}
    if p.inline_enum_values:
        return {"type": "string", "enum": p.inline_enum_values}
    if p.enum_union_refs:
        # Resolve to a single closed enum from the referenced enums, which may
        # be declared in another file.
        vals: list[str] = []
        for ref in p.enum_union_refs:
            # `("<inline union>",)`: an inline union is still a union, so a
            # ref that resolves nowhere raises instead of assembling half a
            # closed set — even when the caller passed no registry.
            vals.extend(
                _resolve_enum_values(ref, doc, registry, ("<inline union>",))
            )
        return {"type": "string", "enum": vals}
    if p.type_ref == "enum":
        return {"$ref": f"#/$defs/{p.enum_ref}"}
    if p.type_ref == "named":
        return {"$ref": f"#/$defs/{p.named_ref}"}
    if p.type_ref == "list":
        items: dict
        if p.list_inner_enum:
            items = {"$ref": f"#/$defs/{p.list_inner_enum}"}
        elif p.list_inner_named:
            items = {"$ref": f"#/$defs/{p.list_inner_named}"}
        elif p.list_of_string:
            items = {"type": "string"}
        else:
            # Bare `list.MinItems(N)` — items may be any JSON value.
            items = {}
        if p.pattern:
            items["pattern"] = p.pattern
        if p.string_format:
            items["format"] = p.string_format
        arr: dict = {"type": "array", "items": items}
        if p.list_min_items > 0:
            arr["minItems"] = p.list_min_items
        if p.list_max_items is not None:
            arr["maxItems"] = p.list_max_items
        if p.list_unique_items:
            arr["uniqueItems"] = True
        # JSON-LD coercion: a single scalar is semantically a one-element list.
        # Strict authored arrays, lists requiring two or more members, and
        # impossible one-member maxima must stay arrays at the source layer.
        scalar_allowed = (
            p.list_allow_scalar
            and p.list_min_items <= 1
            and (p.list_max_items is None or p.list_max_items >= 1)
        )
        return {"anyOf": [items, arr]} if scalar_allowed else arr
    if p.type_ref == "int":
        out = {"type": "integer"}
        if p.min_inclusive is not None:
            out["minimum"] = int(p.min_inclusive)
        return out
    if p.type_ref == "float":
        out = {"type": "number"}
        if p.min_inclusive is not None:
            out["minimum"] = p.min_inclusive
        if p.max_inclusive is not None:
            out["maximum"] = p.max_inclusive
        return out
    if p.type_ref == "bool":
        return {"type": "boolean"}
    # string
    out = {"type": "string"}
    if p.pattern:
        out["pattern"] = p.pattern
    if p.forbidden_pattern:
        out["not"] = {"pattern": p.forbidden_pattern}
    if p.string_format:
        out["format"] = p.string_format
        if p.string_format == "date":
            # Draft 2020-12 implementations are allowed to treat ``format`` as
            # annotation-only. The pattern is an enforceable lexical floor;
            # calendar validity and cross-field ordering still require a
            # format-asserting / x-rkaf-order-aware validator or SHACL.
            out["pattern"] = r"^\d{4}-\d{2}-\d{2}$"
            out["$comment"] = (
                "Lexical date guard only. Calendar validity and interval "
                "ordering require the Rulespec validator or SHACL."
            )
    return out


# ---- Rust target ---------------------------------------------------------

def target_rust(
    doc: ConstraintDoc,
    registry: Optional[dict] = None,
    source_file: Optional[Path] = None,
) -> str:
    _prepare_named_references(doc, registry, source_file)
    out: list[str] = [
        "// AUTO-GENERATED by tools/constraints_compile.py",
        f"// Source: {_source_header(doc, source_file)}",
        "// DO NOT EDIT.",
        "",
        "use serde::{Deserialize, Serialize};",
        "",
    ]
    for e in doc.enums:
        out.append(f"/// Closed Rulespec values for `{e.name}`.")
        out.append("#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]")
        out.append(f"pub enum {e.name} {{")
        for v in e.values:
            variant = _pascal_after_colon(v)
            out.append(f"    /// Wire value `{v}`.")
            out.append(f'    #[serde(rename = "{v}")]')
            out.append(f"    {variant},")
        out.append("}")
        out.append("")
    # Enum unions: emit as Rust enum with variants flattened from the
    # referenced enums, including any declared in another CUE file.
    for u in doc.enum_unions:
        out.append(f"/// Closed Rulespec values for `{u.name}`.")
        out.append("#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]")
        out.append(f"pub enum {u.name} {{")
        for v in _resolve_enum_values(u.name, doc, registry):
            variant = _pascal_after_colon(v)
            out.append(f"    /// Wire value `{v}`.")
            out.append(f'    #[serde(rename = "{v}")]')
            out.append(f"    {variant},")
        out.append("}")
        out.append("")

    # Local enum index — used by _rust_type to decide whether an enum reference
    # is local (bare name) or cross-file (fully-qualified path).
    local_enums = (
        {e.name for e in doc.enums}
        | {u.name for u in doc.enum_unions}
        | {definition.name for definition in doc.scalar_types}
        | {definition.name for definition in doc.pattern_maps}
        | {definition.name for definition in doc.object_types}
    )

    # Some composed conditionals narrow a broadly typed carrier field to a
    # cross-file enum without changing the struct field's broad Rust type.
    # A fixed value can similarly replace an enum-typed field with `String`.
    # Keep only THOSE otherwise invisible enums in the generated carrier's
    # dependency set. Ordinary enum-valued fields already carry their path,
    # and local enums are declared in this file.
    structural_only_props = [
        prop
        for shape in doc.shapes
        for prop in (
            [
                shape_prop
                for shape_prop in shape.properties
                if shape_prop.fixed_value is not None
            ]
            + [
                required
                for conditional in shape.conditionals
                for required in conditional.then_require
            ]
            + [
                branch_prop
                for disjunction in shape.disjunctions
                for branch in disjunction
                for branch_prop in branch.properties
            ]
        )
    ]
    external_enum_paths: set[str] = set()
    for prop in structural_only_props:
        enum_names: set[str] = set()
        if prop.enum_ref:
            enum_names.add(prop.enum_ref)
        if prop.list_inner_enum:
            enum_names.add(prop.list_inner_enum)
        if prop.type_ref == "value_object":
            enum_names.update(
                inner.enum_ref
                for branch in _value_object_branches(prop)
                for inner in branch
                if inner.enum_ref
            )
        for enum_name in enum_names:
            if registry is None or enum_name in local_enums:
                continue
            path = _cross_file_enum_path(enum_name, registry)
            if path:
                external_enum_paths.add(path)
    for path in sorted(external_enum_paths):
        enum_name = path.rsplit("::", 1)[-1]
        out.append("#[allow(dead_code)]")
        out.append(
            f"type _StructuralDependency{enum_name} = {path};"
        )
    if external_enum_paths:
        out.append("")

    if doc.shapes or doc.pattern_maps:
        out.append("use std::collections::BTreeMap;")
        out.append("")

    for scalar in doc.scalar_types:
        out.append(
            f"/// Reusable constrained scalar carrier for `{scalar.name}`; "
            "generated validators enforce its lexical grammar."
        )
        out.append(f"pub type {scalar.name} = String;")
        out.append("")

    for map_def in doc.pattern_maps:
        value_type = _rust_type(
            map_def.value,
            local_enums=local_enums,
            registry=registry,
        )
        out.append(
            f"/// Pattern-keyed map carrier for `{map_def.name}`; generated "
            "validators enforce its key and cardinality rules."
        )
        out.append(
            f"pub type {map_def.name} = BTreeMap<String, {value_type}>;"
        )
        out.append("")

    for object_type in doc.object_types:
        out.append(
            f"/// Closed generated property carrier for `{object_type.name}`."
        )
        out.append(
            "#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]"
        )
        out.append("#[serde(deny_unknown_fields)]")
        out.append(f"pub struct {object_type.name} {{")
        used_field_names: set[str] = set()
        for prop in object_type.properties:
            field_name = _rust_unique_field_name(prop.name, used_field_names)
            rust_type = _rust_type(
                prop,
                local_enums=local_enums,
                registry=registry,
            )
            out.append(f"    /// JSON-LD member `{prop.name}`.")
            if prop.optional:
                out.append(
                    f'    #[serde(rename = "{prop.name}", '
                    'skip_serializing_if = "Option::is_none", default)]'
                )
                out.append(f"    pub {field_name}: Option<{rust_type}>,")
            else:
                out.append(f'    #[serde(rename = "{prop.name}")]')
                out.append(f"    pub {field_name}: {rust_type},")
        out.append("}")
        out.append("")

    for s in doc.shapes:
        # The parser diverts `@type` from properties into shape.type_iri, so
        # consult that directly instead of re-scanning properties.
        type_value: Optional[str] = s.type_iri
        used_field_names = {"id", "extra"}
        if type_value is not None:
            used_field_names.add("type_")

        out.append(f"/// Generated JSON-LD carrier for `{s.name}`.")
        out.append("#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]")
        out.append(f"pub struct {s.name} {{")

        # @type field — emit specially with default constructor reference
        if type_value is not None:
            out.append("    /// JSON-LD resource type.")
            out.append(f'    #[serde(rename = "@type", default = "{s.name}::default_type")]')
            out.append("    pub type_: String,")

        # @id field — always optional, always emitted (JSON-LD reserved key)
        out.append("    /// Optional JSON-LD resource identifier.")
        out.append('    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]')
        out.append("    pub id: Option<String>,")

        # Other properties
        for p in s.properties:
            if p.name in ("@type", "@id"):
                continue
            ty = _rust_type(p, local_enums=local_enums, registry=registry)
            field_name = _rust_unique_field_name(p.name, used_field_names)
            out.append(f"    /// JSON-LD property `{p.name}`.")
            if p.optional:
                out.append(
                    f'    #[serde(rename = "{p.name}", skip_serializing_if = "Option::is_none", default)]'
                )
                out.append(f"    pub {field_name}: Option<{ty}>,")
            else:
                out.append(f'    #[serde(rename = "{p.name}")]')
                out.append(f"    pub {field_name}: {ty},")

        # Catch-all for unknown properties (preserves round-trip).
        out.append("    /// Additional JSON-LD properties preserved during round trips.")
        out.append("    #[serde(flatten)]")
        out.append("    pub extra: BTreeMap<String, serde_json::Value>,")
        out.append("}")
        out.append("")

        # Default-type constructor (if @type was fixed in CUE)
        if type_value is not None:
            out.append(f"impl {s.name} {{")
            out.append(f'    fn default_type() -> String {{ "{type_value}".into() }}')
            out.append("}")
            out.append("")
    return "\n".join(out)


_RUST_RESERVED_FIELD_NAMES = frozenset({
    "as", "async", "await", "become", "box", "break", "const", "continue",
    "crate", "do", "dyn", "else", "enum", "extern", "false", "final", "fn",
    "for", "gen", "if", "impl", "in", "let", "loop", "macro", "match",
    "mod", "move", "mut", "override", "priv", "pub", "ref", "return",
    "self", "static", "struct", "super", "trait", "true", "try", "type",
    "typeof", "union", "unsafe", "unsized", "use", "virtual", "where",
    "while", "yield",
})


def _rust_field_clean(name: str) -> str:
    """Generate idiomatic Rust field names from JSON-LD property IRIs.
    Drops the `rkaf:` / `oa:` / `skos:` namespace prefix and snake_cases the rest.
    """
    if ":" in name:
        name = name.split(":", 1)[1]
    out = name.replace("-", "_").replace("@", "")
    field = _to_snake(out)
    return f"{field}_" if field in _RUST_RESERVED_FIELD_NAMES else field


def _rust_unique_field_name(name: str, used: set[str]) -> str:
    """Return a legal field name that is unique within one generated struct.

    Rulespec normally drops the namespace prefix for readable SDK fields.
    JSON-LD `@type` and a property such as `dcterms:type` expose why that cannot
    be the only rule: both clean to `type_`. When a local name collides with a
    reserved carrier field or an earlier property, retain its namespace as the
    disambiguator. A numeric suffix handles the theoretical case where two
    source spellings still normalize to the same identifier.
    """
    candidate = _rust_field_clean(name)
    if candidate in used:
        if ":" in name:
            namespace, local = name.split(":", 1)
            candidate = _to_snake(f"{namespace}_{local}")
        else:
            candidate = _to_snake(name.replace("@", ""))
        if candidate in _RUST_RESERVED_FIELD_NAMES:
            candidate = f"{candidate}_"
        base = candidate
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
    used.add(candidate)
    return candidate


def _pascal_after_colon(v: str) -> str:
    after = v.split(":")[-1]
    parts = re.split(r"[-_]", after)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def _rust_field(name: str) -> str:
    out = name.replace(":", "_").replace("-", "_").replace("@", "")
    return _to_snake(out)


def _to_snake(s: str) -> str:
    s = re.sub(r"([A-Z])", r"_\1", s).lstrip("_").lower()
    return s


def _module_for_cue_package(package: str) -> str:
    """Convert a CUE package / file stem (e.g., `usage-eligibility`) to the
    matching Rust module name (`usage_eligibility`) that `lib.rs` exposes
    under `crate::generated`."""
    return package.replace("-", "_")


def _rust_module_path_for_relpath(relpath: str) -> str:
    """Map a `constraints/`-relative CUE path to its `crate::generated::` path.

    `core/artifact` -> `artifact` (kernel primitives sit at the root of the
    generated tree); `profiles/us-rulemaking/rulemaking` ->
    `profiles::us_rulemaking::rulemaking`, mirroring the sink layout that
    tools/compile_all.sh writes.
    """
    parts = relpath.split("/")
    if parts[0] == "core":
        parts = parts[1:]
    return "::".join(_module_for_cue_package(part) for part in parts)


def _cross_file_enum_path(enum_name: str, registry: dict) -> Optional[str]:
    """Given a registry of {enum_name: EnumDef|EnumUnion}, look up which CUE
    source file defines `enum_name` and return the fully-qualified Rust path.
    The registry's EnumDef stores no source-file hint, so this implementation
    relies on the global scan: the registry is built by parsing each CUE file
    and the EnumDef/EnumUnion's residence is tracked via the parallel
    `_REGISTRY_SOURCES` map below. Returns None if no resolution is possible.
    """
    relpath = _REGISTRY_RELPATHS.get(enum_name)
    if relpath:
        return f"crate::generated::{_rust_module_path_for_relpath(relpath)}::{enum_name}"
    pkg = _REGISTRY_SOURCES.get(enum_name)
    if not pkg:
        return None
    return f"crate::generated::{_module_for_cue_package(pkg)}::{enum_name}"


# Populated by `_scan_global_enum_registry`; maps enum/union name to the CUE
# package (file stem) that defines it. Used to compute fully-qualified Rust
# module paths for cross-file enum references.
_REGISTRY_SOURCES: dict[str, str] = {}

# Same scan, but the `constraints/`-relative path (`core/artifact`,
# `profiles/us-rulemaking/rulemaking`). A cross-SUB-TREE reference — a profile
# shape composing a kernel shape — needs the sub-tree, not just the stem, to
# address the generated Rust module or TypeScript file.
_REGISTRY_RELPATHS: dict[str, str] = {}


def _rust_type(p: PropDef, local_enums: Optional[set] = None,
               registry: Optional[dict] = None) -> str:
    if p.fixed_value is not None:
        return "String"
    if p.type_ref == "value_object":
        # `crate::RdfLiteral<T>` preserves the mutually exclusive typed and
        # language-tagged RDF 1.1 wire branches. A single typed-only source
        # keeps the narrower historical `TypedLiteral<T>` carrier.
        datatype = _value_object_member(p, "@type")
        name = (datatype.enum_ref if datatype else None) or "String"
        if local_enums is not None and name not in local_enums and registry is not None:
            fq = _cross_file_enum_path(name, registry)
            if fq:
                name = fq
        has_language_branch = any(
            _branch_member(branch, "@language") is not None
            for branch in _value_object_branches(p)
        )
        carrier = "RdfLiteral" if has_language_branch else "TypedLiteral"
        return f"crate::{carrier}<{name}>"
    if p.type_ref == "enum":
        name = p.enum_ref or "String"
        if local_enums is not None and name not in local_enums and registry is not None:
            fq = _cross_file_enum_path(name, registry)
            if fq:
                return fq
        return name
    if p.type_ref == "named":
        name = p.named_ref or "serde_json::Value"
        if (
            local_enums is not None
            and name not in local_enums
            and registry is not None
        ):
            fq = _cross_file_enum_path(name, registry)
            if fq:
                return fq
        return name
    if p.type_ref == "list":
        # Strict authoring lists stay Vec; other one-member JSON-LD relations
        # retain the scalar-or-array shorthand.
        carrier = "Vec" if not p.list_allow_scalar else "crate::OneOrMany"
        if p.list_inner_enum:
            inner = p.list_inner_enum
            if local_enums is not None and inner not in local_enums and registry is not None:
                fq = _cross_file_enum_path(inner, registry)
                if fq:
                    inner = fq
            return f"{carrier}<{inner}>"
        if p.list_inner_named:
            inner = p.list_inner_named
            if (
                local_enums is not None
                and inner not in local_enums
                and registry is not None
            ):
                fq = _cross_file_enum_path(inner, registry)
                if fq:
                    inner = fq
            return f"{carrier}<{inner}>"
        if p.list_of_string:
            return f"{carrier}<String>"
        # Bare `list.MinItems(N)` with no item-type constraint — any JSON value.
        return f"{carrier}<serde_json::Value>"
    if p.type_ref == "int":
        return "i64"
    if p.type_ref == "float":
        return "f64"
    if p.type_ref == "bool":
        return "bool"
    return "String"


# ---- TypeScript target ---------------------------------------------------

def _ts_import_specifier(enum_name: str, own_relpath: Optional[str]) -> Optional[str]:
    """Relative ES-module specifier for the file that declares `enum_name`.

    Compiled TypeScript mirrors the `constraints/` tree under
    `compiled/typescript/`, so a same-directory reference stays `./artifact`
    while a profile importing a kernel enum becomes `../../core/artifact`.
    Emitting a bare `./artifact` from a profile file would point at a
    non-existent module.
    """
    target = _REGISTRY_RELPATHS.get(enum_name)
    if target is None:
        source = _REGISTRY_SOURCES.get(enum_name)
        return f"./{source}" if source else None
    if own_relpath is None:
        return f"./{target.rsplit('/', 1)[-1]}"
    own_dir = own_relpath.rsplit("/", 1)[0] if "/" in own_relpath else ""
    target_dir = target.rsplit("/", 1)[0] if "/" in target else ""
    target_stem = target.rsplit("/", 1)[-1]
    if own_dir == target_dir:
        return f"./{target_stem}"
    ups = "../" * len(own_dir.split("/")) if own_dir else ""
    prefix = f"{target_dir}/" if target_dir else ""
    return f"{ups or './'}{prefix}{target_stem}"


def target_typescript(
    doc: ConstraintDoc,
    registry: Optional[dict] = None,
    source_file: Optional[Path] = None,
) -> str:
    _prepare_named_references(doc, registry, source_file)
    out: list[str] = [
        "// AUTO-GENERATED by tools/constraints_compile.py",
        f"// Source: {_source_header(doc, source_file)}",
        "// DO NOT EDIT.",
        "",
    ]

    def _conditional_scalar_values(prop: PropDef) -> list[str]:
        if prop.inline_enum_values:
            return list(prop.inline_enum_values)
        if prop.enum_union_refs:
            values: list[str] = []
            for ref in prop.enum_union_refs:
                values.extend(
                    _resolve_enum_values(
                        ref, doc, registry, ("<inline union>",)
                    )
                )
            return values
        if prop.type_ref == "enum" and prop.enum_ref:
            return _resolve_enum_values(prop.enum_ref, doc, registry)
        return []

    local_enums = {e.name for e in doc.enums} | {
        union.name for union in doc.enum_unions
    }
    local_carriers = (
        {definition.name for definition in doc.scalar_types}
        | {definition.name for definition in doc.pattern_maps}
        | {definition.name for definition in doc.object_types}
    )
    def _referenced_enums(prop: PropDef) -> tuple[Optional[str], ...]:
        """Enum names a property names directly or through a value object."""
        if prop.type_ref == "value_object":
            return tuple(
                inner.enum_ref
                for branch in _value_object_branches(prop)
                for inner in branch
            )
        return (prop.enum_ref, prop.list_inner_enum)

    referenced_props = [
        prop
        for shape in doc.shapes
        for prop in (
            list(shape.properties)
            + [
                required
                for conditional in shape.conditionals
                for required in conditional.then_require
            ]
            + [
                branch_prop
                for disjunction in shape.disjunctions
                for branch in disjunction
                for branch_prop in branch.properties
            ]
        )
    ]
    external_enums = sorted(
        {
            enum_name
            for prop in referenced_props
            for enum_name in _referenced_enums(prop)
            if enum_name
            and enum_name not in local_enums
            and registry is not None
            and enum_name in registry
        }
    )
    external_carriers = sorted(
        {
            carrier_name
            for prop in referenced_props
            for carrier_name in (prop.named_ref, prop.list_inner_named)
            if carrier_name
            and carrier_name not in local_carriers
            and registry is not None
            and isinstance(
                registry.get(carrier_name),
                (ScalarTypeDef, PatternMapDef, ObjectTypeDef),
            )
        }
    )
    own_relpath = _source_relpath(source_file) if source_file is not None else None
    for enum_name in external_enums:
        specifier = _ts_import_specifier(enum_name, own_relpath)
        if specifier:
            out.append(
                f'import type {{ {enum_name} }} from "{specifier}";'
            )
    for carrier_name in external_carriers:
        specifier = _ts_import_specifier(carrier_name, own_relpath)
        if specifier:
            out.append(
                f'import {{ type {carrier_name}, validate{carrier_name} }} '
                f'from "{specifier}";'
            )
    if external_enums or external_carriers:
        out.append("")
    for e in doc.enums:
        lits = " | ".join(f'"{v}"' for v in e.values)
        out.append(f"export type {e.name} = {lits};")
        out.append("")
    for u in doc.enum_unions:
        lits = " | ".join(
            f'"{v}"' for v in _resolve_enum_values(u.name, doc, registry)
        )
        out.append(f"export type {u.name} = {lits};")
        out.append("")
    for scalar in doc.scalar_types:
        pattern = json.dumps(scalar.value.pattern)
        out.append(f"export type {scalar.name} = string;")
        out.append("")
        out.append(
            f"export function validate{scalar.name}(v: unknown): string[] {{"
        )
        out.append("  const errs: string[] = [];")
        out.append(
            f'  if (typeof v !== "string") return ["{scalar.name}: must be a string"];'
        )
        if scalar.value.pattern:
            out.append(
                f"  if (!new RegExp({pattern}).test(v)) "
                f'errs.push("{scalar.name}: pattern mismatch");'
            )
        if scalar.value.forbidden_pattern:
            forbidden = json.dumps(scalar.value.forbidden_pattern)
            out.append(
                f"  if (new RegExp({forbidden}).test(v)) "
                f'errs.push("{scalar.name}: forbidden pattern match");'
            )
        out.append("  return errs;")
        out.append("}")
        out.append("")
    for map_def in doc.pattern_maps:
        value_type = (
            "string | string[]"
            if map_def.value.type_ref == "list"
            else "string"
        )
        key_pattern = json.dumps(map_def.key.pattern)
        out.append(
            f"export type {map_def.name} = Record<string, {value_type}>;"
        )
        out.append("")
        out.append(
            f"export function validate{map_def.name}(v: unknown): string[] {{"
        )
        out.append("  const errs: string[] = [];")
        out.append(
            '  if (typeof v !== "object" || v === null || Array.isArray(v)) '
            f'return ["{map_def.name}: must be a language map"];'
        )
        out.append("  const entries = Object.entries(v);")
        out.append(
            f'  if (entries.length < {map_def.min_properties}) '
            f'errs.push("{map_def.name}: < {map_def.min_properties} entries");'
        )
        out.append(
            f"  if (entries.some(([key]) => !new RegExp({key_pattern}).test(key))) "
            f'errs.push("{map_def.name}: malformed language tag");'
        )
        if map_def.key.forbidden_pattern:
            forbidden = json.dumps(map_def.key.forbidden_pattern)
            out.append(
                f"  if (entries.some(([key]) => new RegExp({forbidden}).test(key))) "
                f'errs.push("{map_def.name}: forbidden language key");'
            )
        if map_def.value.type_ref == "list":
            out.append(
                "  if (entries.some(([, value]) => "
                'typeof value !== "string" && (!Array.isArray(value) || '
                f"value.length < {map_def.value.list_min_items} || "
                'value.some((item) => typeof item !== "string")))) '
                f'errs.push("{map_def.name}: values must be one-or-more strings");'
            )
        else:
            out.append(
                "  if (entries.some(([, value]) => typeof value !== "
                f'"string")) errs.push("{map_def.name}: values must be strings");'
            )
        out.append("  return errs;")
        out.append("}")
        out.append("")
    for object_type in doc.object_types:
        out.append(f"export interface {object_type.name} {{")
        for prop in object_type.properties:
            optional = "?" if prop.optional else ""
            out.append(
                f'  "{prop.name}"{optional}: {_ts_type(prop)};'
            )
        out.append("}")
        out.append("")
        out.append(
            f"export function validate{object_type.name}(v: unknown): string[] {{"
        )
        out.append("  const errs: string[] = [];")
        out.append(
            '  if (typeof v !== "object" || v === null || Array.isArray(v)) '
            f'return ["{object_type.name}: must be an object"];'
        )
        out.append("  const record = v as Record<string, unknown>;")
        allowed = json.dumps([prop.name for prop in object_type.properties])
        out.append(
            f"  if (Object.keys(record).some((key) => !{allowed}.includes(key))) "
            f'errs.push("{object_type.name}: member outside the closed object");'
        )
        for prop in object_type.properties:
            if not prop.optional:
                out.append(
                    f'  if (record["{prop.name}"] === undefined) '
                    f'errs.push("{object_type.name}: {prop.name} is required");'
                )
            if prop.type_ref == "string":
                out.append(
                    f'  if (record["{prop.name}"] !== undefined && '
                    f'typeof record["{prop.name}"] !== "string") '
                    f'errs.push("{object_type.name}: {prop.name} must be a string");'
                )
            if prop.pattern:
                pattern = json.dumps(prop.pattern)
                out.append(
                    f'  if (typeof record["{prop.name}"] === "string" && '
                    f'!new RegExp({pattern}).test(record["{prop.name}"] as string)) '
                    f'errs.push("{object_type.name}: {prop.name} pattern mismatch");'
                )
            if prop.forbidden_pattern:
                pattern = json.dumps(prop.forbidden_pattern)
                out.append(
                    f'  if (typeof record["{prop.name}"] === "string" && '
                    f'new RegExp({pattern}).test(record["{prop.name}"] as string)) '
                    f'errs.push("{object_type.name}: {prop.name} forbidden pattern match");'
                )
        out.append("  return errs;")
        out.append("}")
        out.append("")
    has_date = any(
        prop.string_format == "date"
        for shape in doc.shapes
        for prop in (
            list(shape.properties)
            + [
                required
                for conditional in shape.conditionals
                for required in conditional.then_require
            ]
        )
    )
    if has_date:
        out.extend(
            [
                "function isRkafDate(value: unknown): value is string {",
                '  if (typeof value !== "string" || !/^\\d{4}-\\d{2}-\\d{2}$/.test(value)) return false;',
                '  const parsed = new Date(`${value}T00:00:00.000Z`);',
                "  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;",
                "}",
                "",
            ]
        )
    for s in doc.shapes:
        out.append(f"export interface {s.name} {{")
        for p in s.properties:
            ts = _ts_type(p)
            opt = "?" if p.optional else ""
            out.append(f'  "{p.name}"{opt}: {ts};')
        out.append("}")
        out.append("")
        out.append(f"export function validate{s.name}(v: {s.name}): string[] {{")
        out.append("  const errs: string[] = [];")
        if s.conditionals:
            out.append(
                "  const record = v as unknown as Record<string, unknown>;"
            )
        for p in s.properties:
            if p.type_ref == "named" and p.named_ref:
                out.append(
                    f'  if (v["{p.name}"] !== undefined) '
                    f'errs.push(...validate{p.named_ref}(v["{p.name}"]));'
                )
            if p.type_ref == "list" and p.list_inner_named:
                if not p.list_allow_scalar:
                    out.append(
                        f'  if (v["{p.name}"] !== undefined && '
                        f'!Array.isArray(v["{p.name}"])) '
                        f'errs.push("{p.name}: must be an array");'
                    )
                out.append(
                    f'  if (Array.isArray(v["{p.name}"]) && '
                    f'v["{p.name}"].length < {p.list_min_items}) '
                    f'errs.push("{p.name}: < {p.list_min_items} items");'
                )
                out.append(
                    f'  if (v["{p.name}"] !== undefined) '
                    f'errs.push(...([] as unknown[]).concat(v["{p.name}"] as '
                    f'unknown[]).flatMap((value) => '
                    f"validate{p.list_inner_named}(value)));"
                )
            if p.type_ref == "list" and p.list_max_items is not None:
                out.append(
                    f'  if (Array.isArray(v["{p.name}"]) && '
                    f'v["{p.name}"].length > {p.list_max_items}) '
                    f'errs.push("{p.name}: > {p.list_max_items} items");'
                )
            if p.type_ref == "list" and p.list_unique_items:
                out.append(
                    f'  if (Array.isArray(v["{p.name}"]) && '
                    f'new Set(v["{p.name}"].map((item) => '
                    f'JSON.stringify(item))).size !== v["{p.name}"].length) '
                    f'errs.push("{p.name}: duplicate items");'
                )
            if (
                p.type_ref == "list"
                and not p.list_allow_scalar
                and not p.list_inner_named
            ):
                out.append(
                    f'  if (v["{p.name}"] !== undefined && '
                    f'!Array.isArray(v["{p.name}"])) '
                    f'errs.push("{p.name}: must be an array");'
                )
            if (
                p.type_ref == "list"
                and p.list_min_items > 0
                and not p.optional
                and not p.list_inner_named
            ):
                out.append(f'  if (!Array.isArray(v["{p.name}"]) || v["{p.name}"].length < {p.list_min_items}) errs.push("{p.name}: < {p.list_min_items} items");')
            if p.pattern:
                pattern = json.dumps(p.pattern)
                if p.type_ref == "list":
                    out.append(
                        f'  if (v["{p.name}"] !== undefined && '
                        f'!([] as string[]).concat(v["{p.name}"] as string[]).every'
                        f'((value) => new RegExp({pattern}).test(value))) '
                        f'errs.push("{p.name}: pattern mismatch");'
                    )
                else:
                    out.append(
                        f'  if (v["{p.name}"] !== undefined && '
                        f'!new RegExp({pattern}).test(v["{p.name}"] as string)) '
                        f'errs.push("{p.name}: pattern mismatch");'
                    )
            if p.forbidden_pattern:
                pattern = json.dumps(p.forbidden_pattern)
                if p.type_ref == "list":
                    out.append(
                        f'  if (v["{p.name}"] !== undefined && '
                        f'!([] as string[]).concat(v["{p.name}"] as string[]).every'
                        f'((value) => !new RegExp({pattern}).test(value))) '
                        f'errs.push("{p.name}: forbidden pattern match");'
                    )
                else:
                    out.append(
                        f'  if (v["{p.name}"] !== undefined && '
                        f'new RegExp({pattern}).test(v["{p.name}"] as string)) '
                        f'errs.push("{p.name}: forbidden pattern match");'
                    )
            if p.string_format == "date":
                out.append(
                    f'  if (v["{p.name}"] !== undefined && '
                    f'!isRkafDate(v["{p.name}"])) '
                    f'errs.push("{p.name}: invalid date");'
                )
            if p.type_ref == "value_object":
                # Carry both RDF 1.1 value-object branches faithfully.
                datatype = _value_object_member(p, "@type")
                language = _value_object_member(p, "@language")
                values = (
                    _resolve_enum_values(datatype.enum_ref, doc, registry)
                    if datatype and datatype.enum_ref
                    else []
                )
                literal = f'(v["{p.name}"] as Record<string, unknown> | undefined)'
                out.append(
                    f"  if ({literal} !== undefined && "
                    f'typeof {literal}!["@value"] !== "string") '
                    f'errs.push("{p.name}: @value must be the lexical form");'
                )
                out.append(
                    f"  if ({literal} !== undefined && "
                    f'(({literal}!["@type"] !== undefined) === '
                    f'({literal}!["@language"] !== undefined))) '
                    f'errs.push("{p.name}: exactly one of @type or @language is required");'
                )
                if values:
                    allowed = json.dumps(values)
                    out.append(
                        f"  if ({literal} !== undefined && "
                        f'{literal}!["@type"] !== undefined && '
                        f'!{allowed}.includes({literal}!["@type"] as string)) '
                        f'errs.push("{p.name}: @type outside the closed datatype set");'
                    )
                if language and language.pattern:
                    pattern = json.dumps(language.pattern)
                    out.append(
                        f"  if ({literal} !== undefined && "
                        f'{literal}!["@language"] !== undefined && '
                        f'(typeof {literal}!["@language"] !== "string" || '
                        f'!new RegExp({pattern}).test({literal}!["@language"] as string))) '
                        f'errs.push("{p.name}: @language must be a BCP 47 language tag");'
                    )
                declared = json.dumps(sorted(VALUE_OBJECT_MEMBERS))
                out.append(
                    f"  if ({literal} !== undefined && "
                    f"Object.keys({literal}!).some((member) => "
                    f"!{declared}.includes(member))) "
                    f'errs.push("{p.name}: member outside the closed value object");'
                )
        for index, conditional in enumerate(s.conditionals):
            when_name = f"condition{index + 1}"
            when_value = f'record["{conditional.when_property}"]'
            if conditional.when_equals is None:
                expression = f"{when_value} !== undefined"
            else:
                expected = json.dumps(conditional.when_equals)
                expression = (
                    f"{when_value} === {expected} || "
                    f"(Array.isArray({when_value}) && "
                    f"{when_value}.includes({expected}))"
                )
                if conditional.when_not_equals:
                    expression = f"!({expression})"
            out.append(f"  const {when_name} = {expression};")
            for requirement in conditional.then_require:
                required_value = f'record["{requirement.name}"]'
                out.append(
                    f"  if ({when_name} && {required_value} === undefined) "
                    f'errs.push("{requirement.name}: required by '
                    f'{conditional.when_property}");'
                )
                if (
                    requirement.type_ref == "list"
                    and requirement.list_min_items > 0
                ):
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"(!Array.isArray({required_value}) || "
                        f"{required_value}.length < "
                        f"{requirement.list_min_items})) "
                        f'errs.push("{requirement.name}: < '
                        f'{requirement.list_min_items} items");'
                    )
                if (
                    requirement.type_ref == "list"
                    and requirement.list_max_items is not None
                ):
                    out.append(
                        f"  if ({when_name} && Array.isArray({required_value}) && "
                        f"{required_value}.length > "
                        f"{requirement.list_max_items}) "
                        f'errs.push("{requirement.name}: > '
                        f'{requirement.list_max_items} items");'
                    )
                if requirement.type_ref == "value_object":
                    literal = (
                        f"({required_value} as Record<string, unknown> | "
                        "undefined)"
                    )
                    language = _value_object_member(
                        requirement, "@language"
                    )
                    out.append(
                        f"  if ({when_name} && ({literal} === undefined || "
                        f'typeof {literal}!["@value"] !== "string" || '
                        f'typeof {literal}!["@language"] !== "string" || '
                        f'{literal}!["@type"] !== undefined)) '
                        f'errs.push("{requirement.name}: must be a '
                        'language-tagged value");'
                    )
                    if language and language.pattern:
                        pattern = json.dumps(language.pattern)
                        out.append(
                            f"  if ({when_name} && {literal} !== undefined && "
                            f'typeof {literal}!["@language"] === "string" && '
                            f'!new RegExp({pattern}).test('
                            f'{literal}!["@language"] as string)) '
                            f'errs.push("{requirement.name}: malformed '
                            'language tag");'
                        )
                if requirement.pattern:
                    pattern = json.dumps(requirement.pattern)
                    if requirement.type_ref == "list":
                        out.append(
                            f"  if ({when_name} && {required_value} !== undefined && "
                            f"(!Array.isArray({required_value}) || "
                            f"!{required_value}.every((value) => "
                            f'typeof value === "string" && '
                            f"new RegExp({pattern}).test(value)))) "
                            f'errs.push("{requirement.name}: pattern mismatch");'
                        )
                    else:
                        out.append(
                            f"  if ({when_name} && {required_value} !== undefined && "
                            f"(typeof {required_value} !== \"string\" || "
                            f"!new RegExp({pattern}).test({required_value}))) "
                            f'errs.push("{requirement.name}: pattern mismatch");'
                        )
                if requirement.fixed_value is not None:
                    expected = json.dumps(requirement.fixed_value)
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"{required_value} !== {expected}) "
                        f'errs.push("{requirement.name}: must equal '
                        f'{requirement.fixed_value}");'
                    )
                elif _conditional_scalar_values(requirement):
                    allowed = json.dumps(
                        _conditional_scalar_values(requirement)
                    )
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"!{allowed}.includes({required_value} as string)) "
                        f'errs.push("{requirement.name}: outside closed set");'
                    )
                elif (
                    requirement.type_ref == "list"
                    and requirement.list_inner_enum
                ):
                    allowed = json.dumps(
                        _resolve_enum_values(
                            requirement.list_inner_enum,
                            doc,
                            registry,
                        )
                    )
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"(!Array.isArray({required_value}) || "
                        f"!{required_value}.every((value) => "
                        f"{allowed}.includes(value as string)))) "
                        f'errs.push("{requirement.name}: outside closed set");'
                    )
                if requirement.string_format == "date":
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"!isRkafDate({required_value})) "
                        f'errs.push("{requirement.name}: invalid date");'
                    )
            for forbidden_name in conditional.then_forbid:
                forbidden_value = f'record["{forbidden_name}"]'
                out.append(
                    f"  if ({when_name} && {forbidden_value} !== undefined) "
                    f'errs.push("{forbidden_name}: forbidden by '
                    f'{conditional.when_property}");'
                )
        for order in s.orders:
            out.append(
                f'  if (v["{order.lower_property}"] > v["{order.upper_property}"]) '
                f'errs.push("{order.lower_property}: must be on or before '
                f'{order.upper_property}");'
            )
        for constraint in s.not_equals:
            out.append(
                f'  if (v["{constraint.left_property}"] !== undefined && '
                f'v["{constraint.right_property}"] !== undefined && '
                f'v["{constraint.left_property}"] === '
                f'v["{constraint.right_property}"]) '
                f'errs.push("{constraint.left_property}: must differ from '
                f'{constraint.right_property}");'
            )
        out.append("  return errs;")
        out.append("}")
        out.append("")
    return "\n".join(out)


def _ts_type(p: PropDef) -> str:
    if p.fixed_value is not None:
        return f'"{p.fixed_value}"'
    if p.type_ref == "value_object":
        alternatives: list[str] = []
        for branch in _value_object_branches(p):
            declared = [inner.name for inner in branch]
            members = [
                f'"{inner.name}"{"?" if inner.optional else ""}: {_ts_type(inner)}'
                for inner in branch
            ]
            members.extend(
                f'"{reserved}"?: never'
                for reserved in sorted(VALUE_OBJECT_MEMBERS - set(declared))
            )
            alternatives.append("{ " + "; ".join(members) + " }")
        return " | ".join(alternatives)
    if p.type_ref == "enum":
        return p.enum_ref or "string"
    if p.type_ref == "named":
        return p.named_ref or "unknown"
    if p.type_ref == "list":
        if p.list_inner_named:
            return (
                f"{p.list_inner_named}[]"
                if not p.list_allow_scalar
                else f"{p.list_inner_named} | {p.list_inner_named}[]"
            )
        inner = p.list_inner_enum or "string"
        return f"{inner}[]"
    if p.type_ref == "int" or p.type_ref == "float":
        return "number"
    if p.type_ref == "bool":
        return "boolean"
    return "string"


# ---- SHACL target (Pattern C only) ---------------------------------------

def _pattern_map_definition(
    doc: ConstraintDoc, name: Optional[str], registry: Optional[dict] = None
) -> Optional[PatternMapDef]:
    local = next(
        (definition for definition in doc.pattern_maps if definition.name == name),
        None,
    )
    if local is not None:
        return local
    external = registry.get(name) if registry and name else None
    return external if isinstance(external, PatternMapDef) else None


def _object_type_definition(
    doc: ConstraintDoc, name: Optional[str], registry: Optional[dict] = None
) -> Optional[ObjectTypeDef]:
    local = next(
        (definition for definition in doc.object_types if definition.name == name),
        None,
    )
    if local is not None:
        return local
    external = registry.get(name) if registry and name else None
    return external if isinstance(external, ObjectTypeDef) else None


def target_shacl(
    doc: ConstraintDoc,
    reference_classes: Optional[dict[str, str]] = None,
    source_file: Optional[Path] = None,
    registry: Optional[dict] = None,
) -> str:
    """Emit SHACL for every Pattern-C shape in `doc`.

    Like `target_json_schema`, `target_rust` and `target_typescript`, this
    emitter takes the cross-file enum `registry`, so a property whose enum is
    DEFINED IN ANOTHER CUE FILE still emits its `sh:in` closure. A profile
    overlay composing a kernel shape is exactly that case:
    `compiled/shacl/profiles/us-rulemaking/us-regulatory-artifact.ttl` closes
    `rkaf:artifactIdentifierScheme` over the kernel's scheme values even though
    the kernel declares them, which matters because
    `tools/constraints_parity.py` validates the us-regulatory-artifact rows
    against that overlay ALONE.

    An IRI-valued `sh:in` list only matches data whose values reach RDF as
    IRIs, so every enum-valued term MUST carry an `@type: @id`/`@vocab`
    coercion in `context/rkaf-context.jsonld`. Adding a closure here without
    the matching coercion turns a passing document into a violation whose
    message names the value that is already in the list.
    """
    _prepare_named_references(doc, registry, source_file)
    out: list[str] = [
        "# AUTO-GENERATED by tools/constraints_compile.py (target=shacl, Pattern C only).",
        f"# Source: {_source_header(doc, source_file)}",
        "# DO NOT EDIT.",
        "",
        "@prefix sh:   <http://www.w3.org/ns/shacl#> .",
        "@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix oa:   <http://www.w3.org/ns/oa#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix dcat: <http://www.w3.org/ns/dcat#> .",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix dpv:  <https://w3id.org/dpv#> .",
        "@prefix rkaf: <https://rulespec.org/ns/v1#> .",
        "",
    ]
    # Expand enum unions: a union {A,B,C} contributes the flattened values
    # of its referenced enums to a single resolved value list. Enums declared
    # in another CUE file resolve through the registry; a name that resolves
    # nowhere is a compile error, never a silently open property.
    def resolve_enum(name: str) -> list[str]:
        if not name:
            return []
        return _resolve_enum_values(name, doc, registry)

    def resolve_property_values(prop: PropDef) -> list[str]:
        """Return every closed scalar value carried by one property.

        A CUE field may close its values by naming an enum, by spelling an
        inline literal union, or by assembling named enums inline. JSON Schema
        already projects all three forms; SHACL must use the same resolution
        path or a conditional such as a usage ceiling becomes presence-only.
        """
        if prop.inline_enum_values:
            return list(prop.inline_enum_values)
        if prop.enum_union_refs:
            values: list[str] = []
            for ref in prop.enum_union_refs:
                values.extend(
                    _resolve_enum_values(
                        ref, doc, registry, ("<inline union>",)
                    )
                )
            return values
        if prop.type_ref == "enum" and prop.enum_ref:
            return resolve_enum(prop.enum_ref)
        return []

    for s in doc.shapes:
        if not s.type_iri:
            continue
        type_iri = s.type_iri
        out.append(f"rkaf:{s.name}Shape a sh:NodeShape ;")
        out.append(f"  sh:targetClass {type_iri} ;")
        for p in s.properties:
            named_map = _pattern_map_definition(
                doc, p.named_ref or p.list_inner_named, registry
            )
            named_object = _object_type_definition(
                doc, p.named_ref or p.list_inner_named, registry
            )
            line = f"  sh:property [ sh:path {p.name} ;"
            # Consolidate min-cardinality: max(required ? 1 : 0, list min items).
            # Emitting both sh:minCount predicates yields a malformed SHACL shape
            # (pyshacl 0.31+ refuses load with `MinCountConstraintComponent must
            # have at most one sh:minCount`).
            min_count = 0
            if not p.optional:
                min_count = max(1, p.list_min_items)
            if min_count > 0:
                line += f" sh:minCount {min_count} ;"
            # A scalar CUE field is exactly-one when required and at-most-one
            # when optional. RDF permits repeated predicates, so SHACL must
            # carry the upper bound explicitly.
            if p.type_ref != "list" and named_map is None:
                line += " sh:maxCount 1 ;"
            if p.type_ref == "list" and p.list_max_items is not None:
                line += f" sh:maxCount {p.list_max_items} ;"
            scalar_values = resolve_property_values(p)
            if scalar_values:
                values = " ".join(scalar_values)
                line += f" sh:in ( {values} ) ;"
            if p.type_ref == "list" and p.list_inner_enum:
                values = " ".join(resolve_enum(p.list_inner_enum))
                if values:
                    line += f" sh:in ( {values} ) ;"
            if p.type_ref == "value_object":
                # JSON-LD value objects expand to one RDF literal. Close the
                # RDF branch over the typed datatype set plus rdf:langString
                # when the CUE source declares a language-tagged branch.
                line += " sh:nodeKind sh:Literal ;"
                datatype = _value_object_member(p, "@type")
                values_list = (
                    resolve_enum(datatype.enum_ref)
                    if datatype and datatype.enum_ref
                    else []
                )
                alternatives_list = [
                        f"[ sh:datatype {value} ]" for value in values_list
                ]
                if any(
                    _branch_member(branch, "@language") is not None
                    for branch in _value_object_branches(p)
                ):
                    alternatives_list.append("[ sh:datatype rdf:langString ]")
                if alternatives_list:
                    alternatives = " ".join(alternatives_list)
                    line += f" sh:or ( {alternatives} ) ;"
            if named_map is not None:
                # A JSON-LD language map expands to one rdf:langString literal
                # per value. The wire keys no longer exist in RDF; datatype
                # validation proves every expanded value remains tagged, and
                # `sh:uniqueLang` carries the one-preferred-label-per-language
                # rule for a single-valued map.
                line += " sh:nodeKind sh:Literal ;"
                line += " sh:datatype rdf:langString ;"
                if named_map.value.type_ref == "string":
                    line += " sh:uniqueLang true ;"
            if named_object is not None:
                # A named JSON-LD typed-literal object expands to the literal
                # itself. RDF guarantees datatype identifiers are IRIs. Exclude
                # the language-tagged branch because this carrier requires
                # `@type`, not `@language`.
                line += " sh:nodeKind sh:Literal ;"
                line += " sh:not [ sh:datatype rdf:langString ; ] ;"
            if p.pattern:
                line += f" sh:pattern {json.dumps(p.pattern)} ;"
            if p.forbidden_pattern:
                line += (
                    " sh:not [ sh:pattern "
                    f"{json.dumps(p.forbidden_pattern)} ; ] ;"
                )
            if p.string_format == "date":
                line += " sh:datatype xsd:date ;"
            if reference_classes and (reference_class := reference_classes.get(p.name)):
                line += f" sh:class {reference_class} ;"
            line += " ] ;"
            out.append(line)
        # Conditional branches → Pattern C (sh:or with sh:not)
        for c in s.conditionals:
            out.append("  sh:or (")
            if c.when_equals is None:
                out.append("    [ sh:not [ sh:property [")
                out.append(f"        sh:path {c.when_property} ; sh:minCount 1")
                out.append("      ] ] ]")
            elif c.when_not_equals:
                out.append("    [ sh:property [")
                out.append(
                    f"        sh:path {c.when_property} ; "
                    f"sh:hasValue {c.when_equals}"
                )
                out.append("      ] ]")
            else:
                out.append("    [ sh:not [ sh:property [")
                out.append(
                    f"        sh:path {c.when_property} ; sh:hasValue {c.when_equals}"
                )
                out.append("      ] ] ]")
            if c.then_require or c.then_forbid:
                # EVERY requirement, not just the first. A guard that emitted
                # `then_require[0]` and dropped the rest is the silent-pass
                # failure `constraints/adversarial/conditional-silent-pass.cue`
                # is about, one layer down: the shape file still reads as a
                # correct conditional while enforcing a strict subset of what
                # the source declares. Each requirement is its own
                # `sh:property` inside the same branch node, so the branch
                # holds only when all of them hold.
                requirements: list[str] = []
                for requirement in c.then_require:
                    min_count = max(1, requirement.list_min_items)
                    part = (
                        f"sh:property [ sh:path {requirement.name} ; "
                        f"sh:minCount {min_count} ;"
                    )
                    # Mirror the unconditional property loop above: a scalar
                    # CUE field is at-most-one whether it is unconditionally
                    # required or required only inside a conditional branch.
                    # Omitting this here (as the compiler did until this fix)
                    # left every conditionally-required scalar field capped
                    # only at the JSON Schema layer — a pure-RDF graph could
                    # carry two values and still satisfy sh:minCount 1, which
                    # is exactly the machine-adjudication independence-pair
                    # bypass a reviewer caught for rkaf:sealedResponseArtifact
                    # (two values, one shared and one unique, satisfy both
                    # "has a value" and "the pair is distinct on SOME value").
                    named_map = _pattern_map_definition(
                        doc,
                        requirement.named_ref or requirement.list_inner_named,
                        registry,
                    )
                    if requirement.type_ref != "list" and named_map is None:
                        part += " sh:maxCount 1 ;"
                    if requirement.list_max_items is not None:
                        part += f" sh:maxCount {requirement.list_max_items} ;"
                    if requirement.fixed_value is not None:
                        part += f" sh:hasValue {requirement.fixed_value} ;"
                    scalar_values = resolve_property_values(requirement)
                    if scalar_values:
                        values = " ".join(scalar_values)
                        part += f" sh:in ( {values} ) ;"
                    if (
                        requirement.type_ref == "list"
                        and requirement.list_inner_enum
                    ):
                        values = " ".join(
                            resolve_enum(requirement.list_inner_enum)
                        )
                        part += f" sh:in ( {values} ) ;"
                    if requirement.type_ref == "value_object":
                        part += " sh:nodeKind sh:Literal ;"
                        has_language = any(
                            _branch_member(branch, "@language") is not None
                            for branch in _value_object_branches(requirement)
                        )
                        has_datatype = any(
                            _branch_member(branch, "@type") is not None
                            for branch in _value_object_branches(requirement)
                        )
                        if has_language and not has_datatype:
                            part += " sh:datatype rdf:langString ;"
                    if requirement.pattern:
                        part += f" sh:pattern {json.dumps(requirement.pattern)} ;"
                    if requirement.string_format == "date":
                        part += " sh:datatype xsd:date ;"
                    part += " ]"
                    requirements.append(part)
                requirements.extend(
                    f"sh:property [ sh:path {name} ; sh:maxCount 0 ; ]"
                    for name in c.then_forbid
                )
                out.append("    [ " + " ; ".join(requirements) + " ]")
            else:
                out.append("    [ sh:property [ sh:path rkaf:_unsatisfiable ; sh:minCount 1 ] ]")
            out.append("  ) ;")
        for order in s.orders:
            out.append(
                f"  sh:property [ sh:path {order.lower_property} ; "
                f"sh:lessThanOrEquals {order.upper_property} ; ] ;"
            )
        for constraint in s.not_equals:
            out.append("  sh:or (")
            out.append("    [ sh:not [ sh:property [")
            out.append(
                f"        sh:path {constraint.right_property} ; sh:minCount 1"
            )
            out.append("      ] ] ]")
            out.append("    [ sh:not [ sh:property [")
            out.append(
                f"        sh:path {constraint.left_property} ; "
                f"sh:equals {constraint.right_property}"
            )
            out.append("      ] ] ]")
            out.append("  ) ;")
        # Disjunctions → Pattern C
        for disj in s.disjunctions:
            out.append("  sh:or (")
            for br in disj:
                if br.properties:
                    bp = br.properties[0]
                    out.append(f"    [ sh:property [ sh:path {bp.name} ; sh:minCount 1 ] ]")
            out.append("  ) ;")
        out.append("  .")
        out.append("")
    return "\n".join(out)


# ---- Rego target ---------------------------------------------------------

def _rego_symbol(name: str) -> str:
    """CUE definition name → Rego snake_case value-set symbol."""
    return re.sub(r"([A-Z])", r"_\1", name).lstrip("_").lower()


def target_rego(
    doc: ConstraintDoc,
    registry: Optional[dict] = None,
    source_file: Optional[Path] = None,
) -> str:
    _prepare_named_references(doc, registry, source_file)
    out: list[str] = [
        "# AUTO-GENERATED by tools/constraints_compile.py (target=rego).",
        f"# Source: {_source_header(doc, source_file)}",
        f"package rkaf.{doc.package.replace('-', '_')}",
        "",
    ]
    for e in doc.enums:
        vals = ", ".join(f'"{v}"' for v in e.values)
        out.append(f"{_rego_symbol(e.name)}_values := [{vals}]")
    # A union names the closed WHOLE-contract set, assembled from parts that
    # may live in other files. Emitting only `doc.enums` would ship a Rego
    # value set narrower than the CUE — the same quiet weakening
    # `_resolve_enum_values` exists to prevent — so unions resolve through the
    # registry exactly as they do for TypeScript and JSON Schema.
    for u in doc.enum_unions:
        vals = ", ".join(
            f'"{v}"' for v in _resolve_enum_values(u.name, doc, registry)
        )
        out.append(f"{_rego_symbol(u.name)}_values := [{vals}]")
    carrier_metadata: dict[str, dict] = {}
    for scalar in doc.scalar_types:
        carrier_metadata[scalar.name] = {
            "kind": "constrained_scalar",
            "pattern": scalar.value.pattern,
            "forbidden_pattern": scalar.value.forbidden_pattern,
        }
    for map_def in doc.pattern_maps:
        carrier_metadata[map_def.name] = {
            "kind": "pattern_map",
            "key_pattern": map_def.key.pattern,
            "key_forbidden_pattern": map_def.key.forbidden_pattern,
            "min_properties": map_def.min_properties,
            "value_cardinality": (
                "oneOrMany"
                if map_def.value.type_ref == "list"
                else "exactlyOne"
            ),
            "min_items": map_def.value.list_min_items,
        }
    for object_type in doc.object_types:
        datatype = next(
            (
                prop
                for prop in object_type.properties
                if prop.name == "@type"
            ),
            None,
        )
        carrier_metadata[object_type.name] = {
            "kind": "closed_typed_literal",
            "members": [prop.name for prop in object_type.properties],
            "datatype_pattern": datatype.pattern if datatype else None,
        }
    if carrier_metadata:
        out.append(
            "named_carrier_metadata := "
            + json.dumps(carrier_metadata, sort_keys=True)
        )
    shape_constraint_metadata: dict[str, dict] = {}
    for shape in doc.shapes:
        lists = {
            prop.name: {
                "min_items": prop.list_min_items,
                "max_items": prop.list_max_items,
                "unique_items": prop.list_unique_items,
                "strict_array": not prop.list_allow_scalar,
            }
            for prop in shape.properties
            if prop.type_ref == "list"
            and (
                prop.list_min_items
                or prop.list_max_items is not None
                or prop.list_unique_items
                or not prop.list_allow_scalar
            )
        }
        constraints: dict[str, object] = {}
        if lists:
            constraints["lists"] = lists
        if shape.not_equals:
            constraints["not_equals"] = [
                {
                    "left": constraint.left_property,
                    "right": constraint.right_property,
                }
                for constraint in shape.not_equals
            ]
        if constraints:
            shape_constraint_metadata[shape.name] = constraints
    if shape_constraint_metadata:
        out.append(
            "shape_constraint_metadata := "
            + json.dumps(shape_constraint_metadata, sort_keys=True)
        )
    out.append("")
    out.append("# Validators emit `deny[msg]` for each violation.")
    for shape in doc.shapes:
        if not shape.type_iri:
            continue
        for constraint in shape.not_equals:
            message = (
                f"{constraint.left_property} must differ from "
                f"{constraint.right_property}"
            )
            out.extend(
                [
                    "deny[msg] if {",
                    f'  input["@type"] == "{shape.type_iri}"',
                    f'  left := input["{constraint.left_property}"]',
                    f'  right := input["{constraint.right_property}"]',
                    "  left == right",
                    f"  msg := {json.dumps(message)}",
                    "}",
                    "",
                ]
            )
    return "\n".join(out)


# ---- CLI -----------------------------------------------------------------

TARGETS = {
    "json-schema": target_json_schema,
    "rust":        target_rust,
    "typescript":  target_typescript,
    "shacl":       target_shacl,
    "rego":        target_rego,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Rulespec Layer 2 constraint compiler")
    ap.add_argument("--in", dest="input", type=Path, required=True)
    ap.add_argument("--target", required=True,
                    choices=sorted(["json-schema", "rust", "typescript", "shacl", "rego"]))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: source {args.input} missing", file=sys.stderr)
        return 2

    # A `CompileError` means the source carries semantics this projector cannot
    # emit faithfully. Exit 1 (compile error) rather than writing a target that
    # is quietly weaker than the CUE.
    try:
        doc = parse_cue_file(args.input)

        # Build a global enum registry by scanning sibling CUE files. Used by
        # the JSON Schema target to inline cross-file enum definitions (so each
        # emitted schema is self-contained) and by the Rust target to resolve
        # cross-file enum names to fully-qualified module paths.
        enum_registry = _scan_global_enum_registry(args.input)
        _classify_global_named_references(doc, enum_registry)
        for pattern_map in doc.pattern_maps:
            _validate_pattern_map(pattern_map, allow_unresolved=False)
        _validate_document_value_objects(doc, allow_unresolved=False)
        reference_classes = _scan_reference_class_registry(args.input)

        if args.target == "json-schema":
            out = target_json_schema(doc, registry=enum_registry)
        elif args.target == "rust":
            out = target_rust(
                doc, registry=enum_registry, source_file=args.input
            )
        elif args.target == "typescript":
            out = target_typescript(
                doc, registry=enum_registry, source_file=args.input
            )
        elif args.target == "shacl":
            out = target_shacl(
                doc,
                reference_classes=reference_classes,
                source_file=args.input,
                registry=enum_registry,
            )
        elif args.target == "rego":
            out = target_rego(
                doc, registry=enum_registry, source_file=args.input
            )
        else:
            out = TARGETS[args.target](doc)
    except CompileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
