"""Installed specification and common fixture corpus."""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from ._artifact import parse_canonical_json


def _data() -> Traversable:
    packaged = resources.files("rulespec_artifacts") / "_data"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[4]


def platform_artifact_spec() -> str:
    return (_data() / "spec" / "platform-artifacts.md").read_text(encoding="utf-8")


def fixture_corpus() -> dict[str, object]:
    value = json.loads(
        (_data() / "platform-fixtures" / "corpus.json").read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise TypeError("platform fixture corpus must be a JSON object")
    return value


def canonical_json_corpus() -> dict[str, object]:
    """Return the byte-exact canonical-JSON encoder corpus shipped in the wheel."""

    raw = (_data() / "platform-fixtures" / "canonical-json" / "corpus.json").read_bytes()
    value = parse_canonical_json(raw)
    if not isinstance(value, dict):
        raise TypeError("canonical-JSON fixture corpus must be a JSON object")
    return value


def fixture(name: str) -> Traversable:
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise ValueError("fixture name must be one path segment")
    target = _data() / "platform-fixtures" / "cases" / name
    if not target.is_dir():
        raise FileNotFoundError(name)
    return target
