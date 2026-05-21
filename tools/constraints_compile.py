#!/usr/bin/env python3
"""Rulespec Layer 2 constraint compiler.

CUE source-of-truth → multiple compilation targets:
  - JSON Schema 2020-12 (MUST)
  - Rust validator code  (MUST)
  - TypeScript validator code (MUST)
  - SHACL Turtle Pattern C only (MAY; v0.2 hand-written shapes remain canonical)
  - CUE passthrough (identity)
  - Rego (closed-enum + cardinality only)

The compiler reads CUE files as text and extracts the regular structure that
Rulespec CUE follows (defined in constraints/core/, constraints/adversarial/,
constraints/ai-extraction/):

  - `#Name: "lit" | "lit" | "lit"`          → closed enum
  - `#Name: { "field": #TypeRef, ... }`     → shape with typed properties
  - `if "x" == "v" { "y": T }`              → conditional branch
  - `{...} | {...}`                          → disjunction branch
  - `list.MinItems(N)` / `[...#X] & list.MinItems(N)` → list cardinality

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
from dataclasses import dataclass, field
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
    min_inclusive: Optional[float] = None
    max_inclusive: Optional[float] = None
    inline_enum_values: Optional[list[str]] = None
    enum_union_refs: Optional[list[str]] = None


@dataclass
class ConditionalBranch:
    when_property: str
    when_equals: str
    then_require: list[PropDef]


@dataclass
class DisjunctionBranch:
    properties: list[PropDef]


@dataclass
class ShapeDef:
    name: str
    type_iri: Optional[str]
    properties: list[PropDef] = field(default_factory=list)
    conditionals: list[ConditionalBranch] = field(default_factory=list)
    disjunctions: list[list[DisjunctionBranch]] = field(default_factory=list)


@dataclass
class ConstraintDoc:
    package: str
    enums: list[EnumDef] = field(default_factory=list)
    enum_unions: list[EnumUnion] = field(default_factory=list)
    shapes: list[ShapeDef] = field(default_factory=list)


# ---- Parser --------------------------------------------------------------

ENUM_LINE_RE = re.compile(r'^#(\w+):\s*((?:"[^"]+"\s*\|\s*)+"[^"]+")\s*$')
ENUM_MULTI_RE = re.compile(r'"([^"]+)"')
# Closed-enum-of-refs: `#Name: #A | #B | #C`
ENUM_UNION_RE = re.compile(r'^#(\w+):\s*((?:#\w+\s*\|\s*)+#\w+)\s*$')
ENUM_UNION_REFS_RE = re.compile(r'#(\w+)')


def parse_cue_file(path: Path) -> ConstraintDoc:
    src = path.read_text()
    package_match = re.search(r"^package\s+(\w+)", src, re.MULTILINE)
    package = package_match.group(1) if package_match else path.stem

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
        # Shape opening: `#Name: {`
        sm = re.match(r"^#(\w+):\s*\{$", line)
        if sm:
            shape_name = sm.group(1)
            shape, consumed = parse_shape_body(joined_lines, idx + 1)
            shape.name = shape_name
            doc.shapes.append(shape)
            idx += 1 + consumed
            continue
        # Shape composition: `#Name: (#Other & {...}) | (#Other & {...})`
        # We capture these as a degenerate shape (just the name, no constraints)
        # so the codegen has something to emit; the disjunction itself is
        # source-only and not projected to JSON Schema.
        cm = re.match(r"^#(\w+):\s*\(", line)
        if cm:
            doc.shapes.append(ShapeDef(name=cm.group(1), type_iri=None))
            idx += 1
            continue
        idx += 1

    return doc


def parse_shape_body(lines: list[tuple[int, str]], start: int) -> tuple[ShapeDef, int]:
    """Parse the body of `#Name: { ... }` starting at `start`. Returns (shape, lines_consumed).

    Walks line-by-line. Recognized constructs:
      - Top-level property: `"name": <type-expr>`
      - Conditional: `if "x" == "v" { props }`
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
        opens = line.count("{")
        closes = line.count("}")
        if line == "}":
            depth -= 1
            if depth == 0:
                # End of shape body
                break
            i += 1
            continue
        # Conditional
        if line.startswith("if ") and "{" in line:
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
    # `string & =~"pattern"`
    pm = re.match(r'^string\s*&\s*=~"([^"]+)"$', rhs)
    if pm:
        p.type_ref = "string"
        p.pattern = pm.group(1)
        return p
    # `=~"pattern"`
    pm2 = re.match(r'^=~"([^"]+)"$', rhs)
    if pm2:
        p.type_ref = "string"
        p.pattern = pm2.group(1)
        return p
    # `string`
    if rhs == "string":
        p.type_ref = "string"
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
    for cue_file in constraints_root.rglob("*.cue"):
        try:
            sibling = parse_cue_file(cue_file)
        except Exception:
            continue
        package = cue_file.stem  # e.g. "usage-eligibility"
        for e in sibling.enums:
            if e.name not in registry:
                registry[e.name] = e
                _REGISTRY_SOURCES[e.name] = package
        for u in sibling.enum_unions:
            if u.name not in registry:
                registry[u.name] = u
                _REGISTRY_SOURCES[u.name] = package
    return registry


