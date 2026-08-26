"""The packaged contract data, addressed through `importlib.resources`.

The wheel carries the compiled JSON Schemas, the compiled SHACL, the
hand-authored SHACL suite, the JSON-LD context and `VERSION` under
`rulespec_conformance/_data/` (see the force-include table in
`pyproject.toml`). Consumers reach them through the functions here rather than
by constructing paths: a path built from `__file__` guesses at a layout the
build backend owns, and it guessed wrong the moment the data moved into
`_data/`.

`DATA_ROOT` falls back to the repository root when `_data/` is absent, which is
exactly the source-tree case — `compiled/` is gitignored and generated, so the
repository has no `_data/` to package until `make compile` has run. This is the
same rule `rulespec_conformance.conformance_lib.ROOT` applies; that one stays
`Path`-typed because pyshacl and rdflib are handed real filesystem paths and
517 fixtures resolve `../context/rkaf-context.jsonld` relative to themselves.
Here the type is `Traversable`, which is what `importlib.resources` returns.
"""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

# this file -> contract -> rulespec_conformance -> src -> repository root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGED = resources.files("rulespec_conformance") / "_data"

DATA_ROOT: Traversable = _PACKAGED if _PACKAGED.is_dir() else _REPO_ROOT

#: Every sub-tree of compiled output the wheel carries, by the sub-path the
#: compiler writes it to (`tools/compile_all.sh`). A family is a path segment,
#: never a guess: `json_schema("rulemaking", family="profiles/us-rulemaking")`.
COMPILED_TARGETS: tuple[str, ...] = ("json-schema", "rego", "shacl", "typescript")

CONTEXT_FILE = "context/rkaf-context.jsonld"


def _segments(*parts: str) -> tuple[str, ...]:
    """Split `parts` into path segments, refusing anything that walks out.

    The packaged data is a closed set. `..` or an absolute segment would leave
    it, and on a zip-imported package it would not resolve at all, so it is a
    caller error rather than a lookup that happens to work in a checkout.
    """
    segments: list[str] = []
    for part in parts:
        text = str(part)
        if text.startswith("/"):
            raise ValueError(f"resource path is absolute: {part!r}")
        for segment in text.split("/"):
            if not segment or segment == ".":
                continue
            if segment == "..":
                raise ValueError(f"resource path escapes the packaged data: {part!r}")
            segments.append(segment)
    if not segments:
        raise ValueError("no resource path given")
    return tuple(segments)


def resource(*parts: str) -> Traversable:
    """The `Traversable` for a packaged file, whether or not it exists."""
    target = DATA_ROOT
    for segment in _segments(*parts):
        target = target / segment
    return target


def _require(*parts: str) -> Traversable:
    target = resource(*parts)
    if not target.is_file():
        raise FileNotFoundError(
            f"{'/'.join(_segments(*parts))} is not packaged with this "
            f"Rulespec contract (data root: {DATA_ROOT})"
        )
    return target


def read_text(*parts: str) -> str:
    """The UTF-8 text of a packaged file."""
    return _require(*parts).read_text(encoding="utf-8")


def read_json(*parts: str) -> Any:
    """The parsed JSON of a packaged file."""
    return json.loads(read_text(*parts))


def _names(directory: Traversable, suffix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            entry.name[: -len(suffix)]
            for entry in directory.iterdir()
            if entry.is_file() and entry.name.endswith(suffix)
        )
    )


def version() -> str:
    """The Rulespec version this contract was cut from (`VERSION`)."""
    return read_text("VERSION").strip()


def context() -> dict[str, Any]:
    """The JSON-LD context document (`context/rkaf-context.jsonld`)."""
    return read_json(CONTEXT_FILE)


def platform_artifact_spec() -> str:
    """The normative platform artifact 1.0 specification."""

    from rulespec_artifacts.resources import platform_artifact_spec as read_spec

    return read_spec()


def platform_artifact_fixture_corpus() -> dict[str, Any]:
    """The packaged common structural fixture-corpus index."""

    from rulespec_artifacts.resources import fixture_corpus

    return fixture_corpus()


def platform_artifact_fixture(name: str) -> Traversable:
    """One packaged fixture artifact directory named by the corpus index."""

    from rulespec_artifacts.resources import fixture

    return fixture(name)


def json_schema(name: str, *, family: str = "core") -> dict[str, Any]:
    """A compiled Draft 2020-12 schema, e.g. `json_schema("artifact")`."""
    return read_json("compiled/json-schema", family, f"{name}.schema.json")


def json_schema_names(family: str = "core") -> tuple[str, ...]:
    """Every compiled schema in `family`, without the `.schema.json` suffix."""
    return _names(resource("compiled/json-schema", family), ".schema.json")


def shacl(name: str, *, family: str = "core") -> str:
    """The compiled SHACL Turtle for one primitive, e.g. `shacl("warrant")`."""
    return read_text("compiled/shacl", family, f"{name}.ttl")


def shacl_names(family: str = "core") -> tuple[str, ...]:
    """Every compiled SHACL file in `family`, without the `.ttl` suffix."""
    return _names(resource("compiled/shacl", family), ".ttl")


def shapes(name: str) -> str:
    """A hand-authored shape file's Turtle, e.g. `shapes("rkaf-shapes-core")`.

    The compiled SHACL and this suite are not alternatives: the compiler emits
    what CUE can express, and `shapes/` carries the Pattern C conditionals and
    cross-node constraints it cannot. A consumer validating rkaf data loads
    both.
    """
    return read_text("shapes", f"{name}.ttl")


def shape_names() -> tuple[str, ...]:
    """Every hand-authored shape file, without the `.ttl` suffix."""
    return _names(resource("shapes"), ".ttl")
