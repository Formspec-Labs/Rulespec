#!/usr/bin/env python3
"""Deterministic generator for the packaged rkaf contract exports.

Writes two modules of the `rulespec-conformance` distribution:

  src/rulespec_conformance/contract/enums.py  — every closed enum and lattice
      CUE declares, as tuples in CUE declaration order.
  src/rulespec_conformance/contract/terms.py  — every rkaf term Rulespec
      declares, as module attributes.

Both are tracked, for the same reason `crates/rkaf-core/src/generated/` is
tracked and `compiled/` is not: they are importable source, and a consumer
installing the wheel must not need a CUE toolchain to get them. `--check`
is the gate that keeps them in lock-step with the sources below.

Why generate them at all: a downstream that spells `rkaf:assignedConcept`
today gets a string that validates as a string and fails at the far end of a
pipeline. Against `terms.py` it is an ImportError at the first import, and
`assignedConcept` in particular is a term Rulespec retired — `shapes/`
holds it at `sh:maxCount 0`.

Enums come from the CUE through `tools/constraints_compile.py`'s own parser,
so this generator adds no second reading of the source of truth. Enum unions
(`#WarrantKind: #WarrantKindLegal | #WarrantKindScientific | ...`) are
flattened against a registry of every enum in the tree, in reference order,
first occurrence winning.

TERM SOURCES, and why each one:

  constraints/**/*.cue            The contract. Comments are stripped: a
                                  comment naming `rkaf:consent` is the
                                  adversarial suite explaining what is NOT a
                                  term (`constraints/ai-extraction/`).
  context/rkaf-context.jsonld     The `@context` keys. Only terms needing
                                  JSON-LD coercion appear, so it is a source
                                  and never a completeness check.
  spec/rkaf-vocabulary.md         The normative term table. `tools/vocab_audit.py`
                                  already fails the build when a compiled CUE
                                  class is missing from it, so the two move
                                  together.
  spec/rkaf-behavior.md           The L4 `BehaviorTestCase` wire format, which
                                  has no CUE at all — its carrier is prose plus
                                  the Rust runtime.
  crates/rkaf-runtime/src/*.rs    The rest of that L4 vocabulary
                                  (`rkaf:behaviorContract`, `rkaf:input`,
                                  `rkaf:expectedRuntimeError`, the runtime
                                  error IRIs). Read up to the first
                                  `#[cfg(test)]`: the test modules mint
                                  `rkaf:WhateverNotARealContract` on purpose.

DELIBERATELY NOT SOURCES:

  shapes/*.ttl                    Carries retired terms at `sh:maxCount 0`
                                  (the concept-assignment shadow fields) and
                                  `*Shape` node names, which are shape
                                  identifiers, not data vocabulary.
  fixtures/**                     The negative corpus invents non-terms as its
                                  whole purpose (`rkaf:proceedingBogus`), and
                                  even a positive fixture may carry a retired
                                  field to prove a shape rejects it.
  spec/rkaf-core.md and the rest  They narrate history, including the renames
                                  that retired the shadow fields above.
  compiled/**                     A projection of the CUE, not a source; also
                                  gitignored, so it is absent from a fresh
                                  clone.

Usage:
  python3 tools/build_contract_exports.py            # rewrite both modules
  python3 tools/build_contract_exports.py --check    # drift gate

Exit codes:
  0  modules match their sources (or --write succeeded)
  1  drift detected (--check), or a collision the exports cannot carry
  2  setup error (a source is missing, the CUE parser failed)
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import constraints_compile as cc  # noqa: E402

from rulespec_conformance.contract._term import RKAF_NAMESPACE  # noqa: E402

CONTRACT_DIR = ROOT / "src" / "rulespec_conformance" / "contract"
ENUMS_MODULE = CONTRACT_DIR / "enums.py"
TERMS_MODULE = CONTRACT_DIR / "terms.py"

CONSTRAINTS_DIR = ROOT / "constraints"
CONTEXT_FILE = ROOT / "context" / "rkaf-context.jsonld"
VOCABULARY_DOC = ROOT / "spec" / "rkaf-vocabulary.md"
BEHAVIOR_DOC = ROOT / "spec" / "rkaf-behavior.md"
RUNTIME_SRC = ROOT / "crates" / "rkaf-runtime" / "src"

# `(?<!urn:)` keeps Rulespec's own URN identifiers (`urn:rkaf:us:cfr:...`) from
# reading as compact IRIs; `us` and `cfr` are not terms.
COMPACT_IRI = re.compile(r"(?<!urn:)\brkaf:([A-Za-z][A-Za-z0-9_-]*)")

GENERATED_HEADER = "# GENERATED by tools/build_contract_exports.py — do not edit."

# Emitted verbatim at the end of terms.py. A module-level `__getattr__` runs
# only for names the module does not define, so this changes nothing about a
# real term and turns an unknown one into a sentence instead of a bare
# AttributeError.
UNKNOWN_TERM_GUARD = '''def __getattr__(name: str) -> Term:
    """Refuse any name that is not a term Rulespec declares."""
    raise AttributeError(
        f"'rkaf:{name}' is not a term this Rulespec contract declares "
        f"({len(TERMS)} terms). A term that was renamed, retired, or never "
        "minted fails here rather than reaching the wire."
    )
'''


class BuildError(Exception):
    """A collision or inconsistency the generated modules cannot carry."""


# ---- source reading ------------------------------------------------------


def strip_cue_comments(text: str) -> str:
    """CUE source with `//` line comments removed, string literals intact.

    A naive `line.split("//")` would also cut `=~"^https://..."` in half and
    silently drop every term after it on that line. CUE has no block comment,
    so tracking the double-quoted string state per line is the whole job.
    """
    stripped: list[str] = []
    for line in text.splitlines():
        kept: list[str] = []
        in_string = False
        escaped = False
        index = 0
        while index < len(line):
            char = line[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "/" and line[index + 1 : index + 2] == "/":
                break
            kept.append(char)
            index += 1
        stripped.append("".join(kept))
    return "\n".join(stripped)


def truncate_at_rust_tests(text: str) -> str:
    """Rust source up to its first `#[cfg(test)]` attribute."""
    marker = text.find("#[cfg(test)]")
    return text if marker < 0 else text[:marker]


def cue_files() -> list[Path]:
    return sorted(CONSTRAINTS_DIR.rglob("*.cue"))


def term_sources() -> list[tuple[str, str]]:
    """(repository-relative label, text) for every declared term source."""
    sources: list[tuple[str, str]] = []
    for path in cue_files():
        sources.append(
            (
                str(path.relative_to(ROOT)),
                strip_cue_comments(path.read_text(encoding="utf-8")),
            )
        )
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
    sources.append(
        (
            str(CONTEXT_FILE.relative_to(ROOT)),
            "\n".join(key for key in context["@context"] if key.startswith("rkaf:")),
        )
    )
    for doc in (VOCABULARY_DOC, BEHAVIOR_DOC):
        sources.append((str(doc.relative_to(ROOT)), doc.read_text(encoding="utf-8")))
    for path in sorted(RUNTIME_SRC.glob("*.rs")):
        sources.append(
            (
                str(path.relative_to(ROOT)),
                truncate_at_rust_tests(path.read_text(encoding="utf-8")),
            )
        )
    return sources


def scan_terms() -> dict[str, tuple[str, ...]]:
    """Every declared rkaf term, mapped to the sources that declare it."""
    found: dict[str, list[str]] = {}
    for label, text in term_sources():
        for local_name in COMPACT_IRI.findall(text):
            declared_in = found.setdefault(local_name, [])
            if label not in declared_in:
                declared_in.append(label)
    return {name: tuple(labels) for name, labels in sorted(found.items())}


# ---- enums ---------------------------------------------------------------


def collect_enums() -> dict[str, tuple[str, tuple[str, ...]]]:
    """CUE enum name → (source relpath, values in declaration order).

    Unions are flattened here rather than left as references: a consumer
    checking membership of `#WarrantKind` needs the members, and resolving
    them at every call site is how six families become five.
    """
    values: dict[str, tuple[str, ...]] = {}
    origins: dict[str, str] = {}
    unions: dict[str, tuple[str, ...]] = {}
    for path in cue_files():
        relpath = str(path.relative_to(ROOT))
        # `resolve_composition=False`: composition resolves SHAPES, and an
        # enum's values are already complete without it. It is off so that a
        # shape the compiler cannot compose never blocks the enum export.
        doc = cc.parse_cue_file(path, resolve_composition=False)
        for enum in doc.enums:
            if enum.name in origins:
                raise BuildError(
                    f"enum #{enum.name} is declared twice: "
                    f"{origins[enum.name]} and {relpath}"
                )
            origins[enum.name] = relpath
            values[enum.name] = tuple(enum.values)
        for union in doc.enum_unions:
            if union.name in origins:
                raise BuildError(
                    f"enum #{union.name} is declared twice: "
                    f"{origins[union.name]} and {relpath}"
                )
            origins[union.name] = relpath
            unions[union.name] = tuple(union.refs)

    def flatten(name: str, seen: tuple[str, ...] = ()) -> tuple[str, ...]:
        if name in values:
            return values[name]
        if name in seen:
            raise BuildError(f"enum union #{name} references itself: {' -> '.join(seen)}")
        if name not in unions:
            raise BuildError(f"enum union references #{name}, which is not declared")
        flattened: list[str] = []
        for ref in unions[name]:
            for value in flatten(ref, (*seen, name)):
                if value not in flattened:
                    flattened.append(value)
        return tuple(flattened)

    for name in unions:
        values[name] = flatten(name)
    return {name: (origins[name], values[name]) for name in sorted(values)}


def constant_name(cue_name: str) -> str:
    """`UsageEligibility` → `USAGE_ELIGIBILITY`, `AIUsage` → `AI_USAGE`."""
    return re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", cue_name
    ).upper()


def attribute_name(term: str) -> str:
    """`us-cfr` → `us_cfr`. Rulespec spells some enum members in kebab case."""
    return term.replace("-", "_")


# ---- rendering -----------------------------------------------------------


def render_enums(enums: dict[str, tuple[str, tuple[str, ...]]]) -> str:
    by_constant: dict[str, str] = {}
    for cue_name in enums:
        constant = constant_name(cue_name)
        if constant in by_constant:
            raise BuildError(
                f"#{cue_name} and #{by_constant[constant]} both render as {constant}"
            )
        if not constant.isidentifier() or keyword.iskeyword(constant):
            raise BuildError(f"#{cue_name} renders as {constant}, not a Python name")
        by_constant[constant] = cue_name

    lines = [
        GENERATED_HEADER,
        "#",
        "# Source: constraints/**/*.cue, read through tools/constraints_compile.py.",
        '"""Every closed enum and lattice the Rulespec CUE declares.',
        "",
        "Each constant is the enum's members as a tuple in CUE DECLARATION ORDER,",
        "which is the order the compiled JSON Schema `enum` arrays carry and the",
        "order `#UsageEligibility` calls normative: usage eligibility ascends from",
        "`rkaf:notEligible` to `rkaf:officialUse`, consumers MAY narrow and MUST NOT",
        "broaden, and every floor/ceiling comparison downstream is a rank against",
        "this tuple. Where a CUE comment does not call order normative, membership is",
        "the contract and the order is simply the source's.",
        "",
        "Values are the literal wire strings, prefix and all — most are `rkaf:`, but",
        "`#SelectorKind` carries `oa:`, `#SkosMappingPredicate` carries `skos:`, and",
        "`#ValueDatatype` carries `xsd:`.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for constant, cue_name in sorted(by_constant.items()):
        relpath, values = enums[cue_name]
        lines.append(f"#: `#{cue_name}` — {relpath}")
        lines.append(f"{constant}: tuple[str, ...] = (")
        lines.extend(f'    "{value}",' for value in values)
        lines.append(")")
        lines.append("")

    lines.append("#: Every enum by its CUE definition name.")
    lines.append("ENUMS: dict[str, tuple[str, ...]] = {")
    lines.extend(
        f'    "{cue_name}": {constant_name(cue_name)},' for cue_name in enums
    )
    lines.append("}")
    lines.append("")
    lines.append("#: Where each enum is declared, for the consumer that has to go read it.")
    lines.append("ENUM_SOURCES: dict[str, str] = {")
    lines.extend(f'    "{cue_name}": "{relpath}",' for cue_name, (relpath, _) in enums.items())
    lines.append("}")
    lines.append("")
    lines.append('__all__ = [')
    lines.append('    "ENUMS",')
    lines.append('    "ENUM_SOURCES",')
    lines.extend(f'    "{constant}",' for constant in sorted(by_constant))
    lines.append("]")
    return "\n".join(lines) + "\n"