def target_json_schema(doc: ConstraintDoc, registry: Optional[dict] = None) -> str:
    schemas: dict = {}
    enum_by_name = {e.name: e for e in doc.enums}
    for e in doc.enums:
        schemas[e.name] = {"type": "string", "enum": e.values}
    # Enum-unions: collapse to a single closed enum from the union of referenced values.
    for u in doc.enum_unions:
        union_values: list[str] = []
        for ref in u.refs:
            if ref in enum_by_name:
                union_values.extend(enum_by_name[ref].values)
        schemas[u.name] = {"type": "string", "enum": union_values}

    # Inline cross-file enum definitions referenced by this doc's properties /
    # disjunctions / conditionals so the resulting schema is self-contained.
    # This makes embedded validators (rkaf-validate) able to resolve every
    # `$ref` without splicing in sibling schemas at load time.
    def _inline_cross_file(enum_name: str) -> None:
        if enum_name in schemas or registry is None:
            return
        entry = registry.get(enum_name)
        if entry is None:
            return
        if isinstance(entry, EnumDef):
            schemas[enum_name] = {"type": "string", "enum": entry.values}
        else:  # EnumUnion
            values: list[str] = []
            for ref in entry.refs:
                ref_entry = registry.get(ref)
                if isinstance(ref_entry, EnumDef):
                    values.extend(ref_entry.values)
            schemas[enum_name] = {"type": "string", "enum": values}

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
                        props[bp.name] = property_to_jsonschema(bp, doc)
        if s.type_iri:
            props["@type"] = {"const": s.type_iri}
            required.append("@type")
        for p in s.properties:
            props[p.name] = property_to_jsonschema(p, doc)
            if not p.optional and p.name not in disjunction_prop_names:
                required.append(p.name)
        # Conditional branches → JSON Schema `allOf` with `if/then`
        all_of: list[dict] = []
        for c in s.conditionals:
            then_props: dict = {}
            for tp in c.then_require:
                then_props[tp.name] = property_to_jsonschema(tp, doc)
                if tp.name not in props:
                    props[tp.name] = property_to_jsonschema(tp, doc)
            all_of.append({
                "if":   {"properties": {c.when_property: {"const": c.when_equals}}, "required": [c.when_property]},
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
                    br_props[bp.name] = property_to_jsonschema(bp, doc)
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
        schemas[s.name] = schema

    envelope = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://rulespec.org/jsonschema/{doc.package}.json",
        "title": doc.package,
        "$defs": schemas,
    }
    return json.dumps(envelope, indent=2)


def property_to_jsonschema(p: PropDef, doc: ConstraintDoc) -> dict:
    if p.fixed_value is not None:
        return {"const": p.fixed_value}
    if p.inline_enum_values:
        return {"type": "string", "enum": p.inline_enum_values}
    if p.enum_union_refs:
        # Resolve to a single closed enum from the referenced enums.
        enum_by_name = {e.name: e for e in doc.enums}
        vals: list[str] = []
        for ref in p.enum_union_refs:
            if ref in enum_by_name:
                vals.extend(enum_by_name[ref].values)
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
    return out


# ---- Rust target ---------------------------------------------------------

def target_rust(doc: ConstraintDoc, registry: Optional[dict] = None) -> str:
    out: list[str] = [
        "// AUTO-GENERATED by tools/constraints_compile.py",
        f"// Source: constraints/{doc.package}.cue",
        "// DO NOT EDIT.",
        "",
        "use serde::{Deserialize, Serialize};",
        "",
    ]
    for e in doc.enums:
        out.append("#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]")
        out.append(f"pub enum {e.name} {{")
        for v in e.values:
            variant = _pascal_after_colon(v)
            out.append(f'    #[serde(rename = "{v}")]')
            out.append(f"    {variant},")
        out.append("}")
        out.append("")
    # Enum unions: emit as Rust enum with variants flattened from the referenced enums.
    enum_by_name = {e.name: e for e in doc.enums}
    for u in doc.enum_unions:
        out.append("#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]")
        out.append(f"pub enum {u.name} {{")
        for ref in u.refs:
            if ref in enum_by_name:
                for v in enum_by_name[ref].values:
                    variant = _pascal_after_colon(v)
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

        out.append("#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]")
        out.append(f"pub struct {s.name} {{")

        # @type field — emit specially with default constructor reference
        if type_value is not None:
            out.append(f'    #[serde(rename = "@type", default = "{s.name}::default_type")]')
            out.append(f"    pub type_: String,")

        # @id field — always optional, always emitted (JSON-LD reserved key)
        out.append('    #[serde(rename = "@id", skip_serializing_if = "Option::is_none", default)]')
        out.append("    pub id: Option<String>,")

        # Other properties
        for p in s.properties:
            if p.name in ("@type", "@id"):
                continue
            ty = _rust_type(p, local_enums=local_enums, registry=registry)
            field_name = _rust_field_clean(p.name)
            if p.optional:
                out.append(
                    f'    #[serde(rename = "{p.name}", skip_serializing_if = "Option::is_none", default)]'
                )
                out.append(f"    pub {field_name}: Option<{ty}>,")
            else:
                out.append(f'    #[serde(rename = "{p.name}")]')
                out.append(f"    pub {field_name}: {ty},")

        # Catch-all for unknown properties (preserves round-trip).
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


def _cross_file_enum_path(enum_name: str, registry: dict) -> Optional[str]:
    """Given a registry of {enum_name: EnumDef|EnumUnion}, look up which CUE
    source file defines `enum_name` and return the fully-qualified Rust path.
    The registry's EnumDef stores no source-file hint, so this implementation
    relies on the global scan: the registry is built by parsing each CUE file
    and the EnumDef/EnumUnion's residence is tracked via the parallel
    `_REGISTRY_SOURCES` map below. Returns None if no resolution is possible.
    """
    pkg = _REGISTRY_SOURCES.get(enum_name)
    if not pkg:
        return None
    return f"crate::generated::{_module_for_cue_package(pkg)}::{enum_name}"


# Populated by `_scan_global_enum_registry`; maps enum/union name to the CUE
# package (file stem) that defines it. Used to compute fully-qualified Rust
# module paths for cross-file enum references.
_REGISTRY_SOURCES: dict[str, str] = {}


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

def target_typescript(doc: ConstraintDoc) -> str:
    out: list[str] = [
        "// AUTO-GENERATED by tools/constraints_compile.py",
        f"// Source: constraints/{doc.package}.cue",
        "// DO NOT EDIT.",
        "",
    ]
    for e in doc.enums:
        lits = " | ".join(f'"{v}"' for v in e.values)
        out.append(f"export type {e.name} = {lits};")
        out.append("")
    enum_by_name = {e.name: e for e in doc.enums}
    for u in doc.enum_unions:
        all_values: list[str] = []
        for ref in u.refs:
            if ref in enum_by_name:
                all_values.extend(enum_by_name[ref].values)
        lits = " | ".join(f'"{v}"' for v in all_values)
        out.append(f"export type {u.name} = {lits};")
        out.append("")
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
        for p in s.properties:
            if p.type_ref == "list" and p.list_min_items > 0 and not p.optional:
                out.append(f'  if (!Array.isArray(v["{p.name}"]) || v["{p.name}"].length < {p.list_min_items}) errs.push("{p.name}: < {p.list_min_items} items");')
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

def target_shacl(doc: ConstraintDoc) -> str:
    out: list[str] = [
        "# AUTO-GENERATED by tools/constraints_compile.py (target=shacl, Pattern C only).",
        f"# Source: constraints/{doc.package}.cue",
        "# DO NOT EDIT.",
        "",
        "@prefix sh:   <http://www.w3.org/ns/shacl#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix oa:   <http://www.w3.org/ns/oa#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix dpv:  <https://w3id.org/dpv#> .",
        "@prefix rkaf: <https://rulespec.org/ns/v1#> .",
        "",
    ]
    enum_by_name = {e.name: e for e in doc.enums}
    # Expand enum unions: a union {A,B,C} contributes the flattened values
    # of its referenced enums to a single resolved value list.
    def resolve_enum(name: str) -> list[str]:
        if name in enum_by_name:
            return enum_by_name[name].values
        for u in doc.enum_unions:
            if u.name == name:
                vals: list[str] = []
                for ref in u.refs:
                    vals.extend(resolve_enum(ref))
                return vals
        return []
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
                min_count = 1
            if p.type_ref == "list" and p.list_min_items > min_count:
                min_count = p.list_min_items
            if min_count > 0:
                line += f" sh:minCount {min_count} ;"
            if p.type_ref == "enum":
                values = " ".join(resolve_enum(p.enum_ref or ""))
                if values:
                    line += f" sh:in ( {values} ) ;"
            if p.type_ref == "list" and p.list_inner_enum:
                values = " ".join(resolve_enum(p.list_inner_enum))
                if values:
                    line += f" sh:in ( {values} ) ;"
            line += " ] ;"
            out.append(line)
        # Conditional branches → Pattern C (sh:or with sh:not)
        for c in s.conditionals:
            out.append("  sh:or (")
            out.append(f"    [ sh:property [ sh:path {c.when_property} ;")
            out.append(f"        sh:not [ sh:hasValue {c.when_equals} ] ] ]")
            if c.then_require:
                req = c.then_require[0].name
                out.append(f"    [ sh:property [ sh:path {req} ; sh:minCount 1 ] ]")
            else:
                out.append("    [ sh:property [ sh:path rkaf:_unsatisfiable ; sh:minCount 1 ] ]")
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


# ---- CUE passthrough -----------------------------------------------------

def target_cue(doc: ConstraintDoc, source_path: Path) -> str:
    return source_path.read_text()


# ---- Rego target ---------------------------------------------------------

def target_rego(doc: ConstraintDoc) -> str:
    out: list[str] = [
        "# AUTO-GENERATED by tools/constraints_compile.py (target=rego).",
        f"# Source: constraints/{doc.package}.cue",
        f"package rkaf.{doc.package.replace('-', '_')}",
        "",
    ]
    for e in doc.enums:
        lower = re.sub(r"([A-Z])", r"_\1", e.name).lstrip("_").lower()
        vals = ", ".join(f'"{v}"' for v in e.values)
        out.append(f"{lower}_values := [{vals}]")
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

    doc = parse_cue_file(args.input)

    # Build a global enum registry by scanning sibling CUE files. Used by the
    # JSON Schema target to inline cross-file enum definitions (so each
    # emitted schema is self-contained) and by the Rust target to resolve
    # cross-file enum names to fully-qualified module paths.
    enum_registry = _scan_global_enum_registry(args.input)

    if args.target == "cue":
        out = target_cue(doc, args.input)
    elif args.target == "json-schema":
        out = target_json_schema(doc, registry=enum_registry)
    elif args.target == "rust":
        out = target_rust(doc, registry=enum_registry)
    else:
        out = TARGETS[args.target](doc)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
