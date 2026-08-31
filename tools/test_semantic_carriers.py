#!/usr/bin/env python3
"""Semantic carrier tests — meaning survives the carrier, not just shape.

`tools/test_constraints_compile.py` proves the compiled artifacts have the
right SHAPE: this property exists, that enum is closed, this shape composes
that one. Shape parity is necessary and insufficient. A carrier can have
exactly the right fields and still lose the meaning:

  * a digest that survives as a *different* literal after a round trip
  * a subject and an object that expand to the same triple
  * an `xsd:date` that comes back as a plain string
  * an "evidence" IRI that resolves to nothing
  * a regenerated schema that classifies a fixture differently
  * an envelope field that reaches four targets and not the fifth
  * a profile term that the kernel silently enforces (or silently does not)

Each test class below is one of the seven categories the v0.2 contract reshape
named, exercised END-TO-END through a real carrier — a JSON-LD expansion, a
pySHACL run, an actual recompilation — rather than by reading the compiled text.
The class names are the mapping:

  | Category             | Class                            |
  |----------------------|----------------------------------|
  | identity             | `IdentityCarrierTests`           |
  | direction            | `DirectionCarrierTests`          |
  | typed values         | `TypedValueCarrierTests`         |
  | transformations      | `TransformationStabilityTests`   |
  | evidence resolution  | `EvidenceResolutionCarrierTests` |
  | composition          | `CompositionCarrierTests`        |
  | profile isolation    | `ProfileIsolationCarrierTests`   |

The runtime half of profile isolation — whether a profile-contributed lifecycle
kind still drives the kernel's stale transition — is in Rust, where the runtime
is: `crates/rkaf-runtime/tests/profile_isolation_carrier.rs`. The Rust
round-trip harness `crates/rkaf-core/tests/fixture_round_trip.rs` is the typed
SDK half of identity and typed values.

Run:  python3 -m unittest tools.test_semantic_carriers -v
"""

from __future__ import annotations

import copy
import functools
import json
import re
import unittest
from pathlib import Path

import rdflib
from rdflib import BNode, Literal, URIRef
from rdflib.compare import isomorphic
from pyshacl import validate as shacl_validate

try:
    import constraints_compile as cc
    from conformance_lib import (
        COMPILED_PROFILE_SHACL_ROOT,
        COMPILED_SHACL_DIR,
        HAND_AUTHORED_SHACL_DIR,
        ROOT,
        compiled_shacl_paths,
        positive_fixture_paths,
        schema_bindings,
        shacl_shape_paths,
    )
except ModuleNotFoundError:  # imported as tools.test_semantic_carriers
    from tools import constraints_compile as cc
    from tools.conformance_lib import (
        COMPILED_PROFILE_SHACL_ROOT,
        COMPILED_SHACL_DIR,
        HAND_AUTHORED_SHACL_DIR,
        ROOT,
        compiled_shacl_paths,
        positive_fixture_paths,
        schema_bindings,
        shacl_shape_paths,
    )

RKAF = "https://rulespec.org/ns/v1#"
OA = "http://www.w3.org/ns/oa#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DCTERMS = "http://purl.org/dc/terms/"
PROV = "http://www.w3.org/ns/prov#"
RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

CONTEXT_PATH = ROOT / "context" / "rkaf-context.jsonld"
FIXTURES = ROOT / "fixtures"
CONSTRAINT_SOURCES = sorted(
    [*(ROOT / "constraints" / "core").glob("*.cue")]
    + [*(ROOT / "constraints" / "analysis").glob("*.cue")]
    + [*(ROOT / "constraints" / "profiles").glob("*/*.cue")]
)


# ── carrier helpers ───────────────────────────────────────────────────────
#
# Everything below goes through a REAL carrier. `expand` is JSON-LD expansion
# (rdflib's json-ld parser resolves the context, coerces `@type: @id` terms to
# IRIs, and types literals), and `compact` is the inverse with the shipped
# context. Round-tripping through them is the only way to see whether a
# coercion the context declares actually fires.


def _context() -> dict:
    return json.loads(CONTEXT_PATH.read_text())["@context"]


def expand_file(path: Path) -> rdflib.Graph:
    """Parse a fixture file to RDF — JSON-LD expansion through the carrier."""
    graph = rdflib.Graph()
    graph.parse(str(path), format="json-ld")
    return graph


def expand_doc(doc: dict) -> rdflib.Graph:
    """Parse an in-memory JSON-LD document, resolving the repo-relative context.

    The fixtures reference `../context/rkaf-context.jsonld`; an in-memory copy
    has no file to resolve that against, so the context is rewritten to a
    repo-root-relative path and the repo root is passed as the base IRI. The
    document is otherwise untouched — this is the same context the file form
    resolves to.
    """
    doc = copy.deepcopy(doc)
    doc["@context"] = "context/rkaf-context.jsonld"
    graph = rdflib.Graph()
    graph.parse(
        data=json.dumps(doc), format="json-ld", base=ROOT.as_uri() + "/"
    )
    return graph


def compact(graph: rdflib.Graph) -> str:
    """Serialize back to JSON-LD under the shipped context (compaction)."""
    return graph.serialize(format="json-ld", context=_context(), auto_compact=True)


def expanded_jsonld(graph: rdflib.Graph) -> str:
    return graph.serialize(format="json-ld")


def objects(graph: rdflib.Graph, subject: str, predicate: str) -> list:
    return sorted(
        graph.objects(URIRef(subject), URIRef(predicate)), key=lambda o: str(o)
    )


def one(graph: rdflib.Graph, subject: str, predicate: str):
    found = objects(graph, subject, predicate)
    assert len(found) == 1, f"expected exactly one {predicate} on {subject}, got {found}"
    return found[0]


_SHAPE_CACHE: dict[tuple[str, ...], rdflib.Graph] = {}


def shape_graph(paths) -> rdflib.Graph:
    """Load (and memoize) a SHACL shape graph. pySHACL runs are the slow part."""
    key = tuple(str(p) for p in paths)
    cached = _SHAPE_CACHE.get(key)
    if cached is None:
        cached = rdflib.Graph()
        for path in paths:
            cached.parse(str(path), format="turtle")
        _SHAPE_CACHE[key] = cached
    return cached


def conforms(data: rdflib.Graph, shapes: rdflib.Graph) -> tuple[bool, str]:
    ok, _, text = shacl_validate(
        data, shacl_graph=shapes, inference="rdfs", advanced=True
    )
    return ok, text


def full_suite() -> rdflib.Graph:
    return shape_graph(shacl_shape_paths())


@functools.lru_cache(maxsize=1)
def parsed_sources() -> tuple[tuple[Path, cc.ConstraintDoc], ...]:
    """Every kernel, analysis, and profile source, parsed once per process.

    Several tests below walk the whole tree; re-parsing 46 CUE files per test
    turned a 3-second module into a 20-second one.
    """
    return tuple((path, cc.parse_cue_file(path)) for path in CONSTRAINT_SOURCES)


def all_properties(shape: cc.ShapeDef) -> list[cc.PropDef]:
    props = list(shape.properties)
    for conditional in shape.conditionals:
        props.extend(conditional.then_require)
    for disjunction in shape.disjunctions:
        for branch in disjunction:
            props.extend(branch.properties)
    return props


# ── 1. identity ───────────────────────────────────────────────────────────