def render_terms(terms: dict[str, tuple[str, ...]]) -> str:
    by_attribute: dict[str, str] = {}
    for term in terms:
        attribute = attribute_name(term)
        if attribute in by_attribute:
            raise BuildError(
                f"rkaf:{term} and rkaf:{by_attribute[attribute]} both render "
                f"as {attribute}"
            )
        if not attribute.isidentifier() or keyword.iskeyword(attribute):
            raise BuildError(f"rkaf:{term} renders as {attribute}, not a Python name")
        by_attribute[attribute] = term

    lines = [
        GENERATED_HEADER,
        "#",
        "# Sources are listed in tools/build_contract_exports.py, which also records",
        "# what is deliberately not a source and why.",
        '"""Every rkaf term Rulespec declares, as an attribute of this module.',
        "",
        "    from rulespec_conformance.contract.terms import hasContentDigest",
        "",
        "An unknown name — a rename not followed, a term retired, a typo — is an",
        "ImportError or an AttributeError at import time, not a string that",
        "validates as a string and fails at the far end of a pipeline. That is the",
        "whole point of the module: the check is the import.",
        "",
        "Attribute names are the term's local name, with `-` written `_`:",
        "`rkaf:us-cfr` is `us_cfr`. The VALUE is always the exact compact IRI, and",
        "it is a `Term`, so `.iri` expands it and everything else treats it as the",
        "`str` it is.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from ._term import RKAF_NAMESPACE as RKAF_NAMESPACE",
        "from ._term import Term as Term",
        "",
    ]
    for attribute, term in sorted(by_attribute.items()):
        lines.append(f'{attribute} = Term("rkaf:{term}")')
    lines.append("")
    lines.append("_TERM_NAMES: tuple[str, ...] = (")
    lines.extend(f'    "{attribute}",' for attribute in sorted(by_attribute))
    lines.append(")")
    lines.append("")
    lines.append("#: Every declared term as its compact IRI. Derived from the attributes")
    lines.append("#: above, so the set and the module cannot disagree.")
    lines.append(
        "TERMS: frozenset[Term] = frozenset(globals()[_name] for _name in _TERM_NAMES)"
    )
    lines.append("")
    lines.append('__all__ = ["RKAF_NAMESPACE", "TERMS", "Term", *_TERM_NAMES]')
    lines.append("")
    lines.append("")
    lines.append(UNKNOWN_TERM_GUARD)
    return "\n".join(lines) + "\n"


