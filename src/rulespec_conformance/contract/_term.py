"""The rkaf term type the generated registry is written in.

Hand-authored, and the only place the namespace IRI is spelled in Python.
`tools/build_contract_exports.py` refuses to write the registry when
`RKAF_NAMESPACE` disagrees with the `rkaf` prefix in
`context/rkaf-context.jsonld`, and `tools/test_contract_exports.py` asserts the
same equality, so the copy cannot outlive the source it copies.
"""

from __future__ import annotations

RKAF_NAMESPACE = "https://rulespec.org/ns/v1#"

_PREFIX = "rkaf:"


class Term(str):
    """A compact rkaf IRI that also knows its expanded form.

    A plain `str` subclass on purpose: every consumer that already writes
    `"rkaf:Artifact"` into a JSON-LD document, a SPARQL string, or a test
    fixture keeps working unchanged — `json.dumps`, `==`, dict keys and
    f-strings all see the compact IRI. `.iri` is here so that expanding one is
    not string surgery at the call site, which is where the two spellings
    drift apart.
    """

    __slots__ = ()

    @property
    def local(self) -> str:
        """The local name, without the `rkaf:` prefix."""
        return self[len(_PREFIX) :]

    @property
    def iri(self) -> str:
        """The absolute IRI this compact form abbreviates."""
        return RKAF_NAMESPACE + self.local

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Term({str.__repr__(self)})"