class IdentityCarrierTests(unittest.TestCase):
    """Same content ⇒ same identity, and that binding survives the carrier.

    §4.1 and §4.2 of `spec/rkaf-core.md` make identity CONTENT-bound: an
    Artifact version carries `rkaf:hasContentDigest`, a SourceFragment carries
    the digest of the Artifact state its offsets were taken against plus the
    digest of the region text itself. A carrier that preserved the IRIs and
    dropped or altered a digest would keep every shape gate green while
    destroying exactly the thing the digests exist to pin.
    """

    def test_a_fragment_digest_binding_survives_a_json_ld_round_trip(self) -> None:
        original = expand_file(FIXTURES / "sourcefragment-position-selector-positive.jsonld")
        round_tripped = rdflib.Graph()
        round_tripped.parse(data=expanded_jsonld(original), format="json-ld")

        fragment = "urn:rkaf:fixture:sf-pos:fragment"
        artifact = "urn:rkaf:fixture:sf-pos:artifact"
        for graph, label in ((original, "before"), (round_tripped, "after")):
            source_digest = one(graph, fragment, RKAF + "sourceArtifactDigest")
            artifact_digest = one(graph, artifact, RKAF + "hasContentDigest")
            self.assertEqual(
                str(source_digest),
                str(artifact_digest),
                f"{label}: the fragment's sourceArtifactDigest must be the same "
                "string as the Artifact's contentDigest — same content, same "
                "identity",
            )
        self.assertTrue(
            isomorphic(original, round_tripped),
            "expanding, re-serializing, and re-expanding a fragment fixture "
            "must yield the same graph — identity is carried, not recomputed",
        )

    def test_fragment_identity_is_four_bindings_and_all_four_survive(self) -> None:
        graph = rdflib.Graph()
        graph.parse(
            data=expanded_jsonld(
                expand_file(FIXTURES / "sourcefragment-position-selector-positive.jsonld")
            ),
            format="json-ld",
        )
        fragment = "urn:rkaf:fixture:sf-pos:fragment"
        selector = "urn:rkaf:fixture:sf-pos:selector"

        self.assertEqual(
            str(one(graph, fragment, OA + "hasSource")),
            "urn:rkaf:fixture:sf-pos:artifact",
            "binding 1 — the exact Artifact, as an IRI (the context coerces "
            "oa:hasSource to @id; a string literal here would make the parent "
            "unresolvable)",
        )
        self.assertIn(
            URIRef(selector),
            [o for o in graph.objects(URIRef(fragment), URIRef(OA + "hasSelector"))],
            "binding 2 — the region, reachable as a node",
        )
        self.assertEqual(
            str(one(graph, selector, RKAF + "coordinateSystem")),
            RKAF + "unicode-codepoint",
            "binding 3 — the unit the offsets count in, on the offset-bearing "
            "selector; an offset with no unit names three different regions",
        )
        self.assertTrue(
            str(one(graph, fragment, RKAF + "fragmentContentDigest")).startswith("sha256:"),
            "binding 4 — the digest of the selected region text itself",
        )

    def test_two_editions_of_one_work_keep_distinct_content_identities(self) -> None:
        graph = rdflib.Graph()
        graph.parse(
            data=expanded_jsonld(
                expand_file(FIXTURES / "artifact-version-lineage-positive.jsonld")
            ),
            format="json-ld",
        )
        newer = "urn:example:document:air-quality-plan:2026-07-25"
        older = "urn:example:document:air-quality-plan:2025-07-25"
        digests = {
            str(one(graph, newer, RKAF + "hasContentDigest")),
            str(one(graph, older, RKAF + "hasContentDigest")),
        }
        self.assertEqual(
            len(digests), 2, "two editions must carry two distinct content digests"
        )
        self.assertEqual(
            str(one(graph, newer, DCTERMS + "isVersionOf")),
            str(one(graph, older, DCTERMS + "isVersionOf")),
            "both editions must name the SAME stable work resource — that is "
            "what makes them versions of one thing rather than two documents",
        )
        self.assertEqual(
            str(one(graph, newer, PROV + "wasRevisionOf")),
            older,
            "the revision edge must resolve to the earlier edition, not to the "
            "work",
        )

    def test_a_changed_digest_is_a_different_identity(self) -> None:
        """The control. Without it, every assertion above would also hold for a
        carrier that ignored digests entirely."""
        source = json.loads(
            (FIXTURES / "sourcefragment-position-selector-positive.jsonld").read_text()
        )
        original = expand_doc(source)

        mutated = copy.deepcopy(source)
        for node in mutated["@graph"]:
            if node.get("@id") == "urn:rkaf:fixture:sf-pos:fragment":
                node["rkaf:fragmentContentDigest"] = "sha256:" + "c" * 64
        self.assertFalse(
            isomorphic(original, expand_doc(mutated)),
            "changing one region digest must change the graph — if it does "
            "not, the digest is decoration and 'same content, same identity' "
            "means nothing",
        )


# ── 2. direction ──────────────────────────────────────────────────────────


class DirectionCarrierTests(unittest.TestCase):
    """A relation points one way, and the carrier has to keep it that way.

    `rkaf:assertsSubject` and `rkaf:assertsObject` are the worked example
    (`spec/rkaf-core.md` §2.1): predicates stay affirmative and polarity is
    stated, so the ONLY thing distinguishing "A applies to B" from "B applies
    to A" is which slot each IRI sits in.
    """

    def test_subject_and_object_do_not_collapse_under_expansion(self) -> None:
        graph = expand_file(FIXTURES / "relationshipassertion-affirmed-positive.jsonld")
        node = "urn:rkaf:fixture:relationship-assertion:expected-baseline"
        subject = one(graph, node, RKAF + "assertsSubject")
        obj = one(graph, node, RKAF + "assertsObject")
        self.assertNotEqual(
            subject, obj, "subject and object must expand to different terms"
        )
        for term, slot in ((subject, "assertsSubject"), (obj, "assertsObject")):
            self.assertIsInstance(
                term,
                URIRef,
                f"{slot} must expand to an IRI, not a literal — the context "
                "coerces it to @id, and a literal here would make the relation "
                "unresolvable",
            )

    def test_swapping_subject_and_object_changes_the_graph(self) -> None:
        source = json.loads(
            (FIXTURES / "relationshipassertion-affirmed-positive.jsonld").read_text()
        )
        swapped = copy.deepcopy(source)
        source_assertion = next(
            node
            for node in source["@graph"]
            if node.get("@type") == "rkaf:RelationshipAssertion"
        )
        swapped_assertion = next(
            node
            for node in swapped["@graph"]
            if node.get("@type") == "rkaf:RelationshipAssertion"
        )
        swapped_assertion["rkaf:assertsSubject"], swapped_assertion["rkaf:assertsObject"] = (
            source_assertion["rkaf:assertsObject"],
            source_assertion["rkaf:assertsSubject"],
        )
        self.assertFalse(
            isomorphic(expand_doc(source), expand_doc(swapped)),
            "swapping the subject and object of a relationship assertion must "
            "produce a different graph — direction is carried by the slot, and "
            "a carrier that normalized the pair would silently assert the "
            "converse",
        )

    def test_swapping_two_class_ranged_edges_flips_the_shacl_verdict(self) -> None:
        """Where a range IS declared, a swap is not merely different — it is
        invalid. `rkaf:proofIssuer` is class-ranged to `rkaf:ResolverProofIssuer`
        and `rkaf:proofComparisonContext` to `rkaf:RelationComparisonContext`
        (`constraints/analysis/semantics/l0-ranges.cue`), so a proof record that
        transposes them names a resolver version that never ran."""
        source = json.loads(
            (FIXTURES / "relationcomparisoncontext-satisfied-positive.jsonld").read_text()
        )
        shapes = full_suite()
        ok, _ = conforms(expand_doc(source), shapes)
        self.assertTrue(ok, "the shipped fixture must conform (control)")

        swapped = copy.deepcopy(source)
        for node in swapped["@graph"]:
            if node.get("@type") == "rkaf:ResolverProofRecord":
                node["rkaf:proofIssuer"], node["rkaf:proofComparisonContext"] = (
                    node["rkaf:proofComparisonContext"],
                    node["rkaf:proofIssuer"],
                )
        ok_swapped, _ = conforms(expand_doc(swapped), shapes)
        self.assertFalse(
            ok_swapped,
            "transposing rkaf:proofIssuer and rkaf:proofComparisonContext must "
            "change the verdict — both are IRIs of the same syntactic shape, "
            "so only the declared class range distinguishes them",
        )

    def test_both_endpoints_of_a_concept_mapping_expand_as_iris(self) -> None:
        """Canonical mapping endpoints and their release pins stay directed IRIs."""
        graph = expand_file(FIXTURES / "conceptmapping-positive.jsonld")
        node = "urn:rkaf:fixture:cmap:income-closematch"
        for term in (
            "assertsSubject",
            "assertsObject",
            "sourceConceptRelease",
            "targetConceptRelease",
        ):
            with self.subTest(term=term):
                self.assertIsInstance(
                    one(graph, node, RKAF + term),
                    URIRef,
                    f"rkaf:{term} must expand to an IRI",
                )
        self.assertNotEqual(
            one(graph, node, RKAF + "assertsSubject"),
            one(graph, node, RKAF + "assertsObject"),
            "a mapping's two endpoints are a direction, not a set",
        )

    def test_polarity_is_carried_beside_an_affirmative_predicate(self) -> None:
        affirmed = expand_file(FIXTURES / "relationshipassertion-affirmed-positive.jsonld")
        denied = expand_file(FIXTURES / "relationshipassertion-denied-positive.jsonld")
        affirmed_node = "urn:rkaf:fixture:relationship-assertion:expected-baseline"
        denied_nodes = list(
            denied.subjects(URIRef(RKAF + "assertionPolarity"), URIRef(RKAF + "denied"))
        )
        self.assertEqual(
            len(denied_nodes), 1, "the denied fixture must state exactly one denial"
        )
        self.assertEqual(
            str(one(affirmed, affirmed_node, RKAF + "assertionPolarity")),
            RKAF + "affirmed",
        )
        denied_predicate = str(
            one(denied, str(denied_nodes[0]), RKAF + "assertsPredicate")
        )
        affirmed_predicate = str(one(affirmed, affirmed_node, RKAF + "assertsPredicate"))
        self.assertEqual(
            denied_predicate,
            affirmed_predicate,
            "a denied assertion names the SAME affirmative predicate as an "
            "affirmed one — polarity lives in its own slot, so no consumer can "
            "read a denial off the predicate IRI, and no producer can express "
            "one by inventing a negated predicate",
        )


