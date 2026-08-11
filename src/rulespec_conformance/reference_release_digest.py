#!/usr/bin/env python3
"""Compute and verify a Rulespec ReferenceResourceRelease digest.

The digest preimage is the closed semantic-manifest dataset defined by
spec/rkaf-core.md: every allowed triple whose subject is the release, except
rkaf:referenceReleaseDigest itself, plus each dcat:distribution Artifact's
identifier, media type, and byte digest. The selected RDF dataset is normalized
with RDF Dataset Canonicalization 1.0 (RDFC-1.0), encoded as UTF-8 canonical
N-Quads, and hashed with SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from rdfcanon import RDFCanon, RDFCanonTimeTicker
from rdflib import (
    DCAT,
    DCTERMS,
    PROV,
    RDF,
    XSD,
    Dataset,
    Graph,
    Literal,
    Namespace,
    URIRef,
)
from rdflib.term import Identifier

RKAF = Namespace("https://rulespec.org/ns/v1#")
DCAT_VERSION = URIRef("http://www.w3.org/ns/dcat#version")

RELEASE_PREDICATES = frozenset(
    {
        RDF.type,
        DCTERMS.isVersionOf,
        DCAT_VERSION,
        DCTERMS.type,
        RKAF.membershipMode,
        PROV.hadMember,
        DCAT.distribution,
        RKAF.versionBasis,
        DCTERMS.issued,
        RKAF.hasEffectivePeriod,
    }
)
DIST_PREDICATES = frozenset(
    {
        RKAF.hasArtifactIdentifier,
        DCTERMS.format,
        RKAF.hasContentDigest,
    }
)


class ReleaseDigestError(ValueError):
    """The release graph cannot produce the normative digest preimage."""


def _rdfc_term(term):
    """Normalize rdflib's explicit xsd:string carrier for canonical N-Quads.

    RDFC-1.0 Appendix A requires an xsd:string literal to serialize without
    the datatype IRI. rdflib preserves the same RDF term with an explicit
    datatype after JSON-LD expansion, while rdfcanon delegates serialization
    to rdflib. Rebuilding that one term as a simple Literal produces the
    required canonical spelling without changing its RDF meaning.
    """
    if isinstance(term, Literal) and term.datatype == XSD.string:
        return Literal(str(term))
    return term


def canonical_preimage(graph: Graph, release: URIRef) -> str:
    """Return the RDFC-1.0 canonical N-Quads digest preimage.

    `rdfcanon==1.0.0` is pinned because that implementation passes the W3C
    RDFC-1.0 implementation-report suite. The selected manifest contains no
    blank-node subjects or distributions, but using the conforming
    implementation also fixes canonical literal escaping and keeps the
    verifier correct if the closed graph evolves.
    """
    if (release, RDF.type, RKAF.ReferenceResourceRelease) not in graph:
        raise ReleaseDigestError(f"{release} is not a ReferenceResourceRelease")

    dataset = Dataset()
    for predicate in RELEASE_PREDICATES:
        for object_ in graph.objects(release, predicate):
            dataset.add((release, predicate, _rdfc_term(object_)))

    distributions = list(graph.objects(release, DCAT.distribution))
    if not distributions:
        raise ReleaseDigestError(f"{release} has no dcat:distribution")
    for distribution in distributions:
        if not isinstance(distribution, URIRef):
            raise ReleaseDigestError(
                f"distribution must be an IRI: {distribution!r}"
            )
        for predicate in DIST_PREDICATES:
            values = list(graph.objects(distribution, predicate))
            if not values:
                raise ReleaseDigestError(
                    f"{distribution} lacks digest input {predicate}"
                )
            for object_ in values:
                dataset.add((distribution, predicate, _rdfc_term(object_)))

    return RDFCanon(
        "sha256",
        dataset,
        RDFCanonTimeTicker(10_000),
    ).canonize()


def compute_digest(graph: Graph, release: URIRef) -> str:
    preimage = canonical_preimage(graph, release).encode("utf-8")
    return f"sha256:{hashlib.sha256(preimage).hexdigest()}"


def release_nodes(graph: Graph) -> list[Identifier]:
    return sorted(
        set(graph.subjects(RDF.type, RKAF.ReferenceResourceRelease)),
        key=str,
    )


def validate_release(graph: Graph, release: Identifier) -> tuple[str, str | None]:
    if not isinstance(release, URIRef):
        raise ReleaseDigestError(
            "ReferenceResourceRelease must be named by an IRI; blank-node "
            "release manifests are not conformant"
        )
    actual = compute_digest(graph, release)
    declared_values = list(graph.objects(release, RKAF.referenceReleaseDigest))
    if len(declared_values) != 1:
        return actual, None
    return actual, str(declared_values[0])


def release_digest_errors(graph: Graph) -> list[str]:
    """Return conformance errors for every release in an RDF graph.

    This is the production hook used by the ordinary Rulespec L3 validators.
    The lexical CUE/JSON-Schema/SHACL constraint proves only that a digest
    *looks* like SHA-256; this hook proves it commits to the canonical release
    manifest and distribution metadata.
    """
    errors: list[str] = []
    for release in release_nodes(graph):
        try:
            actual, declared = validate_release(graph, release)
        except ReleaseDigestError as error:
            errors.append(f"{release}: {error}")
            continue
        if declared is None:
            errors.append(
                f"{release}: exactly one rkaf:referenceReleaseDigest is required"
            )
        elif declared != actual:
            errors.append(
                f"{release}: declared digest {declared} does not match "
                f"RDFC-1.0 manifest digest {actual}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute or verify ReferenceResourceRelease digests"
    )
    parser.add_argument("document", type=Path)
    parser.add_argument("--release", help="one release IRI; default is every release")
    parser.add_argument(
        "--preimage",
        action="store_true",
        help="print canonical N-Quads before the digest",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable results"
    )
    args = parser.parse_args()

    graph = Graph()
    graph.parse(args.document, format="json-ld")
    releases = (
        [URIRef(args.release)] if args.release is not None else release_nodes(graph)
    )
    if not releases:
        raise ReleaseDigestError("document contains no ReferenceResourceRelease")

    rows = []
    failed = False
    for release in releases:
        actual, declared = validate_release(graph, release)
        matches = declared == actual
        failed |= not matches
        rows.append(
            {
                "release": str(release),
                "declared": declared,
                "computed": actual,
                "matches": matches,
            }
        )
        if args.preimage and not args.json:
            print(canonical_preimage(graph, release), end="")

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            state = "PASS" if row["matches"] else "FAIL"
            print(
                f"[{state}] {row['release']}: declared={row['declared']} "
                f"computed={row['computed']}"
            )
    return 1 if failed else 0


def cli() -> int:
    """`main()` with the setup-error contract: 2 for a malformed document.

    Every entry point goes through this — the shim at `tools/`, `-m`, and the
    block below — so exit 1 keeps meaning "digest mismatch" in all of them.
    """
    try:
        return main()
    except ReleaseDigestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
