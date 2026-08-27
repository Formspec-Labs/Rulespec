#!/usr/bin/env python3
"""Run the shared canonical-JSON corpus against one installed artifact package."""

from __future__ import annotations

import argparse
import json
import math
from importlib.metadata import version
from pathlib import Path

from rulespec_artifacts import (
    ArtifactVerificationError,
    canonical_json_bytes,
    parse_canonical_json,
    resources,
)


class CorpusError(AssertionError):
    """Report one golden-corpus mismatch."""


def _case_list(corpus: dict[str, object], key: str) -> list[dict[str, object]]:
    value = corpus.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise CorpusError(f"{key} must be an array of objects")
    return value


def _case_name(case: dict[str, object], *, section: str) -> str:
    name = case.get("name")
    if not isinstance(name, str) or not name:
        raise CorpusError(f"{section} case name must be nonempty text")
    return name


def _materialize_input(description: object) -> object:
    if not isinstance(description, dict):
        raise CorpusError("rejected encoder input must be an object")
    kind = description.get("kind")
    if kind == "integer":
        return int(str(description.get("literal")))
    if kind == "float":
        literal = description.get("literal")
        if literal == "nan":
            return math.nan
        if literal == "inf":
            return math.inf
        if literal == "-inf":
            return -math.inf
        return float(str(literal))
    if kind in {"lone-surrogate-string", "lone-surrogate-key"}:
        code_unit = description.get("codeUnit")
        if not isinstance(code_unit, str):
            raise CorpusError(f"{kind} requires a hexadecimal codeUnit")
        value = chr(int(code_unit, 16))
        return {value: "value"} if kind == "lone-surrogate-key" else value
    if kind == "non-string-key":
        return {1: "value"}
    if kind == "bytes":
        return b"value"
    raise CorpusError(f"unknown rejected encoder input kind: {kind!r}")


def evaluate_corpus(corpus: dict[str, object]) -> dict[str, object]:
    """Return stable observations after enforcing every golden expectation."""

    if corpus.get("format") != "rulespec-canonical-json-golden-corpus":
        raise CorpusError("unknown canonical-JSON corpus format")
    if corpus.get("formatVersion") != "1.0":
        raise CorpusError("unknown canonical-JSON corpus format version")

    names: set[str] = set()
    accepted_results: list[dict[str, str]] = []
    for case in _case_list(corpus, "encodeAccepted"):
        name = _case_name(case, section="encodeAccepted")
        if name in names:
            raise CorpusError(f"duplicate corpus case name: {name}")
        names.add(name)
        expected_hex = case.get("canonicalHex")
        if not isinstance(expected_hex, str):
            raise CorpusError(f"{name}: canonicalHex must be text")
        expected = bytes.fromhex(expected_hex)
        actual = canonical_json_bytes(case.get("value"))
        if actual != expected:
            raise CorpusError(
                f"{name}: encoded {actual.hex()} instead of golden {expected_hex}"
            )
        if parse_canonical_json(expected) != case.get("value"):
            raise CorpusError(f"{name}: canonical bytes did not parse to their value")
        accepted_results.append({"canonicalHex": actual.hex(), "name": name})

    rejected_results: list[dict[str, str]] = []
    for case in _case_list(corpus, "encodeRejected"):
        name = _case_name(case, section="encodeRejected")
        if name in names:
            raise CorpusError(f"duplicate corpus case name: {name}")
        names.add(name)
        try:
            canonical_json_bytes(_materialize_input(case.get("input")))
        except ArtifactVerificationError:
            rejected_results.append({"name": name, "status": "rejected"})
        else:
            raise CorpusError(f"{name}: encoder admitted a forbidden value")

    parse_results: list[dict[str, str]] = []
    for case in _case_list(corpus, "parseRejected"):
        name = _case_name(case, section="parseRejected")
        qualified_name = f"parse:{name}"
        if qualified_name in names:
            raise CorpusError(f"duplicate corpus case name: {qualified_name}")
        names.add(qualified_name)
        raw_hex = case.get("utf8Hex")
        if not isinstance(raw_hex, str):
            raise CorpusError(f"{name}: utf8Hex must be text")
        try:
            parse_canonical_json(bytes.fromhex(raw_hex))
        except ArtifactVerificationError:
            parse_results.append({"name": name, "status": "rejected"})
        else:
            raise CorpusError(f"{name}: parser admitted forbidden bytes")

    return {
        "encodeAccepted": accepted_results,
        "encodeRejected": rejected_results,
        "format": str(corpus["format"]),
        "formatVersion": str(corpus["formatVersion"]),
        "parseRejected": parse_results,
    }


def _load_corpus(path: Path | None) -> dict[str, object]:
    if path is None:
        return resources.canonical_json_corpus()
    value = parse_canonical_json(path.read_bytes())
    if not isinstance(value, dict):
        raise CorpusError("canonical-JSON corpus must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    observations = evaluate_corpus(_load_corpus(args.corpus))
    report = {"packageVersion": version("rulespec-artifacts"), **observations}
    if args.json:
        print(json.dumps(report, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    else:
        total = sum(
            len(observations[key])
            for key in ("encodeAccepted", "encodeRejected", "parseRejected")
        )
        print(f"rulespec-artifacts {report['packageVersion']}: {total} canonical cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