# ── 3. typed values ───────────────────────────────────────────────────────


class TypedValueCarrierTests(unittest.TestCase):
    """A `ValueAssertion` object is a typed literal, and the type is the point.

    `spec/rkaf-core.md` §2.2 closes `rkaf:ValueDatatype` deliberately: an open
    datatype IRI would make "typed" mean nothing. A carrier that returned
    `"2026-03-01"` as a plain string after a round trip would pass every shape
    check and hand the consumer an untyped string.
    """

    def test_a_date_value_keeps_its_datatype_through_expand_and_compact(self) -> None:
        node = "urn:rkaf:fixture:value-assertion:effective-date"
        fixture = expand_file(FIXTURES / "valueassertion-date-positive.jsonld")
        original = rdflib.Graph()
        for triple in fixture.triples((URIRef(node), None, None)):
            original.add(triple)
        value = one(original, node, RKAF + "assertsValue")
        self.assertIsInstance(value, Literal)
        self.assertEqual(
            value.datatype,
            URIRef(XSD + "date"),
            "expansion must produce an xsd:date literal, not a bare string",
        )
        self.assertEqual(str(value), "2026-03-01", "the lexical form is preserved")

        compacted = compact(original)
        self.assertIn(
            "xsd:date",
            compacted,
            "compaction must re-emit the datatype — a value object that "
            "compacts to a bare string has lost the type on the wire",
        )
        reexpanded = rdflib.Graph()
        reexpanded.parse(data=compacted, format="json-ld")
        self.assertTrue(
            isomorphic(original, reexpanded),
            "expand → compact → expand must be the identity on a typed-literal "
            "assertion",
        )

    def test_an_integer_value_keeps_its_lexical_form(self) -> None:
        node = "urn:rkaf:fixture:value-assertion:comment-count-denied"
        fixture = expand_file(FIXTURES / "valueassertion-denied-integer-positive.jsonld")
        graph = rdflib.Graph()
        for triple in fixture.triples((URIRef(node), None, None)):
            graph.add(triple)
        values = [
            o
            for _, _, o in graph.triples((None, URIRef(RKAF + "assertsValue"), None))
        ]
        self.assertEqual(len(values), 1)
        value = values[0]
        self.assertEqual(value.datatype, URIRef(XSD + "integer"))
        self.assertEqual(
            value._value if hasattr(value, "_value") else None,
            int(str(value)),
            "rdflib must parse the lexical form as an integer",
        )
        reexpanded = rdflib.Graph()
        reexpanded.parse(data=compact(graph), format="json-ld")
        self.assertTrue(
            isomorphic(graph, reexpanded),
            "an integer-valued assertion must survive compaction unchanged — "
            "the RDF literal is lexical-form-plus-datatype, and re-parsing "
            "'42' into a number and back is where the fidelity goes",
        )

    def test_a_language_tagged_object_preserves_language_and_script(self) -> None:
        graph = expand_file(FIXTURES / "valueassertion-language-tagged-positive.jsonld")
        value = one(
            graph,
            "urn:rkaf:fixture:value-assertion:language-tagged",
            RKAF + "assertsValue",
        )
        self.assertIsInstance(value, Literal)
        self.assertEqual(value.language, "zh-Hant")
        self.assertIsNone(value.datatype)
        ok, _ = conforms(graph, full_suite())
        self.assertTrue(ok, "a well-formed BCP 47 language-tagged value must conform")

    def test_every_enum_valued_term_is_iri_coerced_in_the_context(self) -> None:
        """`constraints/README.md` states this as a rule; nothing enforced it.

        The compiled SHACL closes an enum with `sh:in ( rkaf:a rkaf:b )` over
        IRI members. `sh:in` over IRIs only matches data whose values ARRIVE as
        IRIs, so an enum-valued term with no `@type: @id`/`@vocab` coercion
        expands to a plain string literal and misses every member of its own
        set — while the shape file still contains a perfectly correct `sh:in`.
        """
        context = _context()
        uncoerced: list[str] = []
        for path, doc in parsed_sources():
            for shape in doc.shapes:
                for prop in all_properties(shape):
                    is_enum = bool(
                        prop.enum_ref
                        or prop.list_inner_enum
                        or prop.inline_enum_values
                        or prop.enum_union_refs
                    )
                    if not is_enum:
                        continue
                    entry = context.get(prop.name)
                    coercion = entry.get("@type") if isinstance(entry, dict) else None
                    if coercion not in ("@id", "@vocab"):
                        uncoerced.append(
                            f"{prop.name} (on {shape.name} in "
                            f"{path.relative_to(ROOT)}) → {coercion!r}"
                        )
        self.assertEqual(
            [], sorted(set(uncoerced)),
            "every enum-valued term MUST carry an @type: @id or @vocab "
            "coercion in context/rkaf-context.jsonld",
        )

    def test_every_xsd_annotated_term_carries_that_datatype_in_the_context(self) -> None:
        """The temporal half of the same failure, and it was live.

        A property the CUE declares as `string` and annotates `// xsd:dateTime`
        is a timestamp in every surface that reads the source, but the wire is
        decided by `context/rkaf-context.jsonld` alone: with no coercion the
        value expands to a plain literal, and nothing downstream objects
        because the compiled SHACL for these terms checks cardinality, not
        datatype. Ten terms were in that state — `rkaf:attestedAt` among them —
        so an attestation time arrived untyped while `rkaf:assertedAt`, the
        same temporal semantics one record away, arrived as `xsd:dateTime`.
        `context/README.md` listed this as an ungated convention; it is a gate
        now.
        """
        context = _context()
        annotated = re.compile(
            r'^\s*"(rkaf:[A-Za-z]+)"\??:\s*[^/\n]*//\s*(xsd:[A-Za-z]+)'
        )
        checked = 0
        wrong: list[str] = []
        for path in sorted((ROOT / "constraints").rglob("*.cue")):
            for line in path.read_text().splitlines():
                match = annotated.match(line)
                if not match:
                    continue
                term, datatype = match.group(1), match.group(2)
                checked += 1
                entry = context.get(term)
                declared = entry.get("@type") if isinstance(entry, dict) else None
                if declared != datatype:
                    wrong.append(
                        f"{term} (in {path.relative_to(ROOT)}) is annotated "
                        f"{datatype} and the context declares {declared!r}"
                    )
        self.assertGreater(checked, 20, "the annotation scan must actually run")
        self.assertEqual(
            [], sorted(set(wrong)),
            "every property the CUE annotates with an XSD datatype MUST carry "
            "that same datatype in context/rkaf-context.jsonld — the "
            "annotation is the declared meaning and the context is the only "
            "thing that puts it on the wire",
        )


# ── 4. transformations ────────────────────────────────────────────────────


