#!/usr/bin/env python3
"""Audit Rulespec L0 carrier mappings and self-certifications.

An L0 mapping is one or more fenced ``yaml rkaf-l0-mapping`` blocks. Each
block pins the Rulespec contract digest and contains mappings that declare
carrier columns, subject type, relationship direction, value kind, and term.
Identifier transforms include executable samples.

With no arguments, this tool discovers L0 declarations under
``conformance/partners``. A Markdown argument audits a mapping directly; a
YAML argument audits an L0 partner declaration and its referenced mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

try:
    from constraints_compile import (
        ConstraintDoc,
        parse_cue_file,
        range_registry_paths,
    )
except ModuleNotFoundError:  # Imported as tools.l0_mapping_audit in unit tests.
    from tools.constraints_compile import (
        ConstraintDoc,
        parse_cue_file,
        range_registry_paths,
    )

ROOT = Path(__file__).resolve().parent.parent
CONSTRAINTS_ROOT = ROOT / "constraints"
CUE_DIR = ROOT / "constraints" / "core"
ANALYSIS_DIR = ROOT / "constraints" / "analysis"
PROFILES_DIR = ROOT / "constraints" / "profiles"
CONTEXT_PATH = ROOT / "context" / "rkaf-context.jsonld"
RANGE_PATH = ROOT / "constraints" / "semantics" / "l0-ranges.cue"
PARTNER_DIR = ROOT / "conformance" / "partners"

# "Argument not supplied", distinct from an explicit `None`. A caller that
# redirects `cue_dir` at a synthetic tree must not silently pick up the REAL
# repo's profiles or range registry alongside it: the sibling directories are
# derived from whatever `cue_dir` it named. Passing `None` explicitly means
# "no profiles at all", which `PROFILES_DIR`-as-default could never express.
_UNSET: Any = object()


def shape_source_paths(
    *,
    cue_dir: Path | None = None,
    profiles_dir: Path | None = _UNSET,
    analysis_dir: Path | None = _UNSET,
) -> list[Path]:
    """Every CUE file that declares vocabulary-bearing shapes.

    The kernel, the document-analysis module, and every domain profile. The
    analysis module owns the generic comparison contracts (relation changes,
    comparison contexts, resolver proofs, neutral findings, the disabled
    closure claim); profiles own jurisdiction-specific terms (US regulatory
    identifiers, `rkaf:publishedInProceeding`, the rulemaking classes). An L0
    mapping that cites a term from either is still citing the Rulespec
    contract, so the registry and the CONTRACT DIGEST have to cover all three
    trees — a tree left out here is a tree a consumer can pin without pinning.
    Range registries live in their own `semantics/` package directory and are
    handled separately.

    `profiles_dir` and `analysis_dir` default to `cue_dir`'s own siblings, so
    redirecting `cue_dir` redirects all three. Pass `None` explicitly to scan
    the kernel alone.
    """
    cue_dir = CUE_DIR if cue_dir is None else cue_dir
    if profiles_dir is _UNSET:
        profiles_dir = cue_dir.parent / "profiles"
    if analysis_dir is _UNSET:
        analysis_dir = cue_dir.parent / "analysis"
    paths = sorted(cue_dir.glob("*.cue"))
    if analysis_dir is not None and analysis_dir.is_dir():
        paths.extend(sorted(analysis_dir.glob("*.cue")))
    if profiles_dir is not None and profiles_dir.is_dir():
        paths.extend(sorted(profiles_dir.glob("*/*.cue")))
    return paths

FENCE_START = re.compile(r"^```yaml[ \t]+rkaf-l0-mapping[ \t]*$")
FENCE_END = re.compile(r"^```[ \t]*$")
FULL_IRI = re.compile(r"^https?://[^\s]+$")
ABSOLUTE_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
CONTRACT_VERSION = re.compile(r"^sha256:[0-9a-f]{64}$")
ALLOWED_BLOCK_KEYS = {"rulespec_version", "mappings"}
ALLOWED_ENTRY_KEYS = {
    "table",
    "column",
    "columns",
    "subject_type",
    "term",
    "direction",
    "object_type",
    "value_kind",
    "collection",
    "enum_map",
    "transform",
    "samples",
    "source_membership",
}
REQUIRED_ENTRY_KEYS = {"table", "subject_type", "term", "direction", "value_kind"}
VALUE_KINDS = {"iri", "vocab", "literal", "number", "date"}
# Value kinds an `enum_map` may declare. Both put the mapped value on the wire
# as an IRI, which is what `sh:in` over IRI members matches; the difference is
# only whether the context resolves a bare term (`@vocab`) or carries the
# already-expanded IRI (`@id`).
ENUM_MAP_VALUE_KINDS = {"vocab", "iri"}
DIRECTIONS = {"forward", "inverse"}
COLLECTIONS = {"scalar", "json-list"}
IDENTIFIER_TERMS = {
    "https://rulespec.org/ns/v1#hasArtifactIdentifier",
    "https://rulespec.org/ns/v1#hasRegulatoryIdentifier",
    "https://rulespec.org/ns/v1#hasAgendaItemIdentifier",
    "https://rulespec.org/ns/v1#hasProceedingIdentifier",
    "https://rulespec.org/ns/v1#hasDocketIdentifier",
}
# Terms whose value grammar is not recoverable from the value, so a mapping
# that mints one MUST name the registered scheme it minted under. Identifier
# predicates are the original members; `rkaf:assignmentEvidence` joined them
# when `#FragmentIdentityScheme` registered a second identity form for a cited
# region (Core §4.2) — a carrier-local fragment URN and a published fragment
# IRI are both absolute IRIs, and only the declaration says which grammar the
# producer is claiming.
IDENTIFIER_SCHEME_TERMS = {
    "https://rulespec.org/ns/v1#assignmentEvidence":
        "https://rulespec.org/ns/v1#assignmentEvidenceScheme",
    "https://rulespec.org/ns/v1#hasArtifactIdentifier":
        "https://rulespec.org/ns/v1#artifactIdentifierScheme",
    "https://rulespec.org/ns/v1#hasRegulatoryIdentifier":
        "https://rulespec.org/ns/v1#regulatoryIdentifierScheme",
    "https://rulespec.org/ns/v1#hasAgendaItemIdentifier":
        "https://rulespec.org/ns/v1#agendaItemIdentifierScheme",
    "https://rulespec.org/ns/v1#hasProceedingIdentifier":
        "https://rulespec.org/ns/v1#proceedingIdentifierScheme",
    "https://rulespec.org/ns/v1#hasDocketIdentifier":
        "https://rulespec.org/ns/v1#docketIdentifierScheme",
}
ALLOWED_TRANSFORM_KEYS = {
    "template",
    "pattern",
    "replacement",
    "identifier_scheme",
}
ALLOWED_SAMPLE_KEYS = {"input", "output"}
ALLOWED_SOURCE_MEMBERSHIP_KEYS = {"table", "column"}


@dataclass(frozen=True)
class VocabularyRegistry:
    terms: frozenset[str]
    enum_values: frozenset[str]
    enum_values_by_term: dict[str, frozenset[str]]
    domains_by_term: dict[str, frozenset[str]]
    ranges_by_term: dict[str, str]
    value_kinds_by_term: dict[str, str]
    contract_version: str


@dataclass(frozen=True)
class MappingAudit:
    terms: frozenset[str]
    entries: int
    blocks: int
    issues: tuple[str, ...]
    versions: frozenset[str] = frozenset()


def _expand(value: str, prefixes: dict[str, str]) -> str:
    if FULL_IRI.fullmatch(value):
        return value
    if ":" not in value:
        return value
    prefix, suffix = value.split(":", 1)
    base = prefixes.get(prefix)
    return f"{base}{suffix}" if base else value


def _enum_registry(docs: list[ConstraintDoc]) -> dict[str, set[str]]:
    direct = {enum.name: set(enum.values) for doc in docs for enum in doc.enums}
    unions = {union.name: tuple(union.refs) for doc in docs for union in doc.enum_unions}

    def resolve(name: str, seen: frozenset[str] = frozenset()) -> set[str]:
        if name in direct:
            return set(direct[name])
        if name in seen:
            return set()
        values: set[str] = set()
        for ref in unions.get(name, ()):
            values.update(resolve(ref, seen | {name}))
        return values

    return {name: resolve(name) for name in set(direct) | set(unions)}


def _value_kind(context_entry: Any) -> str | None:
    if not isinstance(context_entry, dict):
        return None
    coercion = context_entry.get("@type")
    if coercion == "@id":
        return "iri"
    if coercion == "@vocab":
        return "vocab"
    if coercion == "xsd:date":
        return "date"
    if coercion in {"xsd:float", "xsd:double", "xsd:decimal", "xsd:int", "xsd:integer"}:
        return "number"
    if isinstance(coercion, str):
        return "literal"
    return None


def _load_ranges(paths: list[Path], prefixes: dict[str, str]) -> dict[str, str]:
    ranges: dict[str, str] = {}
    for path in paths:
        for term, target in re.findall(
            r'^\s*"([^"]+)":\s*"([^"]+)"', path.read_text(), re.MULTILINE
        ):
            ranges[_expand(term, prefixes)] = _expand(target, prefixes)
    return ranges


def _contract_version(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            relative = resolved.as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def load_vocabulary_registry(
    *,
    cue_dir: Path = CUE_DIR,
    context_path: Path = CONTEXT_PATH,
    range_path: Path = _UNSET,
    profiles_dir: Path | None = _UNSET,
    analysis_dir: Path | None = _UNSET,
) -> VocabularyRegistry:
    # Both sibling paths derive from `cue_dir` unless named explicitly, so a
    # caller pointing `cue_dir` at a synthetic tree gets that tree's profiles
    # and ranges — never the real repo's silently unioned in.
    if range_path is _UNSET:
        range_path = cue_dir.parent / "semantics" / "l0-ranges.cue"
    context_doc = json.loads(context_path.read_text())
    context = context_doc["@context"]
    prefixes = {
        key: value
        for key, value in context.items()
        if ":" not in key and isinstance(value, str)
    }
    shape_paths = shape_source_paths(
        cue_dir=cue_dir, profiles_dir=profiles_dir, analysis_dir=analysis_dir
    )
    # `range_path` names the KERNEL registry; the contract is the union of every
    # `l0-ranges.cue` beneath the same `constraints/` root, so a profile's
    # ranges are covered without a second parameter.
    range_paths = range_registry_paths(range_path.parent.parent)
    docs = [parse_cue_file(path) for path in shape_paths]
    enums = _enum_registry(docs)

    terms: set[str] = set()
    value_kinds: dict[str, str] = {}
    for key, entry in context.items():
        if ":" in key:
            term = _expand(key, prefixes)
            terms.add(term)
            kind = _value_kind(entry)
            if kind:
                value_kinds[term] = kind

    values_by_term: dict[str, set[str]] = {}
    domains_by_term: dict[str, set[str]] = {}
    for doc in docs:
        for shape in doc.shapes:
            if shape.type_iri:
                shape_type = _expand(shape.type_iri, prefixes)
                terms.add(shape_type)
            else:
                shape_type = None
            props = list(shape.properties)
            props.extend(
                prop
                for conditional in shape.conditionals
                for prop in conditional.then_require
            )
            props.extend(
                prop
                for group in shape.disjunctions
                for branch in group
                for prop in branch.properties
            )
            for prop in props:
                term = _expand(prop.name, prefixes)
                terms.add(term)
                if shape_type:
                    domains_by_term.setdefault(term, set()).add(shape_type)
                values: set[str] = set()
                if prop.enum_ref:
                    values.update(enums.get(prop.enum_ref, set()))
                if prop.list_inner_enum:
                    values.update(enums.get(prop.list_inner_enum, set()))
                if prop.inline_enum_values:
                    values.update(prop.inline_enum_values)
                if prop.enum_union_refs:
                    for ref in prop.enum_union_refs:
                        values.update(enums.get(ref, set()))
                if values:
                    values_by_term.setdefault(term, set()).update(
                        _expand(value, prefixes) for value in values
                    )
                    value_kinds.setdefault(term, "vocab")
                elif prop.string_format == "date":
                    value_kinds.setdefault(term, "date")
                elif prop.type_ref in {"int", "float"}:
                    value_kinds.setdefault(term, "number")
                else:
                    value_kinds.setdefault(term, "literal")

    all_enum_values = {
        _expand(value, prefixes)
        for values in enums.values()
        for value in values
    }
    # The digest pins every input that can change what the contract accepts:
    # kernel shapes, profile shapes, the shared context, and every range
    # registry. A profile CUE edit MUST move the digest, or an L0 declaration
    # could keep certifying against a contract that no longer exists.
    contract_paths = [*shape_paths, context_path, *range_paths]
    return VocabularyRegistry(
        terms=frozenset(terms),
        enum_values=frozenset(all_enum_values),
        enum_values_by_term={
            term: frozenset(values) for term, values in values_by_term.items()
        },
        domains_by_term={
            term: frozenset(domains) for term, domains in domains_by_term.items()
        },
        ranges_by_term=_load_ranges(range_paths, prefixes),
        value_kinds_by_term=value_kinds,
        contract_version=_contract_version(contract_paths),
    )


def extract_mapping_blocks(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    blocks: list[tuple[int, str]] = []
    issues: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not FENCE_START.fullmatch(lines[index]):
            index += 1
            continue
        start_line = index + 1
        body: list[str] = []
        index += 1
        while index < len(lines) and not FENCE_END.fullmatch(lines[index]):
            body.append(lines[index])
            index += 1
        if index == len(lines):
            issues.append(f"line {start_line}: unterminated rkaf-l0-mapping fence")
            break
        blocks.append((start_line, "\n".join(body)))
        index += 1
    if not blocks and not issues:
        issues.append("no fenced `yaml rkaf-l0-mapping` blocks found")
    return blocks, issues


def _mapping_columns(
    entry: dict[str, Any],
    *,
    location: str,
    issues: list[str],
) -> tuple[str, ...] | None:
    column = entry.get("column")
    columns = entry.get("columns")
    if (column is None) == (columns is None):
        issues.append(f"{location}: exactly one of column or columns is required")
        return None
    if column is not None:
        if not isinstance(column, str) or not column.strip():
            issues.append(f"{location}: column MUST be a non-empty string")
            return None
        return (column,)
    if (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(value, str) and value.strip() for value in columns)
    ):
        issues.append(f"{location}: columns MUST be a non-empty list of strings")
        return None
    if len(set(columns)) != len(columns):
        issues.append(f"{location}: columns MUST NOT contain duplicates")
        return None
    return tuple(columns)


def _validate_type_iri(
    value: Any,
    *,
    key: str,
    location: str,
    registry: VocabularyRegistry,
    issues: list[str],
) -> str | None:
    if not isinstance(value, str) or not FULL_IRI.fullmatch(value):
        issues.append(f"{location}: {key} MUST be a full HTTP(S) IRI: {value!r}")
        return None
    if value not in registry.terms:
        issues.append(f"{location}: unregistered {key}: {value}")
        return None
    return value


def _validate_enum_map(
    enum_map: Any,
    *,
    term: str,
    value_kind: Any,
    location: str,
    registry: VocabularyRegistry,
    issues: list[str],
) -> None:
    if not isinstance(enum_map, dict) or not enum_map:
        issues.append(f"{location}: enum_map MUST be a non-empty mapping")
        return
    # A closed enum reaches the wire as an IRI under EITHER coercion. `@vocab`
    # resolves a bare term against the vocabulary; `@id` carries the same value
    # already expanded. `rkaf:decision` and `rkaf:assertionOrigin` are closed
    # sets registered with `@type: @id`, so restricting `enum_map` to `vocab`
    # left them with no way to declare closed-enum discipline at all — only a
    # transform, whose output the audit checks for IRI SHAPE and never for
    # membership. That is the unchecked semantic claim §0.1 requirement 4
    # exists to prevent.
    if value_kind not in ENUM_MAP_VALUE_KINDS:
        issues.append(
            f"{location}: enum_map requires value_kind "
            f"{' or '.join(sorted(ENUM_MAP_VALUE_KINDS))}"
        )
    allowed = registry.enum_values_by_term.get(term)
    if allowed is None:
        issues.append(f"{location}: enum_map is only valid for a closed-enum term")
        return
    for source_value, target in enum_map.items():
        if not isinstance(source_value, str) or not source_value:
            issues.append(f"{location}: enum_map source values MUST be non-empty strings")
        if not isinstance(target, str) or not FULL_IRI.fullmatch(target):
            issues.append(
                f"{location}: enum_map target MUST be a full HTTP(S) IRI: {target!r}"
            )
            continue
        if target not in registry.enum_values:
            issues.append(f"{location}: unregistered enum target: {target}")
        elif target not in allowed:
            issues.append(f"{location}: enum target {target} is not valid for term {term}")


def _validate_transform(
    transform: Any,
    *,
    term: str,
    columns: tuple[str, ...],
    collection: str,
    location: str,
    registry: VocabularyRegistry,
    issues: list[str],
) -> dict[str, Any] | None:
    if not isinstance(transform, dict) or not transform:
        issues.append(f"{location}: transform MUST be a non-empty mapping")
        return None
    extra = set(transform) - ALLOWED_TRANSFORM_KEYS
    valid = not extra
    if extra:
        issues.append(f"{location}: transform has unknown keys {sorted(extra)}")

    template = transform.get("template")
    pattern = transform.get("pattern")
    replacement = transform.get("replacement")
    has_template = isinstance(template, str) and bool(template)
    has_regex = (
        isinstance(pattern, str)
        and bool(pattern)
        and isinstance(replacement, str)
    )
    if has_template == has_regex:
        valid = False
        issues.append(
            f"{location}: transform requires exactly one of template or "
            "pattern plus replacement"
        )
    if pattern is not None or replacement is not None:
        if not has_regex:
            valid = False
            issues.append(
                f"{location}: pattern and replacement MUST both be strings"
            )
        elif len(columns) != 1 or collection != "scalar":
            valid = False
            issues.append(
                f"{location}: regex transforms require one scalar source column"
            )
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                valid = False
                issues.append(f"{location}: invalid transform pattern: {exc}")

    scheme = transform.get("identifier_scheme")
    scheme_term = IDENTIFIER_SCHEME_TERMS.get(term)
    if scheme_term:
        if not isinstance(scheme, str) or not FULL_IRI.fullmatch(scheme):
            valid = False
            issues.append(
                f"{location}: a transform for {term} requires a full-IRI "
                "identifier_scheme"
            )
        elif scheme not in registry.enum_values_by_term.get(scheme_term, frozenset()):
            valid = False
            issues.append(
                f"{location}: identifier_scheme {scheme} is not valid for {term}"
            )
    elif scheme is not None:
        valid = False
        issues.append(
            f"{location}: identifier_scheme is only valid for a scheme-bearing term"
        )

    return transform if valid else None


def _validate_source_membership(
    source_membership: Any,
    *,
    columns: tuple[str, ...],
    location: str,
    issues: list[str],
) -> None:
    if len(columns) != 1:
        issues.append(
            f"{location}: source_membership requires exactly one mapped source column"
        )
    if not isinstance(source_membership, dict):
        issues.append(f"{location}: source_membership MUST be a mapping")
        return
    missing = ALLOWED_SOURCE_MEMBERSHIP_KEYS - set(source_membership)
    extra = set(source_membership) - ALLOWED_SOURCE_MEMBERSHIP_KEYS
    if missing:
        issues.append(
            f"{location}: source_membership is missing keys {sorted(missing)}"
        )
    if extra:
        issues.append(
            f"{location}: source_membership has unknown keys {sorted(extra)}"
        )
    for key in sorted(ALLOWED_SOURCE_MEMBERSHIP_KEYS):
        value = source_membership.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                f"{location}: source_membership {key} MUST be a non-empty string"
            )


def _source_values(
    sample_input: dict[str, Any],
    *,
    columns: tuple[str, ...],
    collection: str,
) -> list[dict[str, Any]]:
    missing = [column for column in columns if column not in sample_input]
    if missing:
        raise ValueError(f"sample input is missing columns {missing}")
    if collection == "scalar":
        values = dict(sample_input)
        if len(columns) == 1:
            values["value"] = sample_input[columns[0]]
        return [values]

    if len(columns) != 1:
        raise ValueError("json-list mappings require exactly one source column")
    raw = sample_input[columns[0]]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"sample input is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("json-list sample input MUST decode to a list")
    return [
        {
            **sample_input,
            columns[0]: value,
            "value": value,
        }
        for value in raw
    ]


def _apply_transform(
    transform: dict[str, Any],
    *,
    sample_input: dict[str, Any],
    columns: tuple[str, ...],
    collection: str,
) -> Any:
    source_values = _source_values(
        sample_input,
        columns=columns,
        collection=collection,
    )
    outputs: list[Any] = []
    for values in source_values:
        if "template" in transform:
            try:
                output = transform["template"].format_map(values)
            except (KeyError, ValueError) as exc:
                raise ValueError(f"template cannot render sample: {exc}") from exc
        else:
            raw = values[columns[0]]
            if not isinstance(raw, str):
                raise ValueError("regex transform input MUST be a string")
            pattern = transform["pattern"]
            if re.fullmatch(pattern, raw) is None:
                raise ValueError(f"sample value {raw!r} does not match transform pattern")
            output = re.sub(pattern, transform["replacement"], raw)
        outputs.append(output)
    return outputs if collection == "json-list" else outputs[0]


def _valid_output_value(value: Any, value_kind: str) -> bool:
    if value_kind == "iri":
        return isinstance(value, str) and ABSOLUTE_IRI.fullmatch(value) is not None
    if value_kind == "vocab":
        return isinstance(value, str) and FULL_IRI.fullmatch(value) is not None
    if value_kind == "literal":
        return isinstance(value, str)
    if value_kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_kind == "date":
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
    return False


def _validate_samples(
    samples: Any,
    *,
    transform: dict[str, Any],
    columns: tuple[str, ...],
    collection: str,
    value_kind: str,
    location: str,
    issues: list[str],
) -> None:
    if not isinstance(samples, list) or not samples:
        issues.append(f"{location}: transform requires at least one executable sample")
        return
    for index, sample in enumerate(samples, start=1):
        sample_location = f"{location}, sample {index}"
        if not isinstance(sample, dict):
            issues.append(f"{sample_location}: sample MUST be a mapping")
            continue
        missing = ALLOWED_SAMPLE_KEYS - set(sample)
        extra = set(sample) - ALLOWED_SAMPLE_KEYS
        if missing:
            issues.append(f"{sample_location}: missing keys {sorted(missing)}")
        if extra:
            issues.append(f"{sample_location}: unknown keys {sorted(extra)}")
        sample_input = sample.get("input")
        if not isinstance(sample_input, dict):
            issues.append(f"{sample_location}: input MUST be a mapping")
            continue
        try:
            actual = _apply_transform(
                transform,
                sample_input=sample_input,
                columns=columns,
                collection=collection,
            )
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"{sample_location}: {exc}")
            continue
        expected = sample.get("output")
        if actual != expected:
            issues.append(
                f"{sample_location}: transform produced {actual!r}, expected {expected!r}"
            )
        output_values = actual if collection == "json-list" else [actual]
        if not all(_valid_output_value(value, value_kind) for value in output_values):
            issues.append(
                f"{sample_location}: transform output does not satisfy "
                f"value_kind {value_kind}"
            )


def audit_mapping_text(
    text: str,
    *,
    registry: VocabularyRegistry | None = None,
) -> MappingAudit:
    registry = registry or load_vocabulary_registry()
    blocks, issues = extract_mapping_blocks(text)
    terms: set[str] = set()
    versions: set[str] = set()
    seen_mappings: set[tuple[str, tuple[str, ...], str, str]] = set()
    entry_count = 0

    for start_line, block in blocks:
        try:
            payload = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            issues.append(f"line {start_line}: invalid mapping YAML: {exc}")
            continue
        if not isinstance(payload, dict):
            issues.append(f"line {start_line}: mapping block MUST be a YAML mapping")
            continue
        block_keys = set(payload)
        missing_block = ALLOWED_BLOCK_KEYS - block_keys
        extra_block = block_keys - ALLOWED_BLOCK_KEYS
        if missing_block:
            issues.append(f"line {start_line}: missing block keys {sorted(missing_block)}")
        if extra_block:
            issues.append(f"line {start_line}: unknown block keys {sorted(extra_block)}")

        version = payload.get("rulespec_version")
        if not isinstance(version, str) or not CONTRACT_VERSION.fullmatch(version):
            issues.append(
                f"line {start_line}: rulespec_version MUST be sha256:<64 lowercase hex>"
            )
        else:
            versions.add(version)
            if version != registry.contract_version:
                issues.append(
                    f"line {start_line}: rulespec_version {version} does not match "
                    f"the current contract {registry.contract_version}"
                )

        mappings = payload.get("mappings")
        if not isinstance(mappings, list) or not mappings:
            issues.append(f"line {start_line}: mappings MUST be a non-empty YAML list")
            continue

        for offset, entry in enumerate(mappings):
            location = f"line {start_line}, entry {offset + 1}"
            entry_count += 1
            if not isinstance(entry, dict):
                issues.append(f"{location}: entry MUST be a mapping")
                continue
            keys = set(entry)
            missing = REQUIRED_ENTRY_KEYS - keys
            extra = keys - ALLOWED_ENTRY_KEYS
            if missing:
                issues.append(f"{location}: missing keys {sorted(missing)}")
            if extra:
                issues.append(f"{location}: unknown keys {sorted(extra)}")
            if missing or extra:
                continue

            table = entry["table"]
            term = entry["term"]
            if not isinstance(table, str) or not table.strip():
                issues.append(f"{location}: table MUST be a non-empty string")
                continue
            columns = _mapping_columns(entry, location=location, issues=issues)
            if columns is None:
                continue
            mapping_key = (table, columns, str(term), str(entry["direction"]))
            if mapping_key in seen_mappings:
                issues.append(
                    f"{location}: duplicate mapping for {table}.{'+'.join(columns)} "
                    f"to {term} ({entry['direction']})"
                )
            seen_mappings.add(mapping_key)

            if not isinstance(term, str) or not FULL_IRI.fullmatch(term):
                issues.append(f"{location}: term MUST be a full HTTP(S) IRI: {term!r}")
            elif term not in registry.terms:
                issues.append(f"{location}: unregistered vocabulary term: {term}")
            else:
                terms.add(term)

            subject_type = _validate_type_iri(
                entry["subject_type"],
                key="subject_type",
                location=location,
                registry=registry,
                issues=issues,
            )
            object_type = None
            if "object_type" in entry:
                object_type = _validate_type_iri(
                    entry["object_type"],
                    key="object_type",
                    location=location,
                    registry=registry,
                    issues=issues,
                )

            direction = entry["direction"]
            if direction not in DIRECTIONS:
                issues.append(
                    f"{location}: direction MUST be one of {sorted(DIRECTIONS)}"
                )
            value_kind = entry["value_kind"]
            if value_kind not in VALUE_KINDS:
                issues.append(
                    f"{location}: value_kind MUST be one of {sorted(VALUE_KINDS)}"
                )
            elif isinstance(term, str):
                expected_kind = registry.value_kinds_by_term.get(term)
                if expected_kind and value_kind != expected_kind:
                    issues.append(
                        f"{location}: value_kind {value_kind} does not match "
                        f"the registered kind {expected_kind} for {term}"
                    )

            collection = entry.get("collection", "scalar")
            if collection not in COLLECTIONS:
                issues.append(
                    f"{location}: collection MUST be one of {sorted(COLLECTIONS)}"
                )
            elif collection == "json-list" and len(columns) != 1:
                issues.append(
                    f"{location}: json-list mappings require exactly one source column"
                )

            if isinstance(term, str) and direction in DIRECTIONS:
                domains = registry.domains_by_term.get(term, frozenset())
                range_type = registry.ranges_by_term.get(term)
                effective_domain = subject_type if direction == "forward" else object_type
                effective_range = object_type if direction == "forward" else subject_type
                if direction == "inverse" and object_type is None:
                    issues.append(f"{location}: inverse mappings require object_type")
                if domains and effective_domain and effective_domain not in domains:
                    issues.append(
                        f"{location}: {direction} mapping domain {effective_domain} "
                        f"is not valid for {term}; expected one of {sorted(domains)}"
                    )
                if range_type:
                    if effective_range is None:
                        issues.append(
                            f"{location}: {term} requires object_type {range_type}"
                        )
                    elif effective_range != range_type:
                        issues.append(
                            f"{location}: {direction} mapping range {effective_range} "
                            f"does not match {range_type} for {term}"
                        )

            enum_map = entry.get("enum_map")
            if enum_map is not None:
                _validate_enum_map(
                    enum_map,
                    term=term,
                    value_kind=value_kind,
                    location=location,
                    registry=registry,
                    issues=issues,
                )

            transform = entry.get("transform")
            samples = entry.get("samples")
            source_membership = entry.get("source_membership")
            checked_transform = None
            if source_membership is not None:
                _validate_source_membership(
                    source_membership,
                    columns=columns,
                    location=location,
                    issues=issues,
                )
            if transform is not None:
                checked_transform = _validate_transform(
                    transform,
                    term=term,
                    columns=columns,
                    collection=collection,
                    location=location,
                    registry=registry,
                    issues=issues,
                )
                if checked_transform and value_kind in VALUE_KINDS:
                    _validate_samples(
                        samples,
                        transform=checked_transform,
                        columns=columns,
                        collection=collection,
                        value_kind=value_kind,
                        location=location,
                        issues=issues,
                    )
            elif samples is not None:
                issues.append(f"{location}: samples require a transform")

            if value_kind == "iri" and transform is None and enum_map is None:
                issues.append(
                    f"{location}: IRI mappings require an executable transform and samples"
                )
            if value_kind == "vocab" and transform is None and enum_map is None:
                issues.append(
                    f"{location}: vocab mappings require enum_map or an executable transform"
                )

    return MappingAudit(
        terms=frozenset(terms),
        entries=entry_count,
        blocks=len(blocks),
        issues=tuple(issues),
        versions=frozenset(versions),
    )


def _declared_levels(document: dict[str, Any]) -> list[str]:
    levels = document.get("declared_levels")
    if isinstance(levels, list):
        return [level for level in levels if isinstance(level, str)]
    declaration = document.get("declaration")
    if isinstance(declaration, dict):
        level = declaration.get("conformance_level")
        if isinstance(level, str):
            return [level]
    return []


def _resolve_mapping_path(partner_path: Path, value: str, repo_root: Path) -> Path | None:
    raw = Path(value)
    candidates = [raw] if raw.is_absolute() else [
        partner_path.parent / raw,
        repo_root / raw,
    ]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def audit_partner(
    partner_path: Path,
    *,
    registry: VocabularyRegistry | None = None,
    repo_root: Path = ROOT,
) -> MappingAudit | None:
    registry = registry or load_vocabulary_registry()
    try:
        document = yaml.safe_load(partner_path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        return MappingAudit(frozenset(), 0, 0, (f"invalid partner YAML: {exc}",))
    if not isinstance(document, dict):
        return MappingAudit(frozenset(), 0, 0, ("partner document MUST be a mapping",))

    levels = _declared_levels(document)
    if "L0" not in levels:
        return None

    issues: list[str] = []
    if levels != ["L0"]:
        issues.append("an L0 declaration MUST NOT claim L1, L2, L3, or L4")
    declaration = document.get("declaration")
    if "adoption_depth" in document or (
        isinstance(declaration, dict) and "adoption_depth" in declaration
    ):
        issues.append(
            "an L0 declaration MUST omit adoption_depth because Appendix D "
            "does not define adoption semantics for non-JSON-LD carriers"
        )

    rulespec_version = document.get("rulespec_version")
    if (
        not isinstance(rulespec_version, str)
        or not CONTRACT_VERSION.fullmatch(rulespec_version)
    ):
        issues.append("L0 declaration requires rulespec_version: sha256:<64 lowercase hex>")
    elif rulespec_version != registry.contract_version:
        issues.append(
            f"rulespec_version {rulespec_version} does not match the current "
            f"contract {registry.contract_version}"
        )

    test_corpus_version = document.get("test_corpus_version")
    if not isinstance(test_corpus_version, str) or not test_corpus_version.strip():
        issues.append("L0 declaration requires an immutable test_corpus_version")

    carrier_mapping = document.get("carrier_mapping")
    terms_used = document.get("terms_used")
    if not isinstance(carrier_mapping, str) or not carrier_mapping:
        issues.append("L0 declaration requires carrier_mapping")
        return MappingAudit(frozenset(), 0, 0, tuple(issues))
    if not isinstance(terms_used, list) or not all(
        isinstance(term, str) for term in terms_used
    ):
        issues.append("L0 declaration requires terms_used as a list of full IRIs")
        terms_used = []

    results = document.get("results")
    if not isinstance(results, dict) or results.get("L0") != "pass":
        issues.append("L0 declaration requires results.L0: pass")

    mapping_path = _resolve_mapping_path(partner_path, carrier_mapping, repo_root)
    if mapping_path is None:
        issues.append(f"carrier_mapping does not resolve to a local file: {carrier_mapping}")
        return MappingAudit(frozenset(), 0, 0, tuple(issues))

    mapping = audit_mapping_text(mapping_path.read_text(), registry=registry)
    issues.extend(mapping.issues)
    if isinstance(rulespec_version, str) and mapping.versions != {rulespec_version}:
        issues.append(
            "every mapping block rulespec_version MUST equal the declaration "
            "rulespec_version"
        )
    declared_terms = set(terms_used)
    invalid_terms = sorted(term for term in declared_terms if not FULL_IRI.fullmatch(term))
    if invalid_terms:
        issues.append(f"terms_used entries MUST be full HTTP(S) IRIs: {invalid_terms}")
    if len(declared_terms) != len(terms_used):
        issues.append("terms_used MUST NOT contain duplicates")
    if declared_terms != set(mapping.terms):
        missing = sorted(set(mapping.terms) - declared_terms)
        extra = sorted(declared_terms - set(mapping.terms))
        if missing:
            issues.append(f"terms_used is missing mapped terms: {missing}")
        if extra:
            issues.append(f"terms_used contains unmapped terms: {extra}")

    return MappingAudit(
        mapping.terms,
        mapping.entries,
        mapping.blocks,
        tuple(issues),
        mapping.versions,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Rulespec L0 carrier mappings")
    parser.add_argument(
        "--print-contract-version",
        action="store_true",
        help="print the current CUE/context/range contract digest and exit",
    )
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    registry = load_vocabulary_registry()
    if args.print_contract_version:
        print(registry.contract_version)
        return 0
    paths = args.paths or sorted(PARTNER_DIR.glob("*.yaml"))
    failures = 0
    audited = 0

    for path in paths:
        if not path.is_file():
            print(f"[FAIL] {path}: file not found")
            failures += 1
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            result = audit_partner(path, registry=registry)
            if result is None:
                continue
        else:
            result = audit_mapping_text(path.read_text(), registry=registry)
        audited += 1
        if result.issues:
            failures += 1
            print(f"[FAIL] {path}")
            for issue in result.issues:
                print(f"  - {issue}")
        else:
            print(
                f"[PASS] {path}: {result.blocks} block(s), "
                f"{result.entries} mapping(s), {len(result.terms)} term(s)"
            )

    print(f"L0 mapping audit: {audited - failures}/{audited} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