# ---- entry point ---------------------------------------------------------


def build() -> dict[Path, str]:
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
    declared_namespace = context["@context"]["rkaf"]
    if declared_namespace != RKAF_NAMESPACE:
        raise BuildError(
            f"_term.RKAF_NAMESPACE is {RKAF_NAMESPACE!r} but "
            f"{CONTEXT_FILE.relative_to(ROOT)} declares {declared_namespace!r}"
        )
    return {
        ENUMS_MODULE: render_enums(collect_enums()),
        TERMS_MODULE: render_terms(scan_terms()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and fail on any drift from the tracked modules",
    )
    args = parser.parse_args(argv)

    for path in (CONSTRAINTS_DIR, CONTEXT_FILE, VOCABULARY_DOC, BEHAVIOR_DOC, RUNTIME_SRC):
        if not path.exists():
            print(f"setup: {path.relative_to(ROOT)} missing", file=sys.stderr)
            return 2

    try:
        rendered = build()
    except BuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except cc.CompileError as error:  # pragma: no cover - a broken CUE tree
        print(f"setup: CUE parse failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        drift = [
            path
            for path, text in rendered.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        if drift:
            print(
                "DRIFT: "
                + ", ".join(str(path.relative_to(ROOT)) for path in sorted(drift))
                + " does not match its sources"
            )
            print("Resolution: run tools/build_contract_exports.py and review the diff.")
            return 1
        print("contract exports match their sources")
        return 0

    for path, text in rendered.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