class TransformationStabilityTests(unittest.TestCase):
    """Compile → regenerate → revalidate is a fixed point.

    `tools/codegen_drift_audit.py` proves the Rust tree is in lock-step by
    re-running the whole driver. These tests answer the narrower question that
    matters for meaning: does a REGENERATED artifact classify data the same way
    the shipped one does, and does a document survive the JSON-LD
    transformation the wire actually applies.
    """

    def test_recompiling_every_source_reproduces_the_shipped_bytes(self) -> None:
        mismatched: list[str] = []
        for path in CONSTRAINT_SOURCES:
            doc = cc.parse_cue_file(path)
            registry = cc._scan_global_enum_registry(path)
            references = cc._scan_reference_class_registry(path)
            sub = self._sub_path(path)
            emitted = {
                ROOT / f"compiled/json-schema/{sub}/{path.stem}.schema.json":
                    cc.target_json_schema(doc, registry=registry),
                ROOT / f"compiled/shacl/{sub}/{path.stem}.ttl":
                    cc.target_shacl(
                        doc,
                        reference_classes=references,
                        source_file=path,
                        registry=registry,
                    ),
                ROOT / f"compiled/typescript/{sub}/{path.stem}.ts":
                    cc.target_typescript(doc, registry=registry, source_file=path),
            }
            for sink, text in emitted.items():
                if not sink.exists():
                    mismatched.append(f"{sink.relative_to(ROOT)} MISSING")
                elif sink.read_text() != text:
                    mismatched.append(str(sink.relative_to(ROOT)))
        self.assertEqual(
            [], mismatched,
            "recompiling each source must reproduce the shipped artifact byte "
            "for byte — a difference means the tree was hand-edited or the "
            "compiler is not deterministic",
        )

    @staticmethod
    def _sub_path(path: Path) -> str:
        parts = path.relative_to(ROOT / "constraints").parts
        if parts[0] == "profiles":
            return f"profiles/{parts[1]}"
        return parts[0]

    def test_a_regenerated_shape_graph_returns_the_same_verdicts(self) -> None:
        """The revalidate half. Regenerating the SHACL and running fixtures
        through the fresh graph must reproduce every shipped verdict; a
        compiler change that weakened a shape would otherwise show up only as a
        byte diff nobody reads."""
        regenerated = rdflib.Graph()
        for path in sorted(HAND_AUTHORED_SHACL_DIR.glob("*.ttl")):
            regenerated.parse(str(path), format="turtle")
        for path in CONSTRAINT_SOURCES:
            doc = cc.parse_cue_file(path)
            regenerated.parse(
                data=cc.target_shacl(
                    doc,
                    reference_classes=cc._scan_reference_class_registry(path),
                    source_file=path,
                    registry=cc._scan_global_enum_registry(path),
                ),
                format="turtle",
            )

        shipped = full_suite()
        cases = [
            (FIXTURES / "valueassertion-date-positive.jsonld", True),
            (FIXTURES / "conceptassignment-fragment-direct-positive.jsonld", True),
            (FIXTURES / "relationfinding-discrepancy-positive.jsonld", True),
            (FIXTURES / "negatives" / "value-assertion-unregistered-datatype-negative.jsonld", False),
            (FIXTURES / "negatives" / "text-position-selector-inverted-offsets-negative.jsonld", False),
            (FIXTURES / "negatives" / "closure-claim-enabled-status-negative.jsonld", False),
        ]
        for path, expected in cases:
            with self.subTest(fixture=path.name):
                data = expand_file(path)
                shipped_ok, _ = conforms(data, shipped)
                fresh_ok, _ = conforms(expand_file(path), regenerated)
                self.assertEqual(
                    shipped_ok, expected, f"shipped verdict changed for {path.name}"
                )
                self.assertEqual(
                    fresh_ok,
                    shipped_ok,
                    f"the regenerated shape graph disagrees with the shipped "
                    f"one on {path.name} — recompiling changed a verdict",
                )

    def test_every_blank_node_free_positive_fixture_survives_compaction(self) -> None:
        """Expand → compact → expand over the whole positive corpus.

        Fixtures containing blank nodes are excluded, and the exclusion is a
        limitation of the SERIALIZER, not of Rulespec: rdflib emits a blank-node
        object of an `@type: @id`-coerced term as a bare `_:b0` reference
        without also emitting its node object, so the description is lost on
        re-parse. Those fixtures are still covered by the expansion round trip
        in `IdentityCarrierTests` and by the Rust carrier harness.
        """
        checked = 0
        diverged: list[str] = []
        for path in positive_fixture_paths():
            graph = expand_file(path)
            if any(isinstance(term, BNode) for triple in graph for term in triple):
                continue
            checked += 1
            reexpanded = rdflib.Graph()
            reexpanded.parse(data=compact(graph), format="json-ld")
            if not isomorphic(graph, reexpanded):
                diverged.append(
                    f"{path.relative_to(FIXTURES)} ({len(graph)} → {len(reexpanded)} triples)"
                )
        self.assertGreater(checked, 50, "the corpus scan must actually run")
        self.assertEqual(
            [], diverged,
            "every blank-node-free positive fixture must survive an "
            "expand → compact → expand round trip unchanged",
        )


# ── 5. evidence resolution ────────────────────────────────────────────────


class EvidenceResolutionCarrierTests(unittest.TestCase):
    """"Evidence" has to resolve to something, and to the RIGHT something.

    The reshape's class ranges (`constraints/**/semantics/l0-ranges.cue`) exist
    so that an evidence edge lands on an addressable record of a declared class
    rather than on any IRI. These tests dereference the edges inside the fixture
    graph and check what they reach.
    """

    def test_assignment_evidence_resolves_to_a_fragment_of_the_subject_artifact(self) -> None:
        graph = expand_file(FIXTURES / "conceptassignment-fragment-direct-positive.jsonld")
        assignment = "urn:rkaf:fixture:ca:seg:sec-3a-income"

        binding = next(
            graph.subjects(
                URIRef(RKAF + "bindsAssertion"),
                URIRef(assignment),
            )
        )
        evidence = one(graph, str(binding), RKAF + "bindsSourceFragment")
        self.assertIsInstance(evidence, URIRef, "evidence must be an IRI, not a label")
        self.assertIn(
            URIRef(RKAF + "SourceFragment"),
            list(graph.objects(evidence, RDF_TYPE)),
            "the evidence IRI must dereference IN THIS GRAPH to a node typed "
            "rkaf:SourceFragment — that is what the declared class range buys",
        )
        subject = one(graph, assignment, RKAF + "assertsSubject")
        self.assertEqual(
            subject, evidence,
            "a segment assignment must cite THAT segment (Core §4.7)",
        )
        artifact = one(graph, str(evidence), OA + "hasSource")
        self.assertIn(
            URIRef(RKAF + "Artifact"),
            list(graph.objects(artifact, RDF_TYPE)),
            "and the fragment's parent must itself resolve to an Artifact",
        )
        self.assertEqual(
            str(one(graph, str(evidence), RKAF + "sourceArtifactDigest")),
            str(one(graph, str(artifact), RKAF + "hasContentDigest")),
            "the cited region must be pinned to the Artifact STATE it was read "
            "from — evidence against an unpinned document is a citation to a "
            "moving target",
        )

    def test_version_lineage_evidence_resolves_to_a_digest_pinned_region(self) -> None:
        graph = expand_file(FIXTURES / "artifact-version-lineage-positive.jsonld")
        newer = "urn:example:document:air-quality-plan:2026-07-25"
        evidence = one(graph, newer, RKAF + "versionLineageEvidence")
        self.assertIn(
            URIRef(RKAF + "SourceFragment"),
            list(graph.objects(evidence, RDF_TYPE)),
            "lineage evidence must resolve to a SourceFragment, never to a "
            "bare label or a similarity score (Core §4.1)",
        )
        self.assertEqual(
            str(one(graph, str(evidence), OA + "hasSource")),
            newer,
            "the region stating the lineage must be a region OF the artifact "
            "making the claim",
        )
        self.assertEqual(
            str(one(graph, str(evidence), RKAF + "sourceArtifactDigest")),
            str(one(graph, newer, RKAF + "hasContentDigest")),
        )

    def test_evidence_from_another_artifact_is_rejected(self) -> None:
        negative = (
            FIXTURES / "negatives"
            / "concept-assignment-evidence-from-another-artifact-negative.jsonld"
        )
        ok, _ = conforms(expand_file(negative), full_suite())
        self.assertFalse(
            ok,
            "citing a region of a DIFFERENT artifact must fail — otherwise "
            "'evidence' means only 'an IRI that happens to be a fragment'",
        )

    def test_every_class_ranged_edge_that_resolves_locally_hits_its_range(self) -> None:
        """Repo-wide sweep over the positive corpus.

        For every declared class range, wherever the object IRI is ALSO
        described in the same document, its `rdf:type` must include the declared
        class. Objects that are not described locally are skipped — a
        cross-document reference is legal and Rulespec does not require a
        fixture to inline the world.
        """
        ranges: dict[str, str] = {}
        for registry in cc.range_registry_paths(ROOT / "constraints"):
            for line in registry.read_text().splitlines():
                parts = line.strip().split('"')
                if len(parts) >= 5 and parts[0] == "" and ":" in parts[1]:
                    ranges[parts[1]] = parts[3]
        self.assertGreater(len(ranges), 15, "the range registries must load")

        prefixes = {
            key: value
            for key, value in _context().items()
            if ":" not in key and isinstance(value, str)
        }

        def expand_term(term: str) -> str:
            prefix, _, local = term.partition(":")
            return prefixes.get(prefix, prefix + ":") + local

        shape_graph = full_suite()
        subclass = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")

        def satisfies_range(actual: URIRef, expected: URIRef) -> bool:
            if actual == expected:
                return True
            seen: set[URIRef] = set()
            pending = [actual]
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                parents = [
                    parent
                    for parent in shape_graph.objects(current, subclass)
                    if isinstance(parent, URIRef)
                ]
                if expected in parents:
                    return True
                pending.extend(parents)
            return False

        violations: list[str] = []
        for path in positive_fixture_paths():
            graph = expand_file(path)
            for term, target in ranges.items():
                predicate = URIRef(expand_term(term))
                expected = URIRef(expand_term(target))
                for subject, obj in graph.subject_objects(predicate):
                    if not isinstance(obj, URIRef):
                        violations.append(
                            f"{path.name}: {term} on {subject} is not an IRI"
                        )
                        continue
                    local_types = list(graph.objects(obj, RDF_TYPE))
                    if not local_types:
                        continue  # described elsewhere; legal
                    if not any(
                        isinstance(actual, URIRef)
                        and satisfies_range(actual, expected)
                        for actual in local_types
                    ):
                        violations.append(
                            f"{path.relative_to(FIXTURES)}: {term} → {obj} is "
                            f"typed {[str(t) for t in local_types]}, "
                            f"declared range {target}"
                        )
        self.assertEqual([], violations)


