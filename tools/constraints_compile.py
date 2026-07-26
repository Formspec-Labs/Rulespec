#!/usr/bin/env python3
"""Rulespec Layer 2 constraint compiler.

CUE source-of-truth → multiple compilation targets:
  - JSON Schema 2020-12 (MUST)
  - Rust validator code  (MUST)
  - TypeScript validator code (MUST)
  - SHACL Turtle Pattern C only (MUST for CUE-expressible constraints)
  - CUE passthrough (identity)
  - Rego (closed-enum + cardinality only)

The compiler reads CUE files as text and extracts the regular structure that
Rulespec CUE follows (defined in constraints/core/, constraints/adversarial/,
constraints/ai-extraction/):

  - `#Name: "lit" | "lit" | "lit"`          → closed enum
  - `#Whole: #PartA | #PartB`                → closed enum assembled from parts
                                               that may live in other files
  - `#Name: { "field": #TypeRef, ... }`     → shape with typed properties
  - `#Name: { #Base, ... }`                  → shape composed from `#Base`
  - `#Name: #Base & { ... }`                 → shape composed from `#Base`
  - `#Name: (#Base & {...}) | (#Base & {...})` → composed disjunction
  - `if X["x"] == "v" { "y": T }`           → conditional branch
  - `if X["start"] > X["end"] { _|_ }`       → ordered-field invariant
  - `{...} | {...}`                          → disjunction branch
  - `list.MinItems(N)` / `[...#X] & list.MinItems(N)` → list cardinality
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

Targets: json-schema | rust | typescript | shacl | cue | rego

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
class PropDef:
    name: str
    type_ref: str             # "string" | "int" | "float" | "bool" | "enum" | "enum_union" | "list"
    enum_ref: Optional[str] = None
    list_inner_enum: Optional[str] = None
    list_min_items: int = 0
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


@dataclass
class ConditionalBranch:
    when_property: str
    when_equals: Optional[str]
    then_require: list[PropDef]


@dataclass
class OrderConstraint:
    lower_property: str
    upper_property: str


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
    disjunctions: list[list[DisjunctionBranch]] = field(default_factory=list)
    # Names of shapes this shape is composed from (`#Base` embedded in the
    # body, or `#Base & {...}`). Resolved into `properties` / `conditionals` /
    # `orders` / `disjunctions` by `_resolve_shape_compositions` so that every
    # emitter sees one flat, fully-composed shape.
    base_refs: list[str] = field(default_factory=list)


@dataclass
class ConstraintDoc:
    package: str
    enums: list[EnumDef] = field(default_factory=list)
    enum_unions: list[EnumUnion] = field(default_factory=list)
    shapes: list[ShapeDef] = field(default_factory=list)


# ---- Parser --------------------------------------------------------------

ENUM_LINE_RE = re.compile(
    r'^#(\w+):\s*("[^"]+"(?:\s*\|\s*"[^"]+")*)\s*$'
)
ENUM_MULTI_RE = re.compile(r'"([^"]+)"')
# Closed-enum-of-refs: `#Name: #A | #B | #C`
ENUM_UNION_RE = re.compile(r'^#(\w+):\s*((?:#\w+\s*\|\s*)+#\w+)\s*$')
ENUM_UNION_REFS_RE = re.compile(r'#(\w+)')


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


def parse_cue_file(path: Path, *, resolve_composition: bool = True) -> ConstraintDoc:
    """Parse one CUE constraint file into the projector's flat AST.

    `resolve_composition=False` returns shapes with their `base_refs` still
    unresolved. It exists so the cross-file shape registry can be built without
    recursing back into composition resolution.
    """
    src = path.read_text()

    doc = ConstraintDoc(package=path.stem)

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
        # Shape opening: `#Name: {` or `#Name: Alias={`
        sm = re.match(r"^#(\w+):\s*(?:\w+=)?\{$", line)
        if sm:
            shape_name = sm.group(1)
            shape, consumed = parse_shape_body(joined_lines, idx + 1)
            shape.name = shape_name
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

    if resolve_composition:
        _resolve_shape_compositions(doc, path)
    return doc


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
                r'^if\s+\w+\["([^"]+)"\]\s*==\s*"([^"]+)"\s*\{',
                line,
            )
            if mc is None:
                # Backward-compatible parser for the repository's early
                # condition spelling. New CUE must use the alias form above.
                mc = re.match(r'^if\s+"([^"]+)"\s*==\s*"([^"]+)"\s*\{', line)
            if mc:
                when_prop, when_eq = mc.group(1), mc.group(2)
                req_props: list[PropDef] = []
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
                shape.conditionals.append(ConditionalBranch(
                    when_property=when_prop, when_equals=when_eq, then_require=req_props
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
    # `[...#Enum] & list.MinItems(N)`
    lm = re.match(r"^\[\.\.\.#(\w+)\]\s*&\s*list\.MinItems\((\d+)\)$", rhs)
    if lm:
        p.type_ref = "list"
        p.list_inner_enum = lm.group(1)
        p.list_min_items = int(lm.group(2))
        return p
    # `[...string] & list.MinItems(N)`
    ls = re.match(r"^\[\.\.\.string\]\s*&\s*list\.MinItems\((\d+)\)$", rhs)
    if ls:
        p.type_ref = "list"
        p.list_of_string = True
        p.list_min_items = int(ls.group(1))
        return p
    # `[...(string & =~"pattern")] & list.MinItems(N)`
    lsp = re.match(
        r'^\[\.\.\.\(string\s*&\s*=~"([^"]+)"\)\]'
        r'(?:\s*&\s*list\.MinItems\((\d+)\))?$',
        rhs,
    )
    if lsp:
        p.type_ref = "list"
        p.list_of_string = True
        p.pattern = _decode_cue_string(lsp.group(1))
        p.list_min_items = int(lsp.group(2) or 0)
        return p
    # `[...#Enum]`
    le = re.match(r"^\[\.\.\.#(\w+)\]$", rhs)
    if le:
        p.type_ref = "list"
        p.list_inner_enum = le.group(1)
        return p
    # `[...string]`
    if rhs == "[...string]":
        p.type_ref = "list"
        p.list_of_string = True
        return p
    # `list.MinItems(N)` — bare list with no item-type constraint. Items may
    # be any JSON value (string, object, array, …). Note: we deliberately do
    # NOT set `list_of_string` here; the previous behavior degraded structured
    # OA selector objects to string, which broke `SourceFragment.hasSelector`.
    lmo = re.match(r"^list\.MinItems\((\d+)\)$", rhs)
    if lmo:
        p.type_ref = "list"
        p.list_min_items = int(lmo.group(1))
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
    "list_inner_enum": None,
    "list_min_items": 0,
    "list_of_string": False,
    "fixed_value": None,
    "pattern": None,
    "forbidden_pattern": None,
    "string_format": None,
    "min_inclusive": None,
    "max_inclusive": None,
    "inline_enum_values": None,
    "enum_union_refs": None,
}

# Facets whose conjunction IS expressible in the flat AST, so two differing
# declarations narrow instead of raising: a bound unified with another bound is
# just the tighter bound, which every target already emits. Every other facet
# (pattern, enum ref, format, fixed value…) would need a real conjunction the
# flat PropDef cannot carry, so a genuine conflict there is a hard error.
_NARROWING_FACETS = {
    "min_inclusive": max,
    "list_min_items": max,
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
    return ConditionalBranch(
        when_property=base.when_property,
        when_equals=base.when_equals,
        then_require=then_require,
    )


def _append_conditional(
    branches: list[ConditionalBranch],
    branch: ConditionalBranch,
    shape_name: str,
) -> None:
    key = (branch.when_property, branch.when_equals)
    for index, existing in enumerate(branches):
        if (existing.when_property, existing.when_equals) == key:
            branches[index] = _unify_conditional(existing, branch, shape_name)
            return
    branches.append(
        ConditionalBranch(
            when_property=branch.when_property,
            when_equals=branch.when_equals,
            then_require=[_copy_property(p) for p in branch.then_require],
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
    """Scan all sibling CUE files for enum definitions, building a global
    registry so cross-file `$ref`s can resolve. Returns `{enum_name: EnumDef
    | EnumUnion}`. Falls back to empty dict if the source file isn't inside
    a recognizable `constraints/` tree.
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
        for definition in [*sibling.enums, *sibling.enum_unions]:
            name = definition.name
            if name in registry:
                raise CompileError(
                    f"enum/union #{name} is declared by both "
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

    if registry:
        for s in doc.shapes:
            for p in s.properties:
                if p.type_ref == "enum" and p.enum_ref:
                    _inline_cross_file(p.enum_ref)
                if p.type_ref == "list" and p.list_inner_enum:
                    _inline_cross_file(p.list_inner_enum)
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
                condition = {
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
            all_of.append({
                "if": condition,
                "then": {"properties": then_props, "required": list(then_props.keys())},
            })
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
    if p.type_ref == "list":
        items: dict
        if p.list_inner_enum:
            items = {"$ref": f"#/$defs/{p.list_inner_enum}"}
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
        # JSON-LD coercion: a single scalar is semantically a one-element list.
        # Accept either form: scalar of items type OR array. minItems>=1 is
        # automatically satisfied by the scalar form.
        return {"anyOf": [items, arr]}
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
    if doc.shapes:
        out.append("use std::collections::BTreeMap;")
        out.append("")

    # Local enum index — used by _rust_type to decide whether an enum reference
    # is local (bare name) or cross-file (fully-qualified path).
    local_enums = {e.name for e in doc.enums} | {u.name for u in doc.enum_unions}

    for s in doc.shapes:
        # The parser diverts `@type` from properties into shape.type_iri, so
        # consult that directly instead of re-scanning properties.
        type_value: Optional[str] = s.type_iri

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
            field_name = _rust_field_clean(p.name)
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


def _rust_field_clean(name: str) -> str:
    """Generate idiomatic Rust field names from JSON-LD property IRIs.
    Drops the `rkaf:` / `oa:` / `skos:` namespace prefix and snake_cases the rest.
    """
    if ":" in name:
        name = name.split(":", 1)[1]
    out = name.replace("-", "_").replace("@", "")
    return _to_snake(out)


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
    if p.type_ref == "enum":
        name = p.enum_ref or "String"
        if local_enums is not None and name not in local_enums and registry is not None:
            fq = _cross_file_enum_path(name, registry)
            if fq:
                return fq
        return name
    if p.type_ref == "list":
        # JSON-LD wire shorthand: scalar OR array. The matching JSON Schema
        # emits `anyOf: [scalar, array]`; mirror with `crate::OneOrMany<T>`.
        if p.list_inner_enum:
            inner = p.list_inner_enum
            if local_enums is not None and inner not in local_enums and registry is not None:
                fq = _cross_file_enum_path(inner, registry)
                if fq:
                    inner = fq
            return f"crate::OneOrMany<{inner}>"
        if p.list_of_string:
            return "crate::OneOrMany<String>"
        # Bare `list.MinItems(N)` with no item-type constraint — any JSON value.
        return "crate::OneOrMany<serde_json::Value>"
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
    out: list[str] = [
        "// AUTO-GENERATED by tools/constraints_compile.py",
        f"// Source: {_source_header(doc, source_file)}",
        "// DO NOT EDIT.",
        "",
    ]
    local_enums = {e.name for e in doc.enums} | {
        union.name for union in doc.enum_unions
    }
    external_enums = sorted(
        {
            enum_name
            for shape in doc.shapes
            for prop in shape.properties
            for enum_name in (
                prop.enum_ref,
                prop.list_inner_enum,
            )
            if enum_name
            and enum_name not in local_enums
            and registry is not None
            and enum_name in registry
        }
    )
    own_relpath = _source_relpath(source_file) if source_file is not None else None
    for enum_name in external_enums:
        specifier = _ts_import_specifier(enum_name, own_relpath)
        if specifier:
            out.append(
                f'import type {{ {enum_name} }} from "{specifier}";'
            )
    if external_enums:
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
            if p.type_ref == "list" and p.list_min_items > 0 and not p.optional:
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
            out.append(f"  const {when_name} = {expression};")
            for requirement in conditional.then_require:
                required_value = f'record["{requirement.name}"]'
                out.append(
                    f"  if ({when_name} && {required_value} === undefined) "
                    f'errs.push("{requirement.name}: required by '
                    f'{conditional.when_property}");'
                )
                if requirement.pattern:
                    pattern = json.dumps(requirement.pattern)
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"(typeof {required_value} !== \"string\" || "
                        f"!new RegExp({pattern}).test({required_value}))) "
                        f'errs.push("{requirement.name}: pattern mismatch");'
                    )
                if requirement.string_format == "date":
                    out.append(
                        f"  if ({when_name} && {required_value} !== undefined && "
                        f"!isRkafDate({required_value})) "
                        f'errs.push("{requirement.name}: invalid date");'
                    )
        for order in s.orders:
            out.append(
                f'  if (v["{order.lower_property}"] > v["{order.upper_property}"]) '
                f'errs.push("{order.lower_property}: must be on or before '
                f'{order.upper_property}");'
            )
        out.append("  return errs;")
        out.append("}")
        out.append("")
    return "\n".join(out)


def _ts_type(p: PropDef) -> str:
    if p.fixed_value is not None:
        return f'"{p.fixed_value}"'
    if p.type_ref == "enum":
        return p.enum_ref or "string"
    if p.type_ref == "list":
        inner = p.list_inner_enum or "string"
        return f"{inner}[]"
    if p.type_ref == "int" or p.type_ref == "float":
        return "number"
    if p.type_ref == "bool":
        return "boolean"
    return "string"


# ---- SHACL target (Pattern C only) ---------------------------------------

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
    out: list[str] = [
        "# AUTO-GENERATED by tools/constraints_compile.py (target=shacl, Pattern C only).",
        f"# Source: {_source_header(doc, source_file)}",
        "# DO NOT EDIT.",
        "",
        "@prefix sh:   <http://www.w3.org/ns/shacl#> .",
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
    for s in doc.shapes:
        if not s.type_iri:
            continue
        type_iri = s.type_iri
        out.append(f"rkaf:{s.name}Shape a sh:NodeShape ;")
        out.append(f"  sh:targetClass {type_iri} ;")
        for p in s.properties:
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
            if p.type_ref != "list":
                line += " sh:maxCount 1 ;"
            if p.type_ref == "enum":
                values = " ".join(resolve_enum(p.enum_ref or ""))
                if values:
                    line += f" sh:in ( {values} ) ;"
            if p.type_ref == "list" and p.list_inner_enum:
                values = " ".join(resolve_enum(p.list_inner_enum))
                if values:
                    line += f" sh:in ( {values} ) ;"
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
            out.append("    [ sh:not [ sh:property [")
            if c.when_equals is None:
                out.append(f"        sh:path {c.when_property} ; sh:minCount 1")
            else:
                out.append(
                    f"        sh:path {c.when_property} ; sh:hasValue {c.when_equals}"
                )
            out.append("      ] ] ]")
            if c.then_require:
                requirement = c.then_require[0]
                line = (
                    f"    [ sh:property [ sh:path {requirement.name} ; "
                    "sh:minCount 1 ;"
                )
                if requirement.pattern:
                    line += f" sh:pattern {json.dumps(requirement.pattern)} ;"
                if requirement.string_format == "date":
                    line += " sh:datatype xsd:date ;"
                line += " ] ]"
                out.append(line)
            else:
                out.append("    [ sh:property [ sh:path rkaf:_unsatisfiable ; sh:minCount 1 ] ]")
            out.append("  ) ;")
        for order in s.orders:
            out.append(
                f"  sh:property [ sh:path {order.lower_property} ; "
                f"sh:lessThanOrEquals {order.upper_property} ; ] ;"
            )
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


# ---- CUE passthrough -----------------------------------------------------

def target_cue(doc: ConstraintDoc, source_path: Path) -> str:
    return source_path.read_text()


# ---- Rego target ---------------------------------------------------------

def _rego_symbol(name: str) -> str:
    """CUE definition name → Rego snake_case value-set symbol."""
    return re.sub(r"([A-Z])", r"_\1", name).lstrip("_").lower()


def target_rego(
    doc: ConstraintDoc,
    registry: Optional[dict] = None,
    source_file: Optional[Path] = None,
) -> str:
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
    out.append("")
    out.append("# Validators emit `deny[msg]` for each violation.")
    return "\n".join(out)


# ---- CLI -----------------------------------------------------------------

TARGETS = {
    "json-schema": target_json_schema,
    "rust":        target_rust,
    "typescript":  target_typescript,
    "shacl":       target_shacl,
    "rego":        target_rego,
    # cue handled specially (needs source path)
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Rulespec Layer 2 constraint compiler")
    ap.add_argument("--in", dest="input", type=Path, required=True)
    ap.add_argument("--target", required=True,
                    choices=sorted(["json-schema", "rust", "typescript", "shacl", "rego", "cue"]))
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
        reference_classes = _scan_reference_class_registry(args.input)

        if args.target == "cue":
            out = target_cue(doc, args.input)
        elif args.target == "json-schema":
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
