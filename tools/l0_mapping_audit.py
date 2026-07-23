#!/usr/bin/env python3
"""Audit Rulespec L0 carrier mappings and self-certifications.

An L0 mapping is one or more fenced ``yaml rkaf-l0-mapping`` blocks. Each
block contains a YAML list of ``table``, ``column``, ``term``, and optional
``enum_map`` entries. Terms and enum targets use full IRIs.

With no arguments, this tool discovers L0 declarations under
``conformance/partners``. A Markdown argument audits a mapping directly; a
YAML argument audits an L0 partner declaration and its referenced mapping.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    from constraints_compile import ConstraintDoc, parse_cue_file
except ModuleNotFoundError:  # Imported as tools.l0_mapping_audit in unit tests.
    from tools.constraints_compile import ConstraintDoc, parse_cue_file

ROOT = Path(__file__).resolve().parent.parent
CUE_DIR = ROOT / "constraints" / "core"
CONTEXT_PATH = ROOT / "context" / "rkaf-context.jsonld"
PARTNER_DIR = ROOT / "conformance" / "partners"

FENCE_START = re.compile(r"^```yaml[ \t]+rkaf-l0-mapping[ \t]*$")
FENCE_END = re.compile(r"^```[ \t]*$")
FULL_IRI = re.compile(r"^https?://[^\s]+$")
ALLOWED_ENTRY_KEYS = {"table", "column", "term", "enum_map"}
REQUIRED_ENTRY_KEYS = {"table", "column", "term"}


@dataclass(frozen=True)
class VocabularyRegistry:
    terms: frozenset[str]
    enum_values: frozenset[str]
    enum_values_by_term: dict[str, frozenset[str]]


@dataclass(frozen=True)
class MappingAudit:
    terms: frozenset[str]
    entries: int
    blocks: int
    issues: tuple[str, ...]


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


def load_vocabulary_registry(
    *,
    cue_dir: Path = CUE_DIR,
    context_path: Path = CONTEXT_PATH,
) -> VocabularyRegistry:
    context_doc = json.loads(context_path.read_text())
    context = context_doc["@context"]
    prefixes = {
        key: value
        for key, value in context.items()
        if ":" not in key and isinstance(value, str)
    }
    docs = [parse_cue_file(path) for path in sorted(cue_dir.glob("*.cue"))]
    enums = _enum_registry(docs)

    terms: set[str] = set()
    for key in context:
        if ":" in key:
            terms.add(_expand(key, prefixes))

    values_by_term: dict[str, set[str]] = {}
    for doc in docs:
        for shape in doc.shapes:
            if shape.type_iri:
                terms.add(_expand(shape.type_iri, prefixes))
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

    all_enum_values = {
        _expand(value, prefixes)
        for values in enums.values()
        for value in values
    }
    return VocabularyRegistry(
        terms=frozenset(terms),
        enum_values=frozenset(all_enum_values),
        enum_values_by_term={
            term: frozenset(values) for term, values in values_by_term.items()
        },
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


def audit_mapping_text(
    text: str,
    *,
    registry: VocabularyRegistry | None = None,
) -> MappingAudit:
    registry = registry or load_vocabulary_registry()
    blocks, issues = extract_mapping_blocks(text)
    terms: set[str] = set()
    seen_columns: set[tuple[str, str]] = set()
    entry_count = 0

    for start_line, block in blocks:
        try:
            payload = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            issues.append(f"line {start_line}: invalid mapping YAML: {exc}")
            continue
        if not isinstance(payload, list) or not payload:
            issues.append(f"line {start_line}: mapping block MUST be a non-empty YAML list")
            continue

        for offset, entry in enumerate(payload):
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
            column = entry["column"]
            term = entry["term"]
            if not all(isinstance(value, str) and value.strip() for value in (table, column, term)):
                issues.append(f"{location}: table, column, and term MUST be non-empty strings")
                continue
            column_key = (table, column)
            if column_key in seen_columns:
                issues.append(f"{location}: duplicate mapping for {table}.{column}")
            seen_columns.add(column_key)

            if not FULL_IRI.fullmatch(term):
                issues.append(f"{location}: term MUST be a full HTTP(S) IRI: {term!r}")
            elif term not in registry.terms:
                issues.append(f"{location}: unregistered vocabulary term: {term}")
            else:
                terms.add(term)

            enum_map = entry.get("enum_map")
            if enum_map is None:
                continue
            if not isinstance(enum_map, dict) or not enum_map:
                issues.append(f"{location}: enum_map MUST be a non-empty mapping")
                continue
            allowed = registry.enum_values_by_term.get(term)
            if allowed is None:
                issues.append(f"{location}: enum_map is only valid for a closed-enum term")
                continue
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
                    issues.append(
                        f"{location}: enum target {target} is not valid for term {term}"
                    )

    return MappingAudit(
        terms=frozenset(terms),
        entries=entry_count,
        blocks=len(blocks),
        issues=tuple(issues),
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

    return MappingAudit(mapping.terms, mapping.entries, mapping.blocks, tuple(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Rulespec L0 carrier mappings")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    registry = load_vocabulary_registry()
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