# ── 6. composition ────────────────────────────────────────────────────────


class CompositionCarrierTests(unittest.TestCase):
    """The shared envelope has to REACH every composer, on every surface.

    `#AssertionEnvelope` was extracted so the envelope has exactly one source
    and cannot drift between classes. That only holds if the projector flattens
    it into every target of every composer — and if the classes it produces are
    declared everywhere a class has to be declared.
    """

    @staticmethod
    def _envelope_fields() -> list[str]:
        for shape in cc.parse_cue_file(
            ROOT / "constraints" / "core" / "assertion.cue"
        ).shapes:
            if shape.name == "AssertionEnvelope":
                return [prop.name for prop in shape.properties]
        raise AssertionError("#AssertionEnvelope not found in assertion.cue")

    @staticmethod
    def _composers() -> list[tuple[Path, str, str]]:
        found = []
        for path in CONSTRAINT_SOURCES:
            raw = cc.parse_cue_file(path, resolve_composition=False)
            for shape in raw.shapes:
                if (
                    {
                        "AssertionEnvelope",
                        "DurableAssertionEnvelope",
                    }
                    & set(shape.base_refs)
                    and shape.type_iri
                ):
                    found.append((path, shape.name, shape.type_iri))
        return found

    @staticmethod
    def _direct_shacl_properties(shacl: str, shape_name: str, where: str) -> set[str]:
        """The terms `rkaf:<shape_name>Shape` declares as its OWN properties.

        Scoped twice over. First to the node shape — a compiled file may hold
        several. Then to the node shape's direct `sh:property` declarations,
        which the emitter writes one per line at two spaces of indent; the
        Pattern C `sh:or` guards nest their `sh:path` four spaces deeper and
        would otherwise keep the check green for a term whose own declaration
        was deleted.
        """
        marker = f"rkaf:{shape_name}Shape a sh:NodeShape"
        parts = shacl.split(marker, 1)
        if len(parts) != 2:
            raise AssertionError(f"no `{marker}` in {where}")
        block = parts[1].split("\n  .", 1)[0]
        return {
            match.group(1)
            for match in re.finditer(
                r"^  sh:property \[ sh:path (\S+) ;", block, re.M
            )
        }

    @staticmethod
    def _rust_struct_body(rust: str, shape_name: str, where: str) -> str:
        """The body of `pub struct <shape_name>`, and nothing else in the file.

        Every composer's module also emits the shared `AssertionEnvelope`
        struct, which carries a `#[serde(rename)]` for every envelope field —
        so a file-wide search for the rename cannot see a field deleted from
        the composer itself.
        """
        marker = f"pub struct {shape_name} {{"
        parts = rust.split(marker, 1)
        if len(parts) != 2:
            raise AssertionError(f"no `{marker}` in {where}")
        return parts[1].split("\n}", 1)[0]

    def test_the_envelope_and_its_composers_are_both_non_empty(self) -> None:
        """Guard: every assertion below is vacuous if the discovery breaks."""
        self.assertGreaterEqual(len(self._envelope_fields()), 10)
        composers = self._composers()
        self.assertGreaterEqual(len(composers), 5)
        self.assertIn(
            "rkaf:ConceptAssignment",
            {type_iri for _, _, type_iri in composers},
            "ConceptAssignment composes the envelope rather than restating it",
        )

    def test_every_envelope_field_reaches_every_composer_in_every_target(self) -> None:
        """`compiled/rego/` is excluded, for the reason `constraints/README.md`
        already records: Rego has no property types at all (it emits value
        sets and leaves `deny` rules to the policy author). There is no CUE
        passthrough target to exclude: `compiled/cue/` was a byte-identical
        copy of `constraints/` with no consumer and was removed."""
        fields = self._envelope_fields()
        missing: list[str] = []
        for path, shape_name, _ in self._composers():
            sub = TransformationStabilityTests._sub_path(path)
            schema = json.loads(
                (ROOT / f"compiled/json-schema/{sub}/{path.stem}.schema.json").read_text()
            )
            properties = (
                schema.get("$defs", {}).get(shape_name, {}).get("properties", {})
            )
            shacl = (ROOT / f"compiled/shacl/{sub}/{path.stem}.ttl").read_text()
            typescript = (ROOT / f"compiled/typescript/{sub}/{path.stem}.ts").read_text()
            # `tools/compile_all.sh` snake-cases the Rust sink: kernel sources
            # land flat under `generated/`, analysis and profile sources under
            # a snake_case subdirectory of the same name.
            rust_dir = ROOT / "crates/rkaf-core/src/generated"
            if sub != "core":
                rust_dir = rust_dir / sub.replace("-", "_")
            rust = (rust_dir / f"{path.stem.replace('-', '_')}.rs").read_text()
            # EVERY leg is scoped to the composer, and none of the four may be a
            # whole-file substring search. Each target restates envelope terms
            # somewhere OTHER than the declaration this test is about, so an
            # unscoped search stays green after the declaration is deleted:
            #
            #   * JSON Schema — sibling `$defs` entries for the shared shapes.
            #   * SHACL — the Pattern C `sh:or` guards name `sh:path
            #     rkaf:assertionOrigin` four more times inside the SAME node
            #     shape, so slicing to the node shape is NOT enough; only the
            #     node shape's DIRECT `sh:property` declarations count, which
            #     the emitter writes at exactly two spaces of indent.
            #   * TypeScript — the emitted `validate<Shape>` body names every
            #     pattern-constrained field.
            #   * Rust — the sibling `AssertionEnvelope` struct in the same
            #     module carries a `#[serde(rename)]` for every envelope field.
            interface_body = typescript.split(f"export interface {shape_name} {{", 1)
            self.assertEqual(
                len(interface_body), 2,
                f"no `export interface {shape_name}` in "
                f"compiled/typescript/{sub}/{path.stem}.ts",
            )
            interface_body = interface_body[1].split("\n}", 1)[0]
            shacl_properties = self._direct_shacl_properties(
                shacl, shape_name, f"compiled/shacl/{sub}/{path.stem}.ttl"
            )
            rust_body = self._rust_struct_body(
                rust, shape_name, f"{rust_dir.relative_to(ROOT)}/{path.stem}.rs"
            )
            for field in fields:
                where = f"{shape_name} ({path.relative_to(ROOT)})"
                if field not in properties:
                    missing.append(f"json-schema: {field} on {where}")
                if field not in shacl_properties:
                    missing.append(f"shacl: {field} on {where}")
                if f'"{field}"?:' not in interface_body and (
                    f'"{field}":' not in interface_body
                ):
                    missing.append(f"typescript: {field} on {where}")
                if f'rename = "{field}"' not in rust_body:
                    missing.append(f"rust: {field} on {where}")
        self.assertEqual(
            [], missing,
            "an envelope field that reaches some targets and not others is the "
            "drift extracting #AssertionEnvelope was meant to make impossible",
        )

    def test_the_shacl_and_rust_legs_see_a_deletion_from_the_composer_alone(self) -> None:
        """The meta-test for the check above: each leg must be blind to the
        restatements elsewhere in its own file.

        Both mutations below delete ONE declaration from ONE composer and leave
        the term present elsewhere in the same file — the exact state a
        whole-file substring search reads as "still there". The assertions run
        against the real shipped artifacts, so if the emitter ever changes the
        layout these helpers slice on, this fails rather than silently going
        vacuous again.
        """
        field = "rkaf:assertionOrigin"

        shacl_path = ROOT / "compiled/shacl/core/concept-assignment.ttl"
        shacl = shacl_path.read_text()
        self.assertIn(
            field,
            self._direct_shacl_properties(shacl, "ConceptAssignment", str(shacl_path)),
            "control: the shipped shape declares the field",
        )
        without = re.sub(
            rf"^  sh:property \[ sh:path {re.escape(field)} ;.*\n",
            "",
            shacl,
            flags=re.M,
        )
        self.assertNotEqual(without, shacl, "the deletion must actually apply")
        self.assertIn(
            f"sh:path {field} ;",
            without,
            "the Pattern C guards still name the term — that is precisely why a "
            "whole-file search cannot be the check",
        )
        self.assertNotIn(
            field,
            self._direct_shacl_properties(without, "ConceptAssignment", str(shacl_path)),
            "deleting rkaf:ConceptAssignmentShape's own sh:property declaration "
            "must be visible to the SHACL leg",
        )

        rust_path = ROOT / "crates/rkaf-core/src/generated/assertion.rs"
        rust = rust_path.read_text()
        self.assertIn(
            f'rename = "{field}"',
            self._rust_struct_body(rust, "Assertion", str(rust_path)),
            "control: the shipped struct carries the rename",
        )
        body = self._rust_struct_body(rust, "Assertion", str(rust_path))
        stripped = rust.replace(
            body,
            re.sub(
                rf'    /// JSON-LD property `{re.escape(field)}`\.\n'
                rf'    #\[serde\(rename = "{re.escape(field)}"\)\]\n'
                r"    pub assertion_origin: AssertionOrigin,\n",
                "",
                body,
            ),
            1,
        )
        self.assertNotEqual(stripped, rust, "the deletion must actually apply")
        self.assertIn(
            f'rename = "{field}"',
            stripped,
            "the sibling AssertionEnvelope struct still carries the rename — "
            "again why a whole-file search cannot be the check",
        )
        self.assertNotIn(
            f'rename = "{field}"',
            self._rust_struct_body(stripped, "Assertion", str(rust_path)),
            "deleting `pub struct Assertion`'s own field must be visible to the "
            "Rust leg",
        )

    def test_the_one_hand_restated_disposition_property_matches_the_shape(self) -> None:
        """`#GeneratedWorkProduct` is the exception to the composition rule.

        `spec/rkaf-vocabulary.md` lists it beside the `#ConsumerDisposition`
        composers, but it does not compose the shape — it restates
        `rkaf:consumerLifecycleState` by hand and takes neither of the other
        two members (`constraints/core/generated-work-product.cue`). It is
        therefore invisible to `_composers()` and to every assertion built on
        it, so the copy can drift from the original with no gate objecting.
        The two declarations are identical today; this is what keeps them so.
        """
        def declaration(source: str, shape_name: str, term: str) -> cc.PropDef:
            doc = cc.parse_cue_file(
                ROOT / "constraints" / "core" / source, resolve_composition=False
            )
            for shape in doc.shapes:
                if shape.name != shape_name:
                    continue
                for prop in all_properties(shape):
                    if prop.name == term:
                        return prop
            raise AssertionError(f"no {term} on #{shape_name} in {source}")

        term = "rkaf:consumerLifecycleState"
        shape = declaration("assertion.cue", "ConsumerDisposition", term)
        restated = declaration("generated-work-product.cue", "GeneratedWorkProduct", term)
        self.assertEqual(
            (shape.type_ref, shape.enum_ref, shape.optional),
            (restated.type_ref, restated.enum_ref, restated.optional),
            "#GeneratedWorkProduct restates #ConsumerDisposition's "
            f"{term} rather than composing the shape, so nothing else in the "
            "repo compares the two — either keep them identical or make "
            "generated-work-product.cue embed #ConsumerDisposition",
        )
        composed_members = {
            prop.name
            for prop in all_properties(
                next(
                    shape
                    for shape in cc.parse_cue_file(
                        ROOT / "constraints" / "core" / "assertion.cue",
                        resolve_composition=False,
                    ).shapes
                    if shape.name == "ConsumerDisposition"
                )
            )
        }
        work_product_members = {
            prop.name
            for prop in all_properties(
                next(
                    shape
                    for shape in cc.parse_cue_file(
                        ROOT / "constraints" / "core" / "generated-work-product.cue",
                        resolve_composition=False,
                    ).shapes
                    if shape.name == "GeneratedWorkProduct"
                )
            )
        }
        self.assertEqual(
            {term},
            composed_members & work_product_members,
            "the vocabulary row for rkaf:consumerLifecycleState says "
            "rkaf:GeneratedWorkProduct takes this ONE disposition property and "
            "not the rest — if that stops being true, the row is wrong",
        )

    def test_every_hand_authored_enum_value_is_declared_by_the_cue(self) -> None:
        """The hand-authored and compiled SHACL halves are ONE graph.

        `tools/conformance_lib.py::shacl_shape_paths` loads `shapes/*.ttl` and
        `compiled/shacl/**` together, and SHACL is conjunctive. A value that a
        hand-authored `sh:in` lists and the CUE does not declare is unreachable
        — the compiled shape rejects it first — so the authored list quietly
        describes a set no document can be in. The `rkaf:mappingRelation` pair
        is the case that was already known to matter
        (`test_the_hand_authored_shape_closes_the_same_mapping_set` in
        `test_constraints_compile.py`); this generalizes the check to every
        authored value set in the directory.
        """
        declared = self._cue_value_sets_by_term()
        offenders: list[str] = []
        for path, term, values in self._authored_enum_lists():
            allowed = declared.get(term)
            if allowed is None:
                offenders.append(
                    f"{path.name}: sh:in on {term}, which no CUE shape declares "
                    "as an enum-valued property"
                )
                continue
            for value in sorted(values - allowed):
                offenders.append(f"{path.name}: {term} lists undeclared {value}")
        self.assertEqual([], offenders)

    def test_an_authored_restatement_of_a_whole_closed_set_stays_complete(self) -> None:
        """Two authored files restate a WHOLE closed set rather than a subset.

        A subset is legitimate and common — `rkaf-shapes-core.ttl` lists only
        the four AI-touched origins because that is the precondition its
        Pattern C guard tests. These two are different: they are the authored
        mirror of the entire CUE value set, split across `sh:in` lists purely
        for readability. A value added to the CUE and not here would be
        rejected by the merged suite even though every compiled artifact
        accepts it.
        """
        declared = self._cue_value_sets_by_term()
        for filename, term, cue_source in (
            ("rkaf-shapes-warrant.ttl", "rkaf:warrantKind", "#WarrantKind"),
            (
                "rkaf-shapes-pattern-c.ttl",
                "rkaf:lifecycleEventKind",
                "#USProceedingLifecycleEventKind",
            ),
        ):
            with self.subTest(shape_file=filename, term=term):
                union: set[str] = set()
                for path, path_term, values in self._authored_enum_lists():
                    if path.name == filename and path_term == term:
                        union |= values
                self.assertTrue(union, f"no sh:in on {term} found in {filename}")
                expected = declared[term]
                if term == "rkaf:lifecycleEventKind":
                    # The kernel's ten universal kinds are NOT restated here —
                    # this file's lists are the US profile's twelve, which is
                    # the set the proceeding-stage guards are about.
                    expected = {
                        value for value in expected if value.startswith("rkaf:proceeding")
                    }
                self.assertEqual(
                    union,
                    expected,
                    f"{filename} restates {cue_source}; the authored union and "
                    "the CUE value set must be identical",
                )

    @staticmethod
    def _authored_enum_lists() -> list[tuple[Path, str, set[str]]]:
        """Every `sh:path <term> … sh:in ( … )` in `shapes/*.ttl`.

        Turtle comments are stripped first: the warrant file annotates its list
        with `# Legal family` headers, and a naive split would read those words
        as enum members.
        """
        found: list[tuple[Path, str, set[str]]] = []
        for path in sorted(HAND_AUTHORED_SHACL_DIR.glob("*.ttl")):
            text = "\n".join(
                re.sub(r"(?<!\S)#.*", "", line) for line in path.read_text().splitlines()
            )
            for match in re.finditer(
                r"sh:path\s+([A-Za-z]+:[A-Za-z]+)\s*;[^\]]*?sh:in\s*\(([^)]*)\)",
                text,
                re.S,
            ):
                found.append((path, match.group(1), set(match.group(2).split())))
        return found

    @staticmethod
    def _cue_value_sets_by_term() -> dict[str, set[str]]:
        """Term → every value any CUE shape declares for it, unions resolved."""
        enums: dict[str, set[str]] = {}
        unions: dict[str, list[str]] = {}
        for _, doc in parsed_sources():
            for enum in doc.enums:
                enums[enum.name] = set(enum.values)
            for union in doc.enum_unions:
                unions[union.name] = list(union.refs)

        def resolve(name: str, seen: frozenset[str] = frozenset()) -> set[str]:
            if name in enums:
                return set(enums[name])
            if name in seen:
                return set()
            values: set[str] = set()
            for ref in unions.get(name, ()):
                values |= resolve(ref, seen | {name})
            return values

        by_term: dict[str, set[str]] = {}
        for _, doc in parsed_sources():
            for shape in doc.shapes:
                for prop in all_properties(shape):
                    names = []
                    if prop.enum_ref:
                        names.append(prop.enum_ref)
                    if prop.list_inner_enum:
                        names.append(prop.list_inner_enum)
                    names.extend(prop.enum_union_refs or ())
                    values = set(prop.inline_enum_values or ())
                    for name in names:
                        values |= resolve(name)
                    if values:
                        by_term.setdefault(prop.name, set()).update(values)
        return by_term

    def test_every_schema_bound_class_carries_a_context_term(self) -> None:
        """DECLARATION CONSISTENCY across the schema-bound set — not a semantic
        gate, and it must not be read as one.

        Removing a class term changes NOTHING on the wire: a class IRI only
        ever appears as an `@type` value, never as a property, so the
        `{"@type": "@id"}` coercion on it never fires, and `rkaf:ValueAssertion`
        compacts through the `rkaf` prefix whether or not a term for it exists.
        Probed: stripping all seven class terms this reshape added leaves every
        positive fixture's expanded graph isomorphic and the compacted data
        byte-identical.

        What it does buy is that the context is a COMPLETE inventory of the
        dispatch set. A reader answering "does Rulespec have a class for this"
        from `context/rkaf-context.jsonld` gets the same 52 classes
        `rkaf-validate` dispatches on, rather than 50 of them plus a habit. The
        convention held for 50 of 52 by habit; this makes it hold by gate."""
        context = _context()
        undeclared = sorted(
            type_iri for type_iri in schema_bindings() if type_iri not in context
        )
        self.assertEqual(
            [], undeclared,
            "every class bound by a compiled JSON Schema MUST have a term "
            'definition with {"@type": "@id"} in context/rkaf-context.jsonld',
        )
        for type_iri in schema_bindings():
            entry = context[type_iri]
            self.assertEqual(
                entry.get("@type") if isinstance(entry, dict) else None,
                "@id",
                f"{type_iri} must be declared as an @id term",
            )

    # Shapes NO compiled JSON Schema binds to a `@type` — they declare no
    # `"@type"` const of their own, so the schema-bound sweep below cannot see
    # them. They are re-exported from the crate root by JUDGEMENT, not by that
    # gate: an SDK consumer composing the envelope, splitting an assertion into
    # its proposition and disposition halves, or reading a mapping-state
    # carrier must not have to reach into `generated::`. Naming them here is
    # what turns the judgement into a check.
    SHARED_SHAPES_REEXPORTED_BY_JUDGEMENT = (
        "AssertionEnvelope",
        "AssertionProposition",
        "ConsumerDisposition",
        "MappingStateCarrier",
    )

    # This source-specific profile remains schema-bound so the independently
    # released Extrapolator can validate it, but it is not part of the
    # generated Rulespec Core crate or its public Rust API.
    EXTRAPOLATOR_ONLY_CLASSES = ("RefSpecOpenLabelValueAssertion",)

    def test_every_schema_bound_class_carries_a_crate_root_reexport(self) -> None:
        """`crates/rkaf-core/src/lib.rs` re-exports every Core class a compiled
        JSON Schema binds to a `@type`, plus the named shared shapes above. An
        SDK consumer that has to reach into `generated::` for a Core class the
        validator dispatches on is reading an undocumented path. Independently
        released Extrapolator profile classes are checked as deliberate
        exclusions.

        The two halves are checked separately because only the first is
        derivable. `schema_bindings()` cannot see a shape with no `@type`
        const, so a sweep over it alone would stay green after any of the four
        shared shapes was dropped from the crate root.
        """
        lib = (ROOT / "crates/rkaf-core/src/lib.rs").read_text()
        # `pub use a::b::{X, Y};` statements span lines, so split on `;` and
        # keep the tail of each chunk that declares one.
        reexported: set[str] = set()
        for chunk in lib.split(";"):
            if "pub use" not in chunk:
                continue
            tail = chunk.split("pub use", 1)[1]
            for token in (
                tail.replace("{", " ")
                .replace("}", " ")
                .replace(",", " ")
                .replace("::", " ")
                .split()
            ):
                if token[:1].isupper():
                    reexported.add(token)
        missing = sorted(
            binding.class_name
            for binding in schema_bindings().values()
            if binding.class_name not in self.EXTRAPOLATOR_ONLY_CLASSES
            if binding.class_name not in reexported
        )
        self.assertEqual(
            [], missing,
            "every schema-bound class must be re-exported from the rkaf-core "
            "crate root",
        )

        bound_class_names = {
            binding.class_name for binding in schema_bindings().values()
        }
        for name in self.EXTRAPOLATOR_ONLY_CLASSES:
            with self.subTest(extrapolator_only_class=name):
                self.assertIn(name, bound_class_names)
                self.assertNotIn(
                    name,
                    reexported,
                    f"{name} belongs to Rulespec Extrapolator, not rkaf-core",
                )
        for name in self.SHARED_SHAPES_REEXPORTED_BY_JUDGEMENT:
            with self.subTest(shared_shape=name):
                self.assertNotIn(
                    name,
                    bound_class_names,
                    f"{name} is now schema-bound, so the sweep above already "
                    "covers it — remove it from "
                    "SHARED_SHAPES_REEXPORTED_BY_JUDGEMENT rather than "
                    "checking it twice and implying the gate is wider than it "
                    "is",
                )
                self.assertIn(
                    name,
                    reexported,
                    f"{name} has no `@type` const, so no compiled JSON Schema "
                    "binds it and the schema-bound sweep cannot see it — it is "
                    "re-exported from the crate root by judgement, and this "
                    "list is what keeps that judgement from being undone by "
                    "accident",
                )


# ── 7. profile isolation ──────────────────────────────────────────────────


class ProfileIsolationCarrierTests(unittest.TestCase):
    """Kernel-only and composed validation differ EXACTLY where documented.

    `constraints/README.md`: a US-bearing document is UNCONSTRAINED by the
    kernel carriers rather than rejected by them, and constrained by the profile
    carriers. Two failure modes hide behind shape parity — the kernel quietly
    enforcing a profile grammar (so a non-adopting consumer rejects valid data)
    and the profile failing to enforce it (so adopting buys nothing) — and both
    leave every compiled artifact looking correct.

    The runtime half of this category is
    `crates/rkaf-runtime/tests/profile_isolation_carrier.rs`.
    """

    KERNEL_ONLY = None
    COMPOSED = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.KERNEL_ONLY = shape_graph(sorted(COMPILED_SHACL_DIR.glob("*.ttl")))
        cls.COMPOSED = shape_graph(compiled_shacl_paths())

    # Negatives whose ONLY defect is a US profile grammar. A kernel-only
    # consumer must accept each (it has no opinion); a profile-loading consumer
    # must reject each.
    PROFILE_ONLY_NEGATIVES = (
        "artifact-us-cfr-malformed-negative",
        "artifact-us-cfr-uppercase-part-negative",
        "artifact-us-cfr-multiletter-part-negative",
        "artifact-us-usc-malformed-negative",
        "artifact-us-frdoc-malformed-negative",
        "artifact-us-frdoc-oversize-sequence-negative",
        "artifact-us-frdoc-short-year-negative",
        "artifact-us-frdoc-legacy-year-negative",
        "artifact-us-regsgov-malformed-negative",
        "artifact-us-pl-malformed-negative",
        "artifact-us-eo-malformed-negative",
    )

    def test_a_us_bearing_document_is_unconstrained_by_the_kernel_alone(self) -> None:
        for name in self.PROFILE_ONLY_NEGATIVES:
            with self.subTest(fixture=name):
                data = expand_file(FIXTURES / "negatives" / f"{name}.jsonld")
                ok, _ = conforms(data, self.KERNEL_ONLY)
                self.assertTrue(
                    ok,
                    f"{name} must PASS kernel-only validation — the kernel "
                    "declares no US identifier grammar, so a consumer that "
                    "never adopted the profile has nothing to reject",
                )

    def test_the_same_document_is_rejected_once_the_profile_loads(self) -> None:
        for name in self.PROFILE_ONLY_NEGATIVES:
            with self.subTest(fixture=name):
                data = expand_file(FIXTURES / "negatives" / f"{name}.jsonld")
                ok, _ = conforms(data, self.COMPOSED)
                self.assertFalse(
                    ok,
                    f"{name} must FAIL once the profile overlay is loaded — "
                    "otherwise adopting the profile buys no enforcement",
                )

    def test_a_kernel_defect_fails_at_both_depths(self) -> None:
        """The control. Without it, `test_a_us_bearing_document_is_
        unconstrained_by_the_kernel_alone` would also pass on a kernel-only
        shape graph that was simply inert — every document conforms to nothing.
        """
        for name in (
            "warrant-missing-warrant-kind-negative",
            "source-fragment-missing-binds-artifact-negative",
        ):
            with self.subTest(fixture=name):
                path = FIXTURES / "negatives" / f"{name}.jsonld"
                kernel_ok, _ = conforms(expand_file(path), self.KERNEL_ONLY)
                composed_ok, _ = conforms(expand_file(path), self.COMPOSED)
                self.assertFalse(
                    kernel_ok,
                    f"{name} violates a KERNEL shape and must fail kernel-only "
                    "validation — the kernel graph has to be live for the "
                    "isolation claim above to mean anything",
                )
                self.assertFalse(
                    composed_ok,
                    f"{name} must also fail composed — SHACL is conjunctive, so "
                    "loading a profile can never relax a kernel constraint",
                )

    # Terms a profile source declares that the KERNEL also declares, each one a
    # deliberate restatement rather than a leak. The list is hard-coded on
    # purpose. Deriving it — as this test once did, by subtracting every term
    # any `constraints/core/*.cue` shape declares — made the assertion below
    # vacuous: a compiled kernel shape names a term only if a kernel CUE source
    # declares it, which is exactly the condition that put the term in the
    # subtracted set. The leak erased itself. Adding a profile term to the
    # kernel now fails this test until someone writes the term and its reason
    # here by hand.
    PROFILE_TERMS_THE_KERNEL_ALSO_OWNS = {
        # Kernel Artifact identity (constraints/core/artifact.cue:39-41). The
        # profile narrows the same three slots for agenda observations.
        "foaf:primaryTopic",
        "rkaf:hasArtifactIdentifier",
        "rkaf:artifactIdentifierScheme",
        # Assertion-envelope terms every kernel assertion form carries; the
        # profile restates them on its own composers.
        "prov:wasDerivedFrom",
        "rkaf:hasAuthority",
        # RefSpec's open-label overlay narrows four universal ValueAssertion
        # fields when the predicate is rkaf:openLabel. The fields remain
        # kernel-owned; the profile adds only openLabelFacet/openLabelRole and
        # the predicate value.
        "rkaf:assertionPolarity",
        "rkaf:assertsValue",
        "rkaf:hasExtractionProvenance",
        "rkaf:assertedAt",
        # The kernel LifecycleEvent property whose value set the profile
        # EXTENDS — the whole point of `#USLifecycleEvent` composing
        # `#LifecycleEvent` rather than minting a class (spec/rkaf-behavior.md
        # §2.1).
        "rkaf:lifecycleEventKind",
    }

    def test_the_kernel_carriers_name_no_profile_term(self) -> None:
        """Every term a profile DECLARES, checked against every kernel and
        analysis shape — not just the two whose local name happens to contain
        "regulatory", and not minus a set derived from the kernel itself.

        `resolve_composition=False` keeps the composed kernel shapes out: a
        profile shape that embeds `#Artifact` would otherwise "declare" every
        kernel Artifact term and make the whole set unusable.
        """
        profile_terms = set()
        for path in sorted((ROOT / "constraints" / "profiles").glob("*/*.cue")):
            doc = cc.parse_cue_file(path, resolve_composition=False)
            for shape in doc.shapes:
                for prop in all_properties(shape):
                    profile_terms.add(prop.name)
        stale_exemptions = sorted(
            self.PROFILE_TERMS_THE_KERNEL_ALSO_OWNS - profile_terms
        )
        self.assertEqual(
            [], stale_exemptions,
            "PROFILE_TERMS_THE_KERNEL_ALSO_OWNS lists a term no profile source "
            "declares any more — an exemption nobody needs silently widens the "
            "hole this test exists to close",
        )
        us_terms = profile_terms - self.PROFILE_TERMS_THE_KERNEL_ALSO_OWNS
        self.assertTrue(us_terms, "the profile must own at least one US term")
        self.assertIn(
            "rkaf:hasRegulatoryIdentifier",
            us_terms,
            "guard: the profile's own identifier term must be in the checked set",
        )
        leaked = []
        kernel_shapes = sorted(COMPILED_SHACL_DIR.glob("*.ttl")) + sorted(
            (ROOT / "compiled" / "shacl" / "analysis").glob("*.ttl")
        )
        self.assertGreater(len(kernel_shapes), 30, "the kernel shape scan must run")
        for path in kernel_shapes:
            text = path.read_text()
            for term in sorted(us_terms):
                if f"sh:path {term} " in text:
                    leaked.append(f"{path.parent.name}/{path.name}: {term}")
        self.assertEqual(
            [], leaked,
            "no compiled KERNEL or ANALYSIS shape may constrain a profile-owned "
            "term — the kernel enforcing a profile grammar makes a non-adopting "
            "consumer reject data it has no opinion about",
        )

    def test_the_profile_overlay_keeps_the_kernel_class(self) -> None:
        """The mechanism the whole category rests on. If an overlay minted its
        own `@type`, the kernel and profile shapes would stop being conjunctive
        over the same nodes — and the runtime would stop seeing profile events
        at all (see the Rust companion test)."""
        bindings = schema_bindings()
        for type_iri, expected_class in (
            ("rkaf:Artifact", "USRegulatoryArtifact"),
            ("rkaf:LifecycleEvent", "USLifecycleEvent"),
        ):
            binding = bindings[type_iri]
            self.assertEqual(
                binding.class_name,
                expected_class,
                f"{type_iri} must be bound by the profile overlay",
            )
            self.assertIn(
                "profiles",
                str(binding.schema_path),
                f"{type_iri}'s binding must come from a profile schema",
            )
        for path in sorted(COMPILED_PROFILE_SHACL_ROOT.glob("*/*.ttl")):
            text = path.read_text()
            if "us-lifecycle-event" in path.name:
                self.assertIn(
                    "sh:targetClass rkaf:LifecycleEvent",
                    text,
                    "the lifecycle overlay must target the SHARED kernel class",
                )
            if "us-regulatory-artifact" in path.name:
                self.assertIn(
                    "sh:targetClass rkaf:Artifact",
                    text,
                    "the artifact overlay must target the SHARED kernel class",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
