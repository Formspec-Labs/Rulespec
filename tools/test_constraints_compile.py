from __future__ import annotations

import json
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from jsonschema import Draft202012Validator

from tools import conformance_lib
from tools.constraints_compile import (
    CompileError,
    _rego_symbol,
    _scan_global_enum_registry,
    _scan_reference_class_registry,
    parse_cue_file,
    target_json_schema,
    target_rego,
    target_rust,
    target_shacl,
    target_typescript,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# The kernel properties that are deliberately EXTENSION POINTS: the kernel
# names the carrier and leaves it unconstrained, and a profile supplies the
# closed value set. FROZEN, and the freeze is the point.
#
# Two audits key off this list, from opposite directions:
#
#   * `LifecycleKindOwnershipTests.test_kernel_carriers_stay_open_on_kind`
#     proves each listed property really is open in every compiled KERNEL
#     carrier — an extension point that quietly acquired a kernel closure
#     would reject the profile values it exists to admit.
#   * `OverlaySupersetTests` allows an overlay to restate a kernel property
#     ONLY when it is on this list. Without the list the exemption keyed on the
#     kernel definition merely BEING `{"type": "string"}` right now, so a future
#     overlay could convert a genuine kernel closure into a profile-only one —
#     a real relaxation of the kernel contract — and pass in silence.
#
# Adding an extension point is therefore a deliberate edit here, reviewed as
# such, not a side effect of loosening a kernel definition somewhere else.
KERNEL_EXTENSION_POINT_PROPERTIES = ("rkaf:lifecycleEventKind",)

# The generic Assertion envelope (constraints/core/assertion.cue). Every one of
# these MUST reach RelationshipAssertion through CUE composition — the envelope
# has exactly one source — and must still arrive in every compiled target.
#
# Composition may DE-DUPLICATE; it must never LOOSEN. A derived shape is
# therefore allowed to restate an envelope field in order to NARROW it (see
# RELATIONSHIP_ASSERTION_NARROWINGS below); what it may not do is arrive at a
# weaker compiled artifact than the CUE source enforces.
#
# The list is grouped the way constraints/core/assertion.cue is: the first two
# entries arrive from `#ConsumerDisposition`, the mutable consumer-scoped half
# the envelope composes; the rest are the envelope's own. `#AssertionProposition`
# — subject, predicate, polarity — is NOT here, and that absence is the point of
# Core §2.3: proposition content is composed by the proposition-bearing forms,
# never by the envelope.
ASSERTION_ENVELOPE_FIELDS = (
    "rkaf:usageEligibility",
    "rkaf:consumerLifecycleState",
    "rkaf:hasAccessScope",
    "rkaf:assertionOrigin",
    "rkaf:hasApplicability",
    "rkaf:hasJustification",
    "rkaf:hasWarrant",
    "rkaf:hasAuthority",
    "prov:wasDerivedFrom",
    "rkaf:hasSourceClaimant",
    "rkaf:hasExtractionProvenance",
    "rkaf:hasConfidence",
    "rkaf:supersedesAssertion",
    "rkaf:assertedAt",
)

# Immutable proposition content (constraints/core/assertion.cue,
# `#AssertionProposition`). Shared by RelationshipAssertion and ValueAssertion;
# the object slot is form-specific and therefore not listed.
ASSERTION_PROPOSITION_FIELDS = (
    "rkaf:assertsSubject",
    "rkaf:assertsPredicate",
    "rkaf:assertionPolarity",
)

# The mutable consumer-scoped disposition (`#ConsumerDisposition`). Core §2.3
# requires these to be structurally separate from the proposition core: an
# assertion's identity never includes them.
CONSUMER_DISPOSITION_FIELDS = (
    "rkaf:usageEligibility",
    "rkaf:consumerLifecycleState",
    "rkaf:hasAccessScope",
)

AI_TOUCHED_ORIGINS = (
    "rkaf:aiSuggested",
    "rkaf:aiPromoted",
    "rkaf:humanQualified",
    "rkaf:humanRevalidation",
)

# The absolute-IRI lexical form RelationshipAssertion demands of its reference
# fields. The generic envelope types them as plain `string`.
IRI_PATTERN = r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$"

# Envelope properties RelationshipAssertion deliberately narrows to an IRI.
RELATIONSHIP_ASSERTION_NARROWED_PROPERTIES = (
    "rkaf:hasApplicability",
    "rkaf:hasJustification",
    "rkaf:hasWarrant",
    "rkaf:hasAuthority",
)

# The fifth narrowing: the envelope's AI-lineage conditionals require
# hasAILineage; RelationshipAssertion additionally requires it to be an IRI.
RELATIONSHIP_ASSERTION_NARROWED_CONDITIONAL = "rkaf:hasAILineage"


class ShapeCompositionTests(unittest.TestCase):
    """CUE shape composition must survive projection to every target.

    A projector that drops composed constraints forces the ontology to
    duplicate shapes (the defect these tests pin down).
    """

    COMPOSED_SOURCE = """
package rkaf

#Origin: "rkaf:human" | "rkaf:ai"

#Envelope: envelope={
	"rkaf:origin":  #Origin
	"rkaf:shared"?: string
	if envelope["rkaf:origin"] == "rkaf:ai" {
		"rkaf:hasLineage": string
	}
}

#Plain: {
	"@type":     "rkaf:Plain"
	"rkaf:only": string
}

#Embedded: {
	#Envelope
	"@type":    "rkaf:Embedded"
	"rkaf:own": string
}

#Conjoined: #Envelope & {
	"rkaf:shared"?: string & =~"^urn:"
}
"""

    def _composed_document(self, temporary: str):
        source = Path(temporary) / "composed.cue"
        source.write_text(self.COMPOSED_SOURCE)
        return parse_cue_file(source)

    def test_embedded_base_shape_projects_properties_and_conditionals(self) -> None:
        """`#Embedded: {#Envelope, ...}` inherits the base's properties AND
        its conditional branches into the compiled JSON Schema."""
        with tempfile.TemporaryDirectory() as temporary:
            document = self._composed_document(temporary)
            schema = json.loads(target_json_schema(document))
            embedded = schema["$defs"]["Embedded"]

            self.assertEqual(
                embedded["properties"]["@type"], {"const": "rkaf:Embedded"}
            )
            self.assertEqual(
                embedded["properties"]["rkaf:origin"],
                {"$ref": "#/$defs/Origin"},
                "composed shape lost the base property type",
            )
            self.assertEqual(
                embedded["properties"]["rkaf:shared"], {"type": "string"}
            )
            self.assertEqual(
                embedded["properties"]["rkaf:own"], {"type": "string"}
            )
            self.assertIn("rkaf:origin", embedded["required"])
            self.assertIn("rkaf:own", embedded["required"])
            self.assertNotIn("rkaf:shared", embedded["required"])
            self.assertIn(
                {
                    "if": {
                        "properties": {
                            "rkaf:origin": {
                                "anyOf": [
                                    {"const": "rkaf:ai"},
                                    {
                                        "type": "array",
                                        "contains": {"const": "rkaf:ai"},
                                    },
                                ]
                            }
                        },
                        "required": ["rkaf:origin"],
                    },
                    "then": {
                        "properties": {"rkaf:hasLineage": {"type": "string"}},
                        "required": ["rkaf:hasLineage"],
                    },
                },
                embedded["allOf"],
                "composed shape lost the base conditional",
            )

    def test_conjunction_base_shape_projects_and_narrows(self) -> None:
        """`#Conjoined: #Envelope & {...}` inherits the base and lets the
        derived body narrow an inherited property."""
        with tempfile.TemporaryDirectory() as temporary:
            document = self._composed_document(temporary)
            schema = json.loads(target_json_schema(document))
            conjoined = schema["$defs"]["Conjoined"]

            self.assertEqual(
                conjoined["properties"]["rkaf:origin"],
                {"$ref": "#/$defs/Origin"},
            )
            self.assertEqual(
                conjoined["properties"]["rkaf:shared"],
                {"type": "string", "pattern": "^urn:"},
                "derived narrowing did not override the inherited property",
            )
            self.assertEqual(len(conjoined["allOf"]), 1)

    def test_non_composed_shape_output_is_unchanged(self) -> None:
        """Composition support must not perturb shapes that do not compose."""
        with tempfile.TemporaryDirectory() as temporary:
            document = self._composed_document(temporary)
            schema = json.loads(target_json_schema(document))
            self.assertEqual(
                schema["$defs"]["Plain"],
                {
                    "type": "object",
                    "properties": {
                        "@type": {"const": "rkaf:Plain"},
                        "rkaf:only": {"type": "string"},
                    },
                    "required": ["@type", "rkaf:only"],
                },
            )

    def test_composed_shape_reaches_rust_typescript_and_shacl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            document = self._composed_document(temporary)

            rust = target_rust(document)
            self.assertIn("pub struct Embedded {", rust)
            self.assertIn("pub origin: Origin,", rust)
            self.assertIn("pub shared: Option<String>,", rust)

            typescript = target_typescript(document)
            self.assertIn("export interface Embedded {", typescript)
            self.assertIn('  "rkaf:origin": Origin;', typescript)
            self.assertIn('  "rkaf:shared"?: string;', typescript)

            shacl = target_shacl(document)
            self.assertIn("rkaf:EmbeddedShape a sh:NodeShape ;", shacl)
            self.assertIn("sh:targetClass rkaf:Embedded ;", shacl)
            self.assertIn("sh:path rkaf:origin ;", shacl)

    def test_disjunction_of_compositions_keeps_base_and_branches(self) -> None:
        """`#Agreement: (#Node & {...}) | (#Node & {...})` — the form already in
        constraints/core/warrant.cue — must project the base shape plus one
        `anyOf` alternative per composed branch."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "agreement.cue"
            source.write_text(
                """
package rkaf

#Kind:   "rkaf:a" | "rkaf:b"
#Family: "rkaf:fa" | "rkaf:fb"

#Node: {
	"@type":       "rkaf:Node"
	"rkaf:kind":   #Kind
	"rkaf:family": #Family
}

#Agreement: (#Node & {
	"rkaf:kind":   "rkaf:a"
	"rkaf:family": "rkaf:fa"
}) | (#Node & {
	"rkaf:kind":   "rkaf:b"
	"rkaf:family": "rkaf:fb"
})
"""
            )
            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            agreement = schema["$defs"]["Agreement"]

            # `@type` is deliberately NOT inherited: `#Agreement` declares no
            # class of its own, and re-binding `rkaf:Node` here would emit a
            # second `@type` const across two `$defs` and a second SHACL
            # NodeShape for the same class. See
            # `test_composed_shape_does_not_rebind_the_base_class`.
            self.assertNotIn("@type", agreement["properties"])
            self.assertEqual(
                agreement["properties"]["rkaf:kind"],
                {"$ref": "#/$defs/Kind"},
                "disjunction-of-compositions dropped the base property",
            )
            self.assertEqual(
                agreement["properties"]["rkaf:family"],
                {"$ref": "#/$defs/Family"},
            )
            self.assertIn(
                {
                    "anyOf": [
                        {
                            "properties": {
                                "rkaf:kind": {"const": "rkaf:a"},
                                "rkaf:family": {"const": "rkaf:fa"},
                            },
                            "required": ["rkaf:kind", "rkaf:family"],
                        },
                        {
                            "properties": {
                                "rkaf:kind": {"const": "rkaf:b"},
                                "rkaf:family": {"const": "rkaf:fb"},
                            },
                            "required": ["rkaf:kind", "rkaf:family"],
                        },
                    ]
                },
                agreement["allOf"],
                "disjunction-of-compositions dropped its branches",
            )

            rust = target_rust(document)
            self.assertIn("pub struct Agreement {", rust)
            self.assertIn("pub kind: Kind,", rust)

            typescript = target_typescript(document)
            self.assertIn("export interface Agreement {", typescript)
            self.assertIn('  "rkaf:kind": Kind;', typescript)

    def test_base_inherited_property_order_survives_composition(self) -> None:
        """Inherited properties keep the base's declaration order, and
        re-narrowing one in the derived body must not move it to the end.

        Property order is load-bearing: it is the field order of the generated
        Rust struct and TypeScript interface, and reordering churns every
        downstream diff."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "ordered.cue"
            source.write_text(
                """
package rkaf

#OrderBase: {
	"rkaf:first":  string & =~"^urn:"
	"rkaf:second": string
	"rkaf:third":  string
}

#OrderDerived: {
	#OrderBase
	"@type":      "rkaf:OrderDerived"
	"rkaf:fourth": string
	"rkaf:second": string & =~"^urn:"
}
"""
            )
            document = parse_cue_file(source)
            derived = next(
                shape
                for shape in document.shapes
                if shape.name == "OrderDerived"
            )
            self.assertEqual(
                [prop.name for prop in derived.properties],
                [
                    "rkaf:first",
                    "rkaf:second",
                    "rkaf:third",
                    "rkaf:fourth",
                ],
                "composition reordered base-inherited properties",
            )
            schema = json.loads(target_json_schema(document))
            self.assertEqual(
                list(schema["$defs"]["OrderDerived"]["properties"]),
                [
                    "@type",
                    "rkaf:first",
                    "rkaf:second",
                    "rkaf:third",
                    "rkaf:fourth",
                ],
            )
            rust = target_rust(document)
            self.assertLess(
                rust.index("pub second:"), rust.index("pub third:")
            )
            self.assertLess(
                rust.index("pub third:"), rust.index("pub fourth:")
            )

    def test_base_inherited_disjunction_survives_composition(self) -> None:
        """A disjunction declared on the base reaches the derived shape."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "disjunctive.cue"
            source.write_text(
                """
package rkaf

#DisjBase: {
	"rkaf:common": string
	{
		"rkaf:alpha": string
	} | {
		"rkaf:beta": string
	}
}

#DisjDerived: {
	#DisjBase
	"@type":     "rkaf:DisjDerived"
	"rkaf:extra": string
}
"""
            )
            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            derived = schema["$defs"]["DisjDerived"]
            self.assertIn(
                {
                    "anyOf": [
                        {
                            "properties": {"rkaf:alpha": {"type": "string"}},
                            "required": ["rkaf:alpha"],
                        },
                        {
                            "properties": {"rkaf:beta": {"type": "string"}},
                            "required": ["rkaf:beta"],
                        },
                    ]
                },
                derived["allOf"],
                "composition dropped the base's disjunction",
            )
            # Disjunction alternatives are alternatives, not always-required.
            self.assertNotIn("rkaf:alpha", derived.get("required", []))
            shacl = target_shacl(document)
            self.assertIn("sh:path rkaf:alpha ; sh:minCount 1", shacl)

    def test_derived_restatement_cannot_drop_a_base_facet(self) -> None:
        """FIX 3 probe: a derived redeclaration without the base's pattern must
        NOT lose the pattern, and a derived `?` must NOT un-require a
        base-required field. CUE unifies; it never widens."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "unify.cue"
            source.write_text(
                """
package rkaf

#UnifyBase: {
	"rkaf:iri":      string & =~"^urn:"
	"rkaf:count":    >=1
	"rkaf:tighter":  >=1
	"rkaf:required": string
}

#UnifyDerived: {
	#UnifyBase
	"@type":          "rkaf:UnifyDerived"
	"rkaf:iri":       string
	"rkaf:count":     int
	"rkaf:tighter":   >=5
	"rkaf:required"?: string
}
"""
            )
            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            derived = schema["$defs"]["UnifyDerived"]

            self.assertEqual(
                derived["properties"]["rkaf:iri"],
                {"type": "string", "pattern": "^urn:"},
                "derived restatement silently dropped the base pattern",
            )
            self.assertEqual(
                derived["properties"]["rkaf:count"],
                {"type": "integer", "minimum": 1},
                "derived restatement silently dropped the base bound",
            )
            # Bounds are the one facet whose conjunction the flat AST can
            # carry: two minima unify to the tighter one, like CUE.
            self.assertEqual(
                derived["properties"]["rkaf:tighter"],
                {"type": "integer", "minimum": 5},
                "conflicting bounds did not unify to the tighter bound",
            )
            self.assertIn(
                "rkaf:required",
                derived["required"],
                "derived `?` un-required a base-required field",
            )

            shacl = target_shacl(document)
            self.assertRegex(
                shacl, r'sh:path rkaf:iri ;[^\n]*sh:pattern "\^urn:"'
            )
            self.assertRegex(
                shacl, r"sh:path rkaf:required ;[^\n]*sh:minCount 1"
            )

    def test_conditional_narrowing_keeps_one_branch_and_the_base_guard(
        self,
    ) -> None:
        """A derived conditional with the same guard unifies with the base's
        rather than replacing it: one branch, carrying the narrowed value."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "conditional.cue"
            source.write_text(
                """
package rkaf

#CondBase: base={
	"rkaf:origin": string
	if base["rkaf:origin"] == "rkaf:ai" {
		"rkaf:lineage": string
	}
}

#CondDerived: derived={
	#CondBase
	"@type": "rkaf:CondDerived"
	if derived["rkaf:origin"] == "rkaf:ai" {
		"rkaf:lineage": string & =~"^urn:"
	}
}
"""
            )
            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            derived = schema["$defs"]["CondDerived"]
            self.assertEqual(
                len(derived["allOf"]),
                1,
                "the narrowed conditional duplicated the base's branch",
            )
            self.assertEqual(
                derived["allOf"][0]["then"],
                {
                    "properties": {
                        "rkaf:lineage": {
                            "type": "string",
                            "pattern": "^urn:",
                        }
                    },
                    "required": ["rkaf:lineage"],
                },
            )

    def test_conflicting_facets_raise_unsupported_composition(self) -> None:
        """Two different values for the same facet are a conjunction the flat
        projector cannot carry. It must raise, never pick one silently."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "conflict.cue"
            source.write_text(
                """
package rkaf

#ConflictBase: {
	"rkaf:iri": string & =~"^urn:"
}

#ConflictDerived: {
	#ConflictBase
	"@type":    "rkaf:ConflictDerived"
	"rkaf:iri": string & =~"^https:"
}
"""
            )
            with self.assertRaises(CompileError) as caught:
                parse_cue_file(source)
            message = str(caught.exception)
            self.assertIn("unsupported composition", message)
            self.assertIn("ConflictDerived", message)
            self.assertIn("rkaf:iri", message)

    def test_unknown_base_ref_raises(self) -> None:
        """An unresolvable base must abort the compile. Skipping it would emit
        a shape missing every constraint the base carries."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "orphan.cue"
            source.write_text(
                """
package rkaf

#Orphan: {
	#NoSuchBase
	"@type":   "rkaf:Orphan"
	"rkaf:own": string
}
"""
            )
            with self.assertRaises(CompileError) as caught:
                parse_cue_file(source)
            message = str(caught.exception)
            self.assertIn("#Orphan", message)
            self.assertIn("#NoSuchBase", message)

    def test_unparseable_sibling_file_raises(self) -> None:
        """A sibling CUE file that fails to parse shrinks the shape registry.
        Silently continuing would resolve a real base to "missing"."""
        with tempfile.TemporaryDirectory() as temporary:
            core = Path(temporary) / "constraints" / "core"
            core.mkdir(parents=True)
            (core / "base.cue").write_text(
                """
package rkaf

#SiblingBase: {
	"rkaf:inherited": string & =~"^urn:"
}
"""
            )
            (core / "broken.cue").write_bytes(b"package rkaf\n\xff\xfe not utf-8\n")
            derived = core / "derived.cue"
            derived.write_text(
                """
package rkaf

#SiblingDerived: {
	#SiblingBase
	"@type":    "rkaf:SiblingDerived"
	"rkaf:own": string
}
"""
            )
            with self.assertRaises(CompileError) as caught:
                parse_cue_file(derived)
            self.assertIn("broken.cue", str(caught.exception))

    def test_cyclic_composition_raises(self) -> None:
        """A composition cycle must raise a named error rather than emitting
        silently asymmetric partial shapes."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "cycle.cue"
            source.write_text(
                """
package rkaf

#CycleA: {
	#CycleB
	"rkaf:a": string
}

#CycleB: {
	#CycleA
	"rkaf:b": string
}
"""
            )
            with self.assertRaises(CompileError) as caught:
                parse_cue_file(source)
            message = str(caught.exception)
            self.assertIn("cyclic", message)
            self.assertIn("CycleA", message)
            self.assertIn("CycleB", message)

    def test_cross_file_composition_resolves_through_shape_registry(
        self,
    ) -> None:
        """The real cross-file path: the base lives in a sibling CUE file and
        resolves through `_shape_registry`, exactly as #AssertionEnvelope does
        for #RelationshipAssertion."""
        with tempfile.TemporaryDirectory() as temporary:
            core = Path(temporary) / "constraints" / "core"
            core.mkdir(parents=True)
            (core / "envelope.cue").write_text(
                """
package rkaf

#CrossEnvelope: envelope={
	"rkaf:origin":  string
	"rkaf:shared"?: string
	if envelope["rkaf:origin"] == "rkaf:ai" {
		"rkaf:lineage": string
	}
}
"""
            )
            derived_path = core / "derived.cue"
            derived_path.write_text(
                """
package rkaf

#CrossDerived: {
	#CrossEnvelope
	"@type":     "rkaf:CrossDerived"
	"rkaf:own":  string
	"rkaf:shared"?: string & =~"^urn:"
}
"""
            )
            document = parse_cue_file(derived_path)
            # The base lives in another file, so it must not appear here.
            self.assertEqual(
                [shape.name for shape in document.shapes], ["CrossDerived"]
            )
            schema = json.loads(target_json_schema(document))
            derived = schema["$defs"]["CrossDerived"]
            self.assertEqual(
                derived["properties"]["rkaf:origin"], {"type": "string"}
            )
            self.assertEqual(
                derived["properties"]["rkaf:shared"],
                {"type": "string", "pattern": "^urn:"},
            )
            self.assertIn("rkaf:origin", derived["required"])
            self.assertEqual(
                derived["allOf"][0]["then"]["required"], ["rkaf:lineage"]
            )

    def test_composed_shape_does_not_rebind_the_base_class(self) -> None:
        """A shape that acquires its fields by composition must not acquire the
        base's `@type`: doing so emits a second SHACL NodeShape for the base's
        class and a duplicate `@type` const across two `$defs`."""
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "rebind.cue"
            source.write_text(
                """
package rkaf

#ClassBase: {
	"@type":     "rkaf:ClassBase"
	"rkaf:kind": string
}

#ClassSilent: {
	#ClassBase
	"rkaf:extra": string
}
"""
            )
            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            self.assertEqual(
                schema["$defs"]["ClassBase"]["properties"]["@type"],
                {"const": "rkaf:ClassBase"},
            )
            self.assertNotIn(
                "@type",
                schema["$defs"]["ClassSilent"]["properties"],
                "composition re-bound the base's class identity",
            )
            shacl = target_shacl(document)
            self.assertEqual(shacl.count("sh:targetClass rkaf:ClassBase ;"), 1)
            self.assertNotIn("rkaf:ClassSilentShape", shacl)


class GeneratedShapeIdentityTests(unittest.TestCase):
    """Generated SHACL must never claim a class IRI it did not declare."""

    @staticmethod
    def _generated_shacl() -> dict[str, str]:
        """`{cue file: compiled SHACL}` for every shipped constraint."""
        return {
            str(path.relative_to(REPO_ROOT)): target_shacl(
                parse_cue_file(path),
                reference_classes=_scan_reference_class_registry(path),
            )
            for path in sorted(REPO_ROOT.glob("constraints/*/*.cue"))
        }

    @staticmethod
    def _node_shapes(turtle: str) -> list[tuple[str, str]]:
        return re.findall(
            r"^(rkaf:\w+Shape) a sh:NodeShape ;\n  sh:targetClass (\S+) ;",
            turtle,
            re.MULTILINE,
        )

    def test_no_cue_file_generates_two_shapes_for_one_class(self) -> None:
        """Inheriting a base's `@type` made warrant.cue emit both
        rkaf:WarrantShape and rkaf:WarrantFamilyKindAgreementShape targeting
        rkaf:Warrant. One CUE file must bind each class exactly once."""
        for name, turtle in self._generated_shacl().items():
            targets = [target for _, target in self._node_shapes(turtle)]
            duplicates = {t for t in targets if targets.count(t) > 1}
            self.assertEqual(
                duplicates,
                set(),
                f"{name} generates two NodeShapes for the same class",
            )

    def test_generated_shape_iris_do_not_collide_with_pattern_c(self) -> None:
        """rkaf:WarrantFamilyKindAgreementShape is hand-authored and normative
        (shapes/rkaf-shapes-pattern-c.ttl). No generated shape may claim that
        IRI — a generated redefinition would silently replace the normative
        family/kind agreement rule with a per-property projection."""
        hand_authored = REPO_ROOT / "shapes" / "rkaf-shapes-pattern-c.ttl"
        hand_iris = {
            iri for iri, _ in self._node_shapes(hand_authored.read_text())
        }
        self.assertIn("rkaf:WarrantFamilyKindAgreementShape", hand_iris)

        generated_iris = {
            iri
            for turtle in self._generated_shacl().values()
            for iri, _ in self._node_shapes(turtle)
        }
        self.assertEqual(
            hand_iris & generated_iris,
            set(),
            "a generated SHACL shape collides with a Pattern-C shape IRI",
        )


class ConstraintCompilerTests(unittest.TestCase):
    def test_relationship_assertion_inherits_envelope_by_composition(self) -> None:
        """RelationshipAssertion must obtain the generic Assertion envelope by
        CUE composition, and every target must still receive every envelope
        field.

        This is a SEMANTIC check, not a textual one. Asserting that envelope
        field names are absent from the CUE text would forbid the legitimate
        derived-shape narrowings this class declares (see
        `test_relationship_assertion_narrowings_reach_every_target`); what
        matters is that the envelope is embedded rather than forked, and that
        the compiled schema carries the whole envelope.
        """
        root = REPO_ROOT
        source = root / "constraints" / "core" / "relationship-assertion.cue"
        text = source.read_text()

        # The envelope must arrive by embedding — a bare `#AssertionEnvelope`
        # line inside the shape body, which is CUE struct embedding — and not
        # as a hand-copied block of fields.
        self.assertRegex(
            text,
            r"(?m)^\s*#AssertionEnvelope\s*$",
            "RelationshipAssertion must embed the shared Assertion envelope",
        )

        assertion_doc = parse_cue_file(
            root / "constraints" / "core" / "assertion.cue"
        )
        envelope = next(
            shape
            for shape in assertion_doc.shapes
            if shape.name == "AssertionEnvelope"
        )
        # Every envelope field is declared once, in the envelope.
        self.assertEqual(
            {prop.name for prop in envelope.properties},
            set(ASSERTION_ENVELOPE_FIELDS),
            "the envelope definition drifted from the fields under test",
        )
        relationship_doc = parse_cue_file(source)
        assertion = next(
            shape
            for shape in assertion_doc.shapes
            if shape.name == "Assertion"
        )
        relationship = next(
            shape
            for shape in relationship_doc.shapes
            if shape.name == "RelationshipAssertion"
        )

        assertion_fields = {prop.name for prop in assertion.properties}
        relationship_fields = {prop.name for prop in relationship.properties}
        self.assertLessEqual(
            assertion_fields,
            relationship_fields,
            "RelationshipAssertion drifted from the generic Assertion envelope",
        )
        self.assertTrue(
            {
                "rkaf:assertsSubject",
                "rkaf:assertsPredicate",
                "rkaf:assertsObject",
                "rkaf:assertionPolarity",
            }
            <= relationship_fields
        )

        def conditions(shape) -> set:
            """Guard + required-field names. Deliberately ignores the value
            shape of the required field: RelationshipAssertion narrows
            hasAILineage to an IRI, which is a narrowing, not a drift."""
            return {
                (
                    condition.when_property,
                    condition.when_equals,
                    tuple(prop.name for prop in condition.then_require),
                )
                for condition in shape.conditionals
            }

        self.assertEqual(
            conditions(assertion),
            conditions(relationship),
            "RelationshipAssertion AI-lineage rules drifted from Assertion",
        )

        registry = _scan_global_enum_registry(source)
        schema = json.loads(
            target_json_schema(relationship_doc, registry=registry)
        )
        composed = schema["$defs"]["RelationshipAssertion"]
        self.assertEqual(
            composed["properties"]["@type"],
            {"const": "rkaf:RelationshipAssertion"},
        )
        for field_name in ASSERTION_ENVELOPE_FIELDS:
            self.assertIn(
                field_name,
                composed["properties"],
                f"{field_name} did not survive composition to JSON Schema",
            )
        self.assertIn("rkaf:assertionOrigin", composed["required"])
        lineage_branches = [
            branch
            for branch in composed["allOf"]
            if branch.get("then", {}).get("required") == ["rkaf:hasAILineage"]
        ]
        self.assertEqual(
            len(lineage_branches),
            len(AI_TOUCHED_ORIGINS),
            "AI-lineage conditionals did not survive composition",
        )

        typescript = target_typescript(relationship_doc, registry=registry)
        self.assertIn(
            'import type { AssertionOrigin } from "./assertion";',
            typescript,
        )
        self.assertIn(
            'import type { UsageEligibility } from "./usage-eligibility";',
            typescript,
        )
        self.assertIn('  "rkaf:usageEligibility"?: UsageEligibility;', typescript)
        self.assertIn('  "rkaf:assertionOrigin": AssertionOrigin;', typescript)

        rust = target_rust(relationship_doc, registry=registry)
        self.assertIn("pub struct RelationshipAssertion {", rust)
        self.assertIn(
            "pub assertion_origin: crate::generated::assertion::AssertionOrigin,",
            rust,
        )
        self.assertIn(
            "pub usage_eligibility: "
            "Option<crate::generated::usage_eligibility::UsageEligibility>,",
            rust,
        )

        shacl = target_shacl(
            relationship_doc,
            reference_classes=_scan_reference_class_registry(source),
        )
        self.assertIn("sh:targetClass rkaf:RelationshipAssertion ;", shacl)
        for field_name in ASSERTION_ENVELOPE_FIELDS:
            self.assertIn(
                f"sh:path {field_name} ;",
                shacl,
                f"{field_name} did not survive composition to SHACL",
            )

        # The Rego target is closed-enum only by design (module docstring), so
        # it carries no inherited properties; assert it still projects the
        # composed document rather than failing on it. `#AssertionPolarity`
        # now lives in assertion.cue with the rest of the proposition core —
        # ValueAssertion closes over the same two values — so the value set is
        # emitted by THAT module's Rego, and this one legitimately carries no
        # enum of its own.
        rego = target_rego(relationship_doc)
        self.assertIn("package rkaf.relationship_assertion", rego)
        self.assertIn(
            'assertion_polarity_values := ["rkaf:affirmed", "rkaf:denied"]',
            target_rego(assertion_doc),
        )

    def test_relationship_assertion_narrowings_reach_every_target(self) -> None:
        """The five deliberate RelationshipAssertion narrowings of the shared
        envelope must survive composition into the compiled artifacts.

        The generic envelope types hasApplicability / hasJustification /
        hasWarrant / hasAuthority and the conditional hasAILineage as plain
        `string`; RelationshipAssertion additionally requires each to be an
        absolute IRI. Composition that dropped these would leave `cue vet`
        enforcing a rule no generated validator checks.
        """
        source = REPO_ROOT / "constraints" / "core" / "relationship-assertion.cue"
        document = parse_cue_file(source)
        registry = _scan_global_enum_registry(source)
        composed = json.loads(
            target_json_schema(document, registry=registry)
        )["$defs"]["RelationshipAssertion"]

        for field_name in RELATIONSHIP_ASSERTION_NARROWED_PROPERTIES:
            self.assertEqual(
                composed["properties"][field_name],
                {"type": "string", "pattern": IRI_PATTERN},
                f"{field_name} lost its RelationshipAssertion IRI narrowing",
            )

        lineage_branches = [
            branch
            for branch in composed["allOf"]
            if branch.get("then", {})
            .get("required", [])
            == [RELATIONSHIP_ASSERTION_NARROWED_CONDITIONAL]
        ]
        self.assertEqual(len(lineage_branches), len(AI_TOUCHED_ORIGINS))
        for branch in lineage_branches:
            self.assertEqual(
                branch["then"]["properties"][
                    RELATIONSHIP_ASSERTION_NARROWED_CONDITIONAL
                ],
                {"type": "string", "pattern": IRI_PATTERN},
                "AI-lineage conditional lost its IRI narrowing",
            )

        shacl = target_shacl(
            document,
            reference_classes=_scan_reference_class_registry(source),
        )
        for field_name in RELATIONSHIP_ASSERTION_NARROWED_PROPERTIES:
            self.assertRegex(
                shacl,
                rf"sh:path {re.escape(field_name)} ;[^\n]*"
                rf"sh:pattern {re.escape(json.dumps(IRI_PATTERN))}",
                f"{field_name} narrowing did not reach SHACL",
            )
        self.assertEqual(
            shacl.count(
                f"sh:path {RELATIONSHIP_ASSERTION_NARROWED_CONDITIONAL} ; "
                f"sh:minCount 1 ; sh:pattern {json.dumps(IRI_PATTERN)}"
            ),
            len(AI_TOUCHED_ORIGINS),
            "AI-lineage narrowing did not reach SHACL",
        )

        typescript = target_typescript(document, registry=registry)
        for field_name in RELATIONSHIP_ASSERTION_NARROWED_PROPERTIES:
            self.assertIn(
                f"{field_name}: pattern mismatch",
                typescript,
                f"{field_name} narrowing did not reach TypeScript",
            )

    def test_patterns_dates_and_order_project_from_aliased_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "interval.cue"
            source.write_text(
                """
package rkaf

import "time"

#Interval: I={
    "@type": "rkaf:Interval"
    "rkaf:links": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:.+$")]
    "rkaf:scheme"?: string
    "rkaf:start": time.Format("2006-01-02")
    "rkaf:end": time.Format("2006-01-02")
    if I["rkaf:scheme"] != _|_ {
        "rkaf:identifier": string
    }
    if I["rkaf:start"] > I["rkaf:end"] {
        _|_
    }
}
"""
            )

            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            interval = schema["$defs"]["Interval"]

            link_schema = interval["properties"]["rkaf:links"]
            self.assertEqual(
                link_schema["anyOf"][1]["items"]["pattern"],
                "^[A-Za-z][A-Za-z0-9+.-]*:.+$",
            )
            self.assertEqual(
                interval["properties"]["rkaf:start"]["format"],
                "date",
            )
            self.assertEqual(
                interval["properties"]["rkaf:start"]["pattern"],
                r"^\d{4}-\d{2}-\d{2}$",
            )
            self.assertEqual(
                interval["x-rkaf-order"],
                [{"lower": "rkaf:start", "upper": "rkaf:end"}],
            )
            self.assertIn(
                {
                    "if": {"required": ["rkaf:scheme"]},
                    "then": {
                        "properties": {
                            "rkaf:identifier": {"type": "string"}
                        },
                        "required": ["rkaf:identifier"],
                    },
                },
                interval["allOf"],
            )

            shacl = target_shacl(document)
            self.assertIn(
                "@prefix prov: <http://www.w3.org/ns/prov#> .",
                shacl,
            )
            self.assertIn('sh:pattern "^[A-Za-z][A-Za-z0-9+.-]*:.+$"', shacl)
            self.assertIn("sh:datatype xsd:date", shacl)
            self.assertIn(
                "sh:lessThanOrEquals rkaf:end",
                shacl,
            )
            self.assertIn("sh:path rkaf:scheme ; sh:minCount 1", shacl)
            self.assertIn("sh:path rkaf:scheme ; sh:maxCount 1", shacl)
            self.assertIn("sh:path rkaf:identifier ; sh:minCount 1", shacl)

            typescript = target_typescript(document)
            self.assertIn("function isRkafDate", typescript)
            self.assertIn('!isRkafDate(v["rkaf:start"])', typescript)
            self.assertIn(
                'const condition1 = record["rkaf:scheme"] !== undefined',
                typescript,
            )
            self.assertIn(
                'rkaf:identifier: required by rkaf:scheme',
                typescript,
            )

    def test_reference_ranges_project_to_shacl_classes(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = (
            root / "constraints" / "profiles" / "us-rulemaking"
            / "rulemaking.cue"
        )
        document = parse_cue_file(source)
        ranges = _scan_reference_class_registry(source)
        shacl = target_shacl(document, reference_classes=ranges)
        self.assertRegex(
            shacl,
            r"sh:path rkaf:hasDocket ;[^\n]*sh:class rkaf:Docket",
        )
        self.assertRegex(
            shacl,
            r"sh:path rkaf:commentPeriodFor ;[^\n]*sh:class rkaf:Proceeding",
        )
        artifact_source = root / "constraints" / "core" / "artifact.cue"
        artifact_document = parse_cue_file(artifact_source)
        artifact_ranges = _scan_reference_class_registry(artifact_source)
        artifact_shacl = target_shacl(
            artifact_document,
            reference_classes=artifact_ranges,
        )
        self.assertRegex(
            artifact_shacl,
            r"sh:path prov:wasRevisionOf ;[^\n]*sh:class rkaf:Artifact",
        )
        self.assertIn("@prefix dcat: <http://www.w3.org/ns/dcat#> .", shacl)
        self.assertIn("@prefix foaf: <http://xmlns.com/foaf/0.1/> .", shacl)

    def test_forbidden_pattern_projects_to_all_shape_validators(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = (
            root / "constraints" / "profiles" / "us-rulemaking"
            / "rulemaking.cue"
        )
        document = parse_cue_file(source)
        agenda_identifier_scheme = next(
            enum for enum in document.enums
            if enum.name == "AgendaItemIdentifierScheme"
        )
        self.assertEqual(agenda_identifier_scheme.values, ["rkaf:us-rin"])

        schema = json.loads(target_json_schema(document))
        identifier = schema["$defs"]["Proceeding"]["properties"][
            "rkaf:hasProceedingIdentifier"
        ]
        self.assertEqual(
            identifier["not"]["pattern"],
            r"^urn:rkaf:us:(rin|regsgov):",
        )

        shacl = target_shacl(document)
        self.assertIn(
            'sh:not [ sh:pattern "^urn:rkaf:us:(rin|regsgov):" ; ]',
            shacl,
        )

        typescript = target_typescript(document)
        self.assertIn(
            'rkaf:hasProceedingIdentifier: forbidden pattern match',
            typescript,
        )

    def test_optional_nonempty_list_is_absent_or_nonempty(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = (
            root / "constraints" / "profiles" / "us-rulemaking"
            / "rulemaking.cue"
        )
        document = parse_cue_file(source)
        schema = json.loads(target_json_schema(document))
        proceeding = schema["$defs"]["Proceeding"]
        has_authority = proceeding["properties"]["rkaf:hasAuthority"]

        self.assertNotIn("rkaf:hasAuthority", proceeding["required"])
        self.assertEqual(has_authority["anyOf"][1]["minItems"], 1)

        shacl = target_shacl(document)
        has_authority_line = next(
            line for line in shacl.splitlines()
            if "sh:path rkaf:hasAuthority" in line
        )
        self.assertNotIn("sh:minCount", has_authority_line)


class KernelProfileBoundaryTests(unittest.TestCase):
    """The kernel never depends on a profile.

    `profiles depend on reusable contracts; the kernel never depends on a
    profile` is the module-boundary rule this repository has to keep
    mechanically, not by review habit. These tests fail the build the moment a
    jurisdiction-specific term or a profile shape reference lands in
    `constraints/core/`.
    """

    KERNEL_DIR = REPO_ROOT / "constraints" / "core"
    PROFILES_DIR = REPO_ROOT / "constraints" / "profiles"

    def _profile_definition_names(self) -> set[str]:
        names: set[str] = set()
        for cue in sorted(self.PROFILES_DIR.rglob("*.cue")):
            for match in re.finditer(r"^#(\w+):", cue.read_text(), re.MULTILINE):
                names.add(match.group(1))
        return names

    def test_kernel_never_references_a_profile_definition(self) -> None:
        profile_names = self._profile_definition_names()
        self.assertIn(
            "USRegulatoryArtifact",
            profile_names,
            "profile scan found no US rulemaking shapes — the test is not "
            "actually looking at the profile tree",
        )
        kernel_names = set()
        for cue in sorted(self.KERNEL_DIR.glob("*.cue")):
            for match in re.finditer(r"^#(\w+):", cue.read_text(), re.MULTILINE):
                kernel_names.add(match.group(1))
        for cue in sorted(self.KERNEL_DIR.glob("*.cue")):
            referenced = set(re.findall(r"#(\w+)", cue.read_text()))
            leaked = sorted((referenced & profile_names) - kernel_names)
            self.assertEqual(
                [],
                leaked,
                f"constraints/core/{cue.name} references profile shape(s) "
                f"{leaked}. The kernel MUST NOT depend on a profile; move the "
                "consumer into the profile instead.",
            )

    def test_kernel_declares_no_us_jurisdiction_terms(self) -> None:
        for cue in sorted(self.KERNEL_DIR.glob("*.cue")):
            text = cue.read_text()
            self.assertEqual(
                [],
                sorted(set(re.findall(r'"(rkaf:us-[\w-]+)"', text))),
                f"constraints/core/{cue.name} declares a US identifier scheme. "
                "US regulatory identity belongs to "
                "constraints/profiles/us-rulemaking/.",
            )
            self.assertNotIn(
                "urn:rkaf:us:",
                text,
                f"constraints/core/{cue.name} encodes a US citation grammar. "
                "Those grammars belong to constraints/profiles/us-rulemaking/.",
            )

    def test_kernel_declares_no_proceeding_scoped_value(self) -> None:
        """No `rkaf:proceeding*` string may appear anywhere under core/.

        A proceeding is a rulemaking construct. The twelve proceeding lifecycle
        kinds live in `constraints/profiles/us-rulemaking/us-lifecycle-event.cue`
        and reach `rkaf:LifecycleEvent` through the composed profile shape, so
        the kernel has no reason to mention one — in an enum, a pattern, or a
        comment.
        """
        for cue in sorted(self.KERNEL_DIR.rglob("*.cue")):
            self.assertEqual(
                [],
                sorted(set(re.findall(r"rkaf:proceeding\w*", cue.read_text()))),
                f"constraints/core/{cue.name} mentions a proceeding-scoped "
                "value. Those belong to constraints/profiles/us-rulemaking/; "
                "the kernel owns only the universal lifecycle kinds.",
            )


class CrossFileEnumRegistryTests(unittest.TestCase):
    """The registry that lets one file's closure name another file's values.

    Every emitter that can express a closed value set now resolves through it,
    so two properties matter beyond "does it find the values":

      * it must be DETERMINISTIC — the registry feeds SHACL and Rego closures,
        and a value set that depends on directory-walk order is a compiled
        artifact that depends on the machine that built it;
      * a name must resolve to exactly ONE definition, because first-wins over
        a duplicate silently picks a value set and the losing file's closure
        vanishes without a diagnostic.
    """

    def _tree(self, root: str, files: dict[str, str]) -> Path:
        """Write a miniature `constraints/` tree, return one file inside it."""
        constraints = Path(root) / "constraints"
        for relpath, text in files.items():
            path = constraints / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return constraints / next(iter(files))

    KERNEL_PART = """
package rkaf

#Kind: "rkaf:a" | "rkaf:b"
"""

    PROFILE_UNION = """
package rkaf

#ProfileKind:  "rkaf:c"
#ComposedKind: #Kind | #ProfileKind

#Event: {
	"@type":    "rkaf:Event"
	"rkaf:kind": #ComposedKind
}
"""

    def test_rego_emits_unions_resolved_across_files(self) -> None:
        """The F1 regression, at the unit level.

        `target_rego` used to iterate `doc.enums` only, so a union naming the
        whole-contract set produced no Rego symbol at all and the target
        shipped the profile's part alone.
        """
        with tempfile.TemporaryDirectory() as temporary:
            self._tree(
                temporary,
                {
                    "core/kernel.cue": self.KERNEL_PART,
                    "profiles/p/overlay.cue": self.PROFILE_UNION,
                },
            )
            overlay = Path(temporary) / "constraints" / "profiles" / "p" / "overlay.cue"
            registry = _scan_global_enum_registry(overlay)
            rego = target_rego(
                parse_cue_file(overlay), registry=registry, source_file=overlay
            )
            self.assertIn('profile_kind_values := ["rkaf:c"]', rego)
            self.assertIn(
                'composed_kind_values := ["rkaf:a", "rkaf:b", "rkaf:c"]',
                rego,
                "the Rego target dropped the assembled union — the closed "
                "whole-contract set exists in every other target and not here.",
            )

    def test_rego_union_that_resolves_nowhere_raises(self) -> None:
        """A union Rego cannot assemble must abort, not emit a partial set."""
        with tempfile.TemporaryDirectory() as temporary:
            overlay = self._tree(
                temporary, {"profiles/p/overlay.cue": self.PROFILE_UNION}
            )
            with self.assertRaises(CompileError):
                target_rego(parse_cue_file(overlay), registry={}, source_file=overlay)

    def test_duplicate_enum_name_across_files_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            anchor = self._tree(
                temporary,
                {
                    "core/kernel.cue": self.KERNEL_PART,
                    "core/other.cue": self.KERNEL_PART,
                },
            )
            with self.assertRaises(CompileError) as caught:
                _scan_global_enum_registry(anchor)
            self.assertIn("#Kind", str(caught.exception))

    def test_duplicate_union_name_across_files_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            anchor = self._tree(
                temporary,
                {
                    "core/kernel.cue": self.KERNEL_PART,
                    "profiles/p/overlay.cue": self.PROFILE_UNION,
                    "profiles/q/overlay.cue": self.PROFILE_UNION,
                },
            )
            with self.assertRaises(CompileError):
                _scan_global_enum_registry(anchor)

    def test_repository_declares_no_duplicate_enum_names(self) -> None:
        """The real tree: 57 names, each declared once.

        Scanning without raising IS the assertion; the count is a guard so a
        tree that stopped being scanned cannot pass vacuously.
        """
        registry = _scan_global_enum_registry(
            REPO_ROOT / "constraints" / "core" / "lifecycle-event.cue"
        )
        self.assertGreaterEqual(
            len(registry),
            57,
            "the enum registry shrank — a definition stopped being scanned.",
        )

    def test_registry_scan_does_not_depend_on_filesystem_order(self) -> None:
        """Walk the same tree in reverse; get the same registry.

        `rglob` yields in directory order, which differs between filesystems.
        With the walk sorted AND duplicates rejected, the assembled value sets
        — and therefore the pinned contract digest — are the same everywhere.
        """
        with tempfile.TemporaryDirectory() as temporary:
            anchor = self._tree(
                temporary,
                {
                    "core/kernel.cue": self.KERNEL_PART,
                    "profiles/p/overlay.cue": self.PROFILE_UNION,
                },
            )
            forward = _scan_global_enum_registry(anchor)
            unsorted_rglob = Path.rglob

            def reverse_rglob(self, pattern):  # noqa: ANN001
                return reversed(sorted(unsorted_rglob(self, pattern)))

            with unittest.mock.patch.object(Path, "rglob", reverse_rglob):
                backward = _scan_global_enum_registry(anchor)
            self.assertEqual(
                {name: getattr(entry, "values", getattr(entry, "refs", None))
                 for name, entry in forward.items()},
                {name: getattr(entry, "values", getattr(entry, "refs", None))
                 for name, entry in backward.items()},
            )


class LifecycleKindOwnershipTests(unittest.TestCase):
    """Every `rkaf:LifecycleEvent` kind is owned by EXACTLY ONE module.

    One class, one property, one closed value set — assembled at build time
    from parts each of which has a single declaring module (the kernel, or one
    profile). This audit replaces the interim
    `test_kernel_domain_value_debt_does_not_grow` allowlist, which could only
    say "the debt did not grow"; the questions that matter after the split are
    ownership questions:

      (i)   no value appears in a compiled artifact without a declaring module,
            and no value is declared by two modules;
      (ii)  the kernel's part is exactly the ten universal kinds;
      (iii) the assembled union equals kernel + sum(profiles) — no orphan
            (declared but never assembled) and no duplicate.

    Everything is derived structurally rather than hardcoded: the audit finds
    the shape that CLOSES `rkaf:lifecycleEventKind`, reads the union it binds,
    and resolves that union's parts to the files that declare them. Renaming a
    definition or adding a second profile does not need an edit here; declaring
    a kind twice, or in no module, fails.
    """

    CONSTRAINTS_DIR = REPO_ROOT / "constraints"
    COMPILED_JSON_SCHEMA = REPO_ROOT / "compiled" / "json-schema"
    COMPILED_SHACL = REPO_ROOT / "compiled" / "shacl"
    COMPILED_TYPESCRIPT = REPO_ROOT / "compiled" / "typescript"
    COMPILED_REGO = REPO_ROOT / "compiled" / "rego"
    GENERATED_RUST = REPO_ROOT / "crates" / "rkaf-core" / "src" / "generated"
    KIND_PROPERTY = "rkaf:lifecycleEventKind"
    EVENT_CLASS = "rkaf:LifecycleEvent"

    # The ten kinds the KERNEL owns: events that happen to a governed assertion
    # in ANY jurisdiction. FROZEN — this is what turns the audit from a
    # `rkaf:proceeding*` prefix scan into a real gate. A kernel kind that is not
    # on this list fails whatever it is called, so smuggling a domain value into
    # the kernel under a name like `rkaf:hearingScheduled` is caught too.
    UNIVERSAL_LIFECYCLE_EVENT_KINDS = (
        "rkaf:revalidation",
        "rkaf:revalidationClosure",
        "rkaf:amendment",
        "rkaf:supersession",
        "rkaf:rescission",
        "rkaf:materialRevision",
        "rkaf:editorialRevision",
        "rkaf:conceptLifecycle",
        "rkaf:promotion",
        "rkaf:demotion",
    )

    # ---- declaration side (CUE source) --------------------------------

    def _cue_documents(self) -> dict[str, object]:
        """`{constraints-relative path: parsed doc}` for every CUE source."""
        return {
            path.relative_to(self.CONSTRAINTS_DIR).with_suffix("").as_posix():
                parse_cue_file(path, resolve_composition=False)
            for path in sorted(self.CONSTRAINTS_DIR.rglob("*.cue"))
        }

    def _closing_union_name(self, documents: dict[str, object]) -> str:
        """The enum/union that CLOSES the kind property, found structurally."""
        closers: list[tuple[str, str]] = []
        for relpath, document in documents.items():
            for shape in document.shapes:
                if shape.type_iri != self.EVENT_CLASS:
                    continue
                for prop in shape.properties:
                    if prop.name == self.KIND_PROPERTY and prop.enum_ref:
                        closers.append((relpath, prop.enum_ref))
        self.assertEqual(
            1,
            len(closers),
            "exactly one CUE shape may close "
            f"{self.KIND_PROPERTY} over a value set; found {closers}. Zero "
            "means nothing enforces the closed set; two means two disagreeing "
            "closed sets bind the same class.",
        )
        return closers[0][1]

    def _parts(self) -> tuple[str, dict[str, tuple[str, ...]]]:
        """`(union name, {declaring module: values})` for the assembled union."""
        documents = self._cue_documents()
        union_name = self._closing_union_name(documents)
        union = next(
            (
                candidate
                for document in documents.values()
                for candidate in document.enum_unions
                if candidate.name == union_name
            ),
            None,
        )
        self.assertIsNotNone(
            union,
            f"#{union_name} closes {self.KIND_PROPERTY} but is not a union of "
            "per-module parts. The whole-contract value set must be assembled "
            "from named parts so each value has a declaring module.",
        )
        parts: dict[str, tuple[str, ...]] = {}
        for ref in union.refs:
            declaring = [
                (relpath, enum)
                for relpath, document in documents.items()
                for enum in document.enums
                if enum.name == ref
            ]
            self.assertEqual(
                1,
                len(declaring),
                f"union member #{ref} must be declared by exactly one CUE "
                f"file; found {[relpath for relpath, _ in declaring]}.",
            )
            relpath, enum = declaring[0]
            self.assertNotIn(
                relpath,
                parts,
                f"{relpath} contributes two parts to #{union_name}; one module "
                "declares one part, or 'which module owns this value' has no "
                "single answer.",
            )
            parts[relpath] = tuple(enum.values)
        return union_name, parts

    # ---- compiled side ------------------------------------------------

    def _compiled_shacl_closures(
        self, prop: str | None = None
    ) -> dict[str, frozenset[str] | None]:
        """`{compiled TTL: sh:in values on `prop`}` (None = open)."""
        prop = prop or self.KIND_PROPERTY
        found: dict[str, frozenset[str] | None] = {}
        for path in sorted(self.COMPILED_SHACL.rglob("*.ttl")):
            for line in path.read_text().splitlines():
                if f"sh:path {prop} ;" not in line:
                    continue
                closure = re.search(r"sh:in \(([^)]*)\)", line)
                found[path.relative_to(self.COMPILED_SHACL).as_posix()] = (
                    frozenset(closure.group(1).split()) if closure else None
                )
        return found

    def _compiled_schema_closures(
        self, prop: str | None = None
    ) -> dict[str, tuple[str, ...] | None]:
        """`{compiled schema: enum on `prop`}` (None = open)."""
        prop = prop or self.KIND_PROPERTY
        found: dict[str, tuple[str, ...] | None] = {}
        for path in sorted(self.COMPILED_JSON_SCHEMA.rglob("*.schema.json")):
            document = json.loads(path.read_text())
            defs = document.get("$defs", {})
            for class_schema in defs.values():
                if not isinstance(class_schema, dict):
                    continue
                definition = class_schema.get("properties", {}).get(prop)
                if definition is None:
                    continue
                reference = definition.get("$ref", "")
                if reference.startswith("#/$defs/"):
                    definition = defs.get(reference.removeprefix("#/$defs/"), {})
                values = definition.get("enum")
                found[
                    path.relative_to(self.COMPILED_JSON_SCHEMA).as_posix()
                ] = tuple(values) if isinstance(values, list) else None
        return found

    def _compiled_typescript_closures(
        self, prop: str | None = None
    ) -> dict[str, tuple[str, ...] | None]:
        """`{compiled .ts: literal union on `prop`}` (None = open).

        TypeScript expresses the property closure the same way JSON Schema
        does — an open carrier types the property `string`, a closed one names
        a literal-union alias — so this scanner mirrors
        `_compiled_schema_closures`: find the property, then follow the named
        type to its `export type` alias. Aliases are collected across ALL
        compiled TS, because a shape may close over an enum a different file
        declares and emit an `import type` for it; the compiler now refuses
        duplicate enum names outright (`_scan_global_enum_registry`), so a bare
        name resolves to exactly one alias.
        """
        prop = prop or self.KIND_PROPERTY
        aliases: dict[str, tuple[str, ...]] = {}
        for path in sorted(self.COMPILED_TYPESCRIPT.rglob("*.ts")):
            for match in re.finditer(
                r"^export type (\w+) = ([^;]+);", path.read_text(), re.M
            ):
                aliases[match.group(1)] = tuple(
                    re.findall(r'"([^"]+)"', match.group(2))
                )
        found: dict[str, tuple[str, ...] | None] = {}
        for path in sorted(self.COMPILED_TYPESCRIPT.rglob("*.ts")):
            for match in re.finditer(
                rf'^  "{re.escape(prop)}"\??: (.+);$',
                path.read_text(),
                re.M,
            ):
                annotation = match.group(1).strip()
                relative = path.relative_to(self.COMPILED_TYPESCRIPT).as_posix()
                if annotation == "string":
                    found[relative] = None
                    continue
                self.assertIn(
                    annotation,
                    aliases,
                    f"compiled/typescript/{relative} types "
                    f"{prop} as {annotation}, which resolves to "
                    "no emitted literal union. The scanner cannot tell whether "
                    "that artifact is open or closed, so the audit would be "
                    "measuring nothing here.",
                )
                found[relative] = aliases[annotation]
        return found

    def _generated_rust_closures(
        self, prop: str | None = None
    ) -> dict[str, tuple[str, ...] | None]:
        """`{generated .rs: wire values of `prop`'s field type}` (None = open).

        Rust closes a property by TYPING the struct field as a generated enum
        rather than `String`; the wire values are the `#[serde(rename = ...)]`
        attributes on that enum's variants. Enum bodies are collected across
        the whole generated tree so a field typed by a cross-module enum still
        resolves.
        """
        prop = prop or self.KIND_PROPERTY
        enums: dict[str, tuple[str, ...]] = {}
        for path in sorted(self.GENERATED_RUST.rglob("*.rs")):
            for match in re.finditer(
                r"^pub enum (\w+) \{\n(.*?)^\}", path.read_text(), re.M | re.S
            ):
                enums[match.group(1)] = tuple(
                    re.findall(
                        r'#\[serde\(rename = "([^"]+)"\)\]', match.group(2)
                    )
                )
        found: dict[str, tuple[str, ...] | None] = {}
        for path in sorted(self.GENERATED_RUST.rglob("*.rs")):
            for match in re.finditer(
                rf'#\[serde\(rename = "{re.escape(prop)}"[^\]]*\)\]'
                r"\n\s*pub \w+: ([\w:]+),",
                path.read_text(),
            ):
                annotation = match.group(1).rsplit("::", 1)[-1]
                relative = path.relative_to(self.GENERATED_RUST).as_posix()
                if annotation == "String":
                    found[relative] = None
                    continue
                self.assertIn(
                    annotation,
                    enums,
                    f"generated Rust {relative} types {prop} as "
                    f"{annotation}, which resolves to no generated enum.",
                )
                found[relative] = enums[annotation]
        return found

    def _compiled_rego_closures(
        self, union_name: str
    ) -> dict[str, tuple[str, ...] | None]:
        """`{compiled .rego: the assembled union's value set}` (None = absent).

        Rego is the one target with no property types at all — it emits value
        SETS keyed by CUE definition name and leaves the `deny` rules that
        consult them to the policy author. So "does this artifact carry the
        closure" is necessarily asked as "does it carry the assembled union's
        value set", not "how is the property typed". That is exactly the
        question the Rego emitter used to answer wrongly: it iterated
        `doc.enums` only, so the composed 22-value set existed in every other
        target and in NO Rego artifact.
        """
        symbol = f"{_rego_symbol(union_name)}_values"
        found: dict[str, tuple[str, ...] | None] = {}
        for path in sorted(self.COMPILED_REGO.rglob("*.rego")):
            match = re.search(
                rf"^{re.escape(symbol)} := \[([^\]]*)\]", path.read_text(), re.M
            )
            found[path.relative_to(self.COMPILED_REGO).as_posix()] = (
                tuple(re.findall(r'"([^"]+)"', match.group(1)))
                if match
                else None
            )
        return found

    def _all_compiled_closures(
        self, union_name: str
    ) -> dict[str, tuple[str, ...] | None]:
        """Every compiled target's view of the kind closure, one flat map.

        Keyed by the sink each artifact actually lives in, so a failure names
        the file on disk. `compiled/cue/` is deliberately absent: it is a
        verbatim passthrough of the CUE source, so scanning it would re-ask the
        declaration-side questions `_parts()` already answers rather than
        checking a projection.
        """
        return {
            **{
                f"compiled/json-schema/{k}": v
                for k, v in self._compiled_schema_closures().items()
            },
            **{
                f"compiled/shacl/{k}": v
                for k, v in self._compiled_shacl_closures().items()
            },
            **{
                f"compiled/typescript/{k}": v
                for k, v in self._compiled_typescript_closures().items()
            },
            **{
                f"compiled/rego/{k}": v
                for k, v in self._compiled_rego_closures(union_name).items()
            },
            **{
                f"crates/rkaf-core/src/generated/{k}": v
                for k, v in self._generated_rust_closures().items()
            },
        }

    # ---- the audit ----------------------------------------------------

    def test_kernel_part_is_exactly_the_ten_universal_kinds(self) -> None:
        _, parts = self._parts()
        kernel = {
            relpath: values
            for relpath, values in parts.items()
            if relpath.startswith("core/")
        }
        self.assertEqual(
            1,
            len(kernel),
            f"exactly one KERNEL part expected; found {sorted(kernel)}",
        )
        self.assertEqual(
            self.UNIVERSAL_LIFECYCLE_EVENT_KINDS,
            next(iter(kernel.values())),
            "the kernel's lifecycle-kind part changed. A jurisdiction-specific "
            "event kind belongs in a profile; if a new kind really is "
            "universal, add it to UNIVERSAL_LIFECYCLE_EVENT_KINDS deliberately.",
        )

    def test_at_least_one_profile_contributes_kinds(self) -> None:
        """Guard the guard: with no profile part the audit proves nothing."""
        _, parts = self._parts()
        self.assertTrue(
            [relpath for relpath in parts if relpath.startswith("profiles/")],
            "no profile contributes lifecycle kinds — either the split "
            "regressed or this audit has stopped measuring anything.",
        )

    def test_no_value_is_declared_by_two_modules(self) -> None:
        _, parts = self._parts()
        seen: dict[str, str] = {}
        for relpath, values in sorted(parts.items()):
            for value in values:
                self.assertNotIn(
                    value,
                    seen,
                    f"{value} is declared by both {seen.get(value)} and "
                    f"{relpath}. Exactly one module owns a value; two "
                    "declarations mean neither module can be changed safely.",
                )
                seen[value] = relpath

        # Ownership is scoped to the KIND value set, not to the IRIs
        # themselves: `#ProceedingStage` legitimately reuses the seven
        # stage-family IRIs for `rkaf:proceedingStage`, the coupled property
        # spec/rkaf-rulemaking.md §6 requires to equal the latest stage-family
        # kind. What must not happen is a second part of the KIND set going
        # unassembled, so the net below is name-shaped: an enum that announces
        # itself as a lifecycle-kind part must be one of the union's parts.
        # (The structural nets are `_closing_union_name` — exactly one shape
        # closes the property — and the compiled-artifact comparisons below.)
        for relpath, document in self._cue_documents().items():
            for enum in document.enums:
                if not enum.name.endswith("LifecycleEventKind"):
                    continue
                self.assertEqual(
                    parts.get(relpath, ()),
                    tuple(enum.values),
                    f"#{enum.name} in {relpath} declares lifecycle kinds but "
                    "is not a part of the assembled union — an orphan set "
                    "nothing enforces.",
                )

    def test_assembled_union_equals_kernel_plus_profiles(self) -> None:
        union_name, parts = self._parts()
        expected = [
            value
            for relpath in sorted(parts, key=lambda p: (not p.startswith("core/"), p))
            for value in parts[relpath]
        ]
        self.assertEqual(
            len(expected),
            len(set(expected)),
            "the assembled union repeats a value",
        )
        for compiled, values in self._all_compiled_closures(union_name).items():
            if values is None:
                continue
            self.assertEqual(
                sorted(expected),
                sorted(values),
                f"{compiled} closes {self.KIND_PROPERTY} over a set that is "
                f"not kernel + sum(profiles) (#{union_name}).",
            )

    def test_composed_rego_artifact_carries_the_whole_contract_set(self) -> None:
        """The shipped Rego artifact, named and counted.

        Rego was the target that lost the union: `compiled/rego/core/
        lifecycle-event.rego` carried the kernel's ten and no artifact anywhere
        under `compiled/rego/` carried the assembled set. This asserts the
        profile artifact specifically, so a failure points at a file rather
        than at a sink.
        """
        union_name, parts = self._parts()
        expected = {value for values in parts.values() for value in values}
        closures = self._compiled_rego_closures(union_name)
        composed = closures.get("profiles/us-rulemaking/us-lifecycle-event.rego")
        self.assertIsNotNone(
            composed,
            "compiled/rego/profiles/us-rulemaking/us-lifecycle-event.rego does "
            f"not carry #{union_name}. Run `make compile`; if it is still "
            "missing, target_rego has stopped emitting enum unions.",
        )
        self.assertEqual(sorted(expected), sorted(composed))
        self.assertEqual(22, len(composed), "the whole-contract set is 22 kinds")

    def test_every_target_carries_the_assembled_closure(self) -> None:
        """One target silently short of the union is the failure mode here.

        The composed set has to arrive in EVERY projection, not just the ones
        a gate happens to load. Rego is the worked example of why: no gate
        walks `compiled/rego/`, so when the emitter shipped only `doc.enums`
        the artifact carried 10 values instead of 22 and every other check
        stayed green. Asserting per-sink means the next target to lose the
        union names itself.
        """
        union_name, _ = self._parts()
        closures = self._all_compiled_closures(union_name)
        for sink in (
            "compiled/json-schema/",
            "compiled/shacl/",
            "compiled/typescript/",
            "compiled/rego/",
            "crates/rkaf-core/src/generated/",
        ):
            with self.subTest(sink=sink):
                self.assertTrue(
                    [
                        compiled
                        for compiled, values in closures.items()
                        if compiled.startswith(sink) and values is not None
                    ],
                    f"no artifact under {sink} carries the assembled "
                    f"#{union_name} closure. That target projects a value set "
                    "narrower than the CUE source declares.",
                )

    def test_no_compiled_kind_value_lacks_a_declaring_module(self) -> None:
        union_name, parts = self._parts()
        declared = {value for values in parts.values() for value in values}
        for compiled, values in self._all_compiled_closures(union_name).items():
            for value in values or ():
                self.assertIn(
                    value,
                    declared,
                    f"{compiled} accepts {value}, which no module declares.",
                )

    def test_kernel_carriers_stay_open_on_kind(self) -> None:
        """The deliberate half of the layering, pinned so it cannot drift.

        A kernel carrier does NOT close an extension point. Closing the kind
        property at the kernel's ten would make the kernel carriers REJECT
        events whose kinds a profile in this same contract declares — the
        compiled artifacts would then disagree with each other. Same semantics
        the kernel `#Artifact` has for US identifier terms: unconstrained, not
        rejected.

        Driven by `KERNEL_EXTENSION_POINT_PROPERTIES` rather than by one
        hardcoded property, so this and the `OverlaySupersetTests` exemption
        are answering to the SAME frozen list from opposite directions.

        `compiled/rego/` is deliberately not consulted here: Rego emits value
        SETS, never property types, so it has no way to express "this carrier
        leaves the property open" and there is nothing to assert. Its half of
        the contract — that the assembled union does arrive — is
        `test_every_target_carries_the_assembled_closure`.
        """
        self.assertTrue(
            KERNEL_EXTENSION_POINT_PROPERTIES,
            "the extension-point list is empty; this audit measures nothing.",
        )
        for prop in KERNEL_EXTENSION_POINT_PROPERTIES:
            scanners = {
                "compiled/json-schema": self._compiled_schema_closures(prop),
                "compiled/shacl": self._compiled_shacl_closures(prop),
                "compiled/typescript": self._compiled_typescript_closures(prop),
                "crates/rkaf-core/src/generated": (
                    self._generated_rust_closures(prop)
                ),
            }
            for sink, closures in scanners.items():
                # "Kernel" is anything not under `profiles/`, which is the one
                # split every sink agrees on: the Rust sink puts core modules
                # at the root (`generated/lifecycle_event.rs`) while the others
                # nest them under `core/`, but ALL of them put a profile under
                # `profiles/<profile>/`.
                kernel = {
                    artifact: values
                    for artifact, values in closures.items()
                    if not artifact.startswith("profiles/")
                }
                with self.subTest(prop=prop, sink=sink):
                    self.assertTrue(
                        kernel,
                        f"no kernel carrier under {sink} declares {prop} — "
                        "either the carrier moved or this audit stopped "
                        "measuring anything (run `make compile`).",
                    )
                    self.assertEqual(
                        [],
                        sorted(
                            artifact
                            for artifact, values in kernel.items()
                            if values is not None
                        ),
                        f"a kernel carrier under {sink} closes {prop}, which "
                        "KERNEL_EXTENSION_POINT_PROPERTIES declares an "
                        "extension point. A kernel closure REJECTS every "
                        "profile-contributed value no matter what the overlay "
                        "says; the closure belongs in the profile.",
                    )
                    self.assertTrue(
                        [
                            artifact
                            for artifact, values in closures.items()
                            if values is not None
                        ],
                        f"nothing under {sink} closes {prop} at all — the "
                        "composed artifact is missing and no profile enforces "
                        "the closed set.",
                    )


class USRulemakingProfileTests(unittest.TestCase):
    """US regulatory identity is enforced by the profile, not the kernel.

    Kernel-purity semantics, stated once and pinned here:

      * At the CUE source of truth the kernel `#Artifact` is CLOSED. Unifying it
        with `rkaf:hasRegulatoryIdentifier` is `field not allowed`.
      * The compiled kernel carriers are OPEN, because that is what JSON Schema
        without `additionalProperties: false` and open-world RDF mean. A
        document carrying US terms is therefore UNCONSTRAINED by the kernel
        carriers, not rejected by them.
      * The profile overlay composes `#Artifact`, keeps `@type: rkaf:Artifact`,
        and re-adds every US constraint. Enforcement moved; it did not vanish.
    """

    KERNEL_ARTIFACT = REPO_ROOT / "constraints" / "core" / "artifact.cue"
    PROFILE_ARTIFACT = (
        REPO_ROOT
        / "constraints"
        / "profiles"
        / "us-rulemaking"
        / "us-regulatory-artifact.cue"
    )

    US_TERMS = (
        "rkaf:hasRegulatoryIdentifier",
        "rkaf:regulatoryIdentifierScheme",
        "rkaf:publishedInProceeding",
    )

    def test_kernel_artifact_carriers_no_longer_mention_us_terms(self) -> None:
        document = parse_cue_file(self.KERNEL_ARTIFACT)
        artifact = next(s for s in document.shapes if s.name == "Artifact")
        declared = {prop.name for prop in artifact.properties}
        for term in self.US_TERMS:
            self.assertNotIn(term, declared)
        # The kernel DOES carry conditionals — §4.1's version-lineage rules are
        # universal. What it must never carry is a JURISDICTION grammar, so the
        # check is on the terms those conditionals mention, not on their count.
        # Asserting "no conditionals at all" would have made every future
        # universal cross-property rule look like a profile leak.
        conditional_terms = {
            branch.when_property for branch in artifact.conditionals
        } | {
            prop.name
            for branch in artifact.conditionals
            for prop in branch.then_require
        }
        for term in self.US_TERMS:
            self.assertNotIn(term, conditional_terms)

        schema = json.loads(target_json_schema(document))
        kernel = schema["$defs"]["Artifact"]
        for term in self.US_TERMS:
            self.assertNotIn(term, kernel["properties"])
        self.assertNotIn("USRegulatoryIdentifierScheme", schema["$defs"])
        self.assertNotIn(
            "USRegulatoryIdentifierScheme", json.dumps(kernel.get("allOf", []))
        )

        shacl = target_shacl(document)
        for term in self.US_TERMS:
            self.assertNotIn(term, shacl)

    def test_kernel_artifact_json_schema_stays_open(self) -> None:
        """The kernel does not REJECT a US-bearing document; it ignores it.

        Spelled out as a test so the semantics is a decision on record rather
        than an accident of the emitter.
        """
        document = parse_cue_file(self.KERNEL_ARTIFACT)
        kernel = json.loads(target_json_schema(document))["$defs"]["Artifact"]
        self.assertNotIn("additionalProperties", kernel)
        self.assertNotIn("unevaluatedProperties", kernel)

    def test_profile_overlay_keeps_every_kernel_artifact_constraint(self) -> None:
        document = parse_cue_file(self.PROFILE_ARTIFACT)
        kernel = json.loads(
            target_json_schema(parse_cue_file(self.KERNEL_ARTIFACT))
        )["$defs"]["Artifact"]
        overlay = json.loads(target_json_schema(document))["$defs"][
            "USRegulatoryArtifact"
        ]
        for name, definition in kernel["properties"].items():
            self.assertIn(
                name,
                overlay["properties"],
                f"the profile overlay dropped kernel property {name}",
            )
            if name != "@type":
                self.assertEqual(definition, overlay["properties"][name])
        self.assertEqual(
            sorted(kernel["required"]),
            sorted(overlay["required"]),
            "the profile overlay changed which kernel fields are required",
        )
        self.assertEqual({"const": "rkaf:Artifact"}, overlay["properties"]["@type"])

    def test_profile_overlay_enforces_every_us_grammar(self) -> None:
        document = parse_cue_file(self.PROFILE_ARTIFACT)
        overlay = json.loads(target_json_schema(document))["$defs"][
            "USRegulatoryArtifact"
        ]
        for term in self.US_TERMS:
            self.assertIn(term, overlay["properties"])

        conditions = {
            branch["if"]
            .get("properties", {})
            .get("rkaf:regulatoryIdentifierScheme", {})
            .get("anyOf", [{}])[0]
            .get("const"): branch["then"]["properties"][
                "rkaf:hasRegulatoryIdentifier"
            ]["pattern"]
            for branch in overlay["allOf"]
            if "rkaf:hasRegulatoryIdentifier" in branch["then"]["properties"]
        }
        for scheme in (
            "rkaf:us-cfr",
            "rkaf:us-usc",
            "rkaf:us-frdoc",
            "rkaf:us-regsgov",
            "rkaf:us-pl",
            "rkaf:us-eo",
        ):
            self.assertIn(
                scheme,
                conditions,
                f"the profile lost the {scheme} canonical-form grammar",
            )
            self.assertTrue(conditions[scheme].startswith("^urn:rkaf:us:"))

        # hasRegulatoryIdentifier present REQUIRES a declared scheme.
        self.assertIn(
            {
                "if": {"required": ["rkaf:hasRegulatoryIdentifier"]},
                "then": {
                    "properties": {
                        "rkaf:regulatoryIdentifierScheme": {
                            "$ref": "#/$defs/USRegulatoryIdentifierScheme"
                        }
                    },
                    "required": ["rkaf:regulatoryIdentifierScheme"],
                },
            },
            overlay["allOf"],
        )

    def test_profile_shacl_targets_the_universal_artifact_class(self) -> None:
        """The overlay constrains `rkaf:Artifact` rather than minting a class.

        A US regulatory document IS an Artifact. Every overlaid property is
        optional and every grammar sits behind a scheme guard, so conjoining
        this NodeShape with the kernel's can only ever add constraints.
        """
        shacl = target_shacl(
            parse_cue_file(self.PROFILE_ARTIFACT),
            reference_classes={"rkaf:publishedInProceeding": "rkaf:Proceeding"},
        )
        self.assertIn("rkaf:USRegulatoryArtifactShape a sh:NodeShape ;", shacl)
        self.assertIn("sh:targetClass rkaf:Artifact ;", shacl)
        self.assertIn(
            "sh:path rkaf:publishedInProceeding ;", shacl
        )
        self.assertIn("sh:class rkaf:Proceeding ;", shacl)
        # Only the shape's own property declarations — not the `sh:not` guards
        # inside the conditional `sh:or` blocks — carry cardinality. Every US
        # property must stay optional so conjoining this shape with the
        # kernel's cannot reject a non-US Artifact.
        declarations = [
            line.strip()
            for line in shacl.splitlines()
            if line.startswith("  sh:property [ sh:path ")
        ]
        for term in ("rkaf:hasRegulatoryIdentifier", "rkaf:regulatoryIdentifierScheme"):
            declaration = next(
                line for line in declarations if f"sh:path {term} ;" in line
            )
            self.assertNotIn("sh:minCount", declaration)
        scheme = next(
            line
            for line in declarations
            if "sh:path rkaf:regulatoryIdentifierScheme ;" in line
        )
        self.assertIn("sh:in ( rkaf:us-cfr", scheme)
        published = next(
            line for line in declarations if "sh:path rkaf:publishedInProceeding ;" in line
        )
        self.assertNotIn("sh:minCount", published)


def _shacl_property_declarations(ttl: str) -> dict[str, dict[str, dict]]:
    """`{target_class: {sh:path: {min, max, in}}}` for one compiled SHACL file.

    Reads only a NodeShape's OWN top-level `sh:property` declarations — the
    two-space-indented lines the emitter writes one per property. Declarations
    nested inside a conditional `sh:or` block are indented further and are
    deliberately skipped: those are guards, not the shape's cardinality.
    """
    shapes: dict[str, dict[str, dict]] = {}
    target: str | None = None
    for line in ttl.splitlines():
        if line.startswith("  sh:targetClass "):
            target = line.strip().removeprefix("sh:targetClass ").removesuffix(" ;")
            shapes.setdefault(target, {})
        elif line == "  .":
            target = None
        elif target is not None and line.startswith("  sh:property [ sh:path "):
            path = re.search(r"sh:path (\S+) ;", line)
            if path is None:
                continue
            minimum = re.search(r"sh:minCount (\d+)", line)
            maximum = re.search(r"sh:maxCount (\d+)", line)
            closure = re.search(r"sh:in \(([^)]*)\)", line)
            shapes[target][path.group(1)] = {
                "min": int(minimum.group(1)) if minimum else 0,
                "max": int(maximum.group(1)) if maximum else None,
                "in": frozenset(closure.group(1).split()) if closure else None,
            }
    return shapes


class ProfileOverlaySupersetTests(unittest.TestCase):
    """Every profile overlay is a SUPERSET of the kernel shape it displaces.

    This is the invariant the whole kernel/profile split rests on. Both
    `tools/conformance_lib.py` and `crates/rkaf-validate/build.rs` bind a
    JSON-LD `@type` to the PROFILE schema whenever a profile claims it, on the
    stated grounds that the overlay restates every kernel constraint and adds
    the profile's own. If that stops being true, the displaced kernel
    constraints stop being enforced and every gate stays green — the profile
    overlay currently carries nine US negatives that nothing else checks.

    So this walks EVERY profile schema that binds a `@type` also bound in
    `core/`, rather than hardcoding the one overlay that exists today. A second
    profile added later is covered on arrival.
    """

    CORE_JSON_SCHEMA = REPO_ROOT / "compiled" / "json-schema" / "core"
    PROFILE_JSON_SCHEMA = REPO_ROOT / "compiled" / "json-schema" / "profiles"
    CORE_SHACL = REPO_ROOT / "compiled" / "shacl" / "core"
    PROFILE_SHACL = REPO_ROOT / "compiled" / "shacl" / "profiles"

    # Kernel SHACL enum closures a profile overlay DROPS, keyed by (overlay TTL
    # relative to compiled/shacl/, target class, property).
    #
    # EMPTY, and it must stay empty. Adversarial-review finding F2 —
    # `target_shacl()` took no cross-file enum registry, so a property whose
    # enum is declared in another CUE file lost its `sh:in` — is FIXED: the
    # emitter now resolves enum references through the same registry the
    # json-schema/rust/typescript emitters use, and
    # `compiled/shacl/profiles/us-rulemaking/us-regulatory-artifact.ttl` closes
    # `rkaf:artifactIdentifierScheme` over the kernel's twelve schemes. That
    # matters because `tools/constraints_parity.py` validates the
    # us-regulatory-artifact rows against that overlay ALONE.
    #
    # Landing the closure required fixing a second defect first: an IRI-valued
    # `sh:in` only matches data whose values reach RDF as IRIs, and
    # `rkaf:capabilityCap` / `rkaf:lifecycleState` carried no `@type`
    # coercion in `context/rkaf-context.jsonld`. Both now do.
    KNOWN_DROPPED_SHACL_ENUM_CLOSURES: set[tuple[str, str, str]] = set()

    def _classes_by_type(
        self, directory: Path, pattern: str
    ) -> dict[str, list[tuple]]:
        """`{type_iri: [(path, class_name, class_schema), ...]}`.

        A list, not a single entry: two overlays claiming one `@type` is a
        collision `conformance_lib` rejects, but this walk must still SEE both
        rather than let the later file quietly replace the earlier one.
        """
        found: dict[str, list[tuple]] = {}
        for path in sorted(directory.glob(pattern)):
            document = json.loads(path.read_text())
            for class_name, class_schema in document.get("$defs", {}).items():
                if not isinstance(class_schema, dict):
                    continue
                type_iri = (
                    class_schema.get("properties", {}).get("@type", {}).get("const")
                )
                if isinstance(type_iri, str) and type_iri.startswith("rkaf:"):
                    found.setdefault(type_iri, []).append(
                        (path, class_name, class_schema)
                    )
        return found

    def _overlay_pairs(self) -> list[tuple]:
        kernel = self._classes_by_type(self.CORE_JSON_SCHEMA, "*.schema.json")
        profile = self._classes_by_type(self.PROFILE_JSON_SCHEMA, "*/*.schema.json")
        return [
            (type_iri, kernel[type_iri][0], entry)
            for type_iri, entries in profile.items()
            if type_iri in kernel
            for entry in entries
        ]

    # The SHAPE a kernel extension point has: `{"type": "string"}` is every
    # string, so an overlay that closes it over an enum can only narrow.
    # Anything richer than this is a real kernel constraint and an overlay must
    # restate it verbatim or not at all.
    #
    # Shape alone is not sufficient authorization. Keyed on shape only, the
    # exemption would also admit an overlay that FIRST relaxed a kernel closure
    # to `{"type": "string"}` and then re-closed it in the profile — turning a
    # constraint every kernel consumer got into one only profile consumers get,
    # while this test reported a superset. So the property must ALSO be named
    # in KERNEL_EXTENSION_POINT_PROPERTIES, which is frozen at module scope.
    KERNEL_EXTENSION_POINT = {"type": "string"}

    @staticmethod
    def _closed_string_enum(definition: dict, schema_path: Path) -> list | None:
        """The closed value list a property definition resolves to, if any."""
        reference = definition.get("$ref", "")
        if reference.startswith("#/$defs/"):
            defs = json.loads(schema_path.read_text()).get("$defs", {})
            definition = defs.get(reference.removeprefix("#/$defs/"), {})
        values = definition.get("enum")
        return values if isinstance(values, list) and values else None

    def test_the_scan_actually_finds_an_overlay(self) -> None:
        """Guard the guard: an empty walk would pass every assertion below."""
        pairs = self._overlay_pairs()
        self.assertIn(
            "rkaf:Artifact",
            {type_iri for type_iri, _, _ in pairs},
            "no profile overlay of a kernel class was found — either "
            "compiled/json-schema/ is stale (run `make compile`) or this test "
            "has stopped measuring anything.",
        )

    def test_every_overlay_is_a_json_schema_superset_of_the_kernel(self) -> None:
        for type_iri, (kpath, kname, kernel), (ppath, pname, overlay) in (
            self._overlay_pairs()
        ):
            with self.subTest(type_iri=type_iri, overlay=ppath.name):
                for name, definition in kernel.get("properties", {}).items():
                    self.assertIn(
                        name,
                        overlay.get("properties", {}),
                        f"{pname} ({ppath.name}) displaces {kname} for "
                        f"{type_iri} but dropped kernel property {name}",
                    )
                    if name == "@type":
                        continue
                    restated = overlay["properties"][name]
                    if restated == definition:
                        continue
                    # The one legal difference: the kernel left the property
                    # UNCONSTRAINED (an extension point — `{"type": "string"}`
                    # carries no constraint at all) and the overlay closes it
                    # over a value set. That is ADDING a constraint, the same
                    # direction this test protects. `rkaf:lifecycleEventKind`
                    # is exactly that: the kernel owns the ten universal kinds
                    # but leaves the carrier open, and the profile binds the
                    # assembled closed union (see LifecycleKindOwnershipTests).
                    #
                    # Two conditions, not one. The property must be a DECLARED
                    # extension point, and the kernel definition must still
                    # have the open shape. Checking only the second lets a
                    # future overlay manufacture its own exemption by relaxing
                    # the kernel first.
                    self.assertIn(
                        name,
                        KERNEL_EXTENSION_POINT_PROPERTIES,
                        f"{pname} restates kernel property {name}, which is "
                        "not a declared extension point. An overlay may ADD "
                        "constraints, never restate one differently. If the "
                        "kernel really should hand this property to profiles, "
                        "add it to KERNEL_EXTENSION_POINT_PROPERTIES as a "
                        "deliberate change to the kernel contract.",
                    )
                    self.assertEqual(
                        self.KERNEL_EXTENSION_POINT,
                        definition,
                        f"{pname} redefines kernel property {name}; an overlay "
                        "may ADD constraints, never restate one differently",
                    )
                    self.assertIsNotNone(
                        self._closed_string_enum(restated, ppath),
                        f"{pname} restates the open kernel property {name} as "
                        f"{restated}, which is not a closed value set. An "
                        "extension point may only be NARROWED.",
                    )
                self.assertEqual(
                    [],
                    sorted(set(kernel.get("required", ())) - set(overlay.get("required", ()))),
                    f"{pname} stopped requiring a field {kname} requires",
                )
                self.assertEqual(
                    {"const": type_iri},
                    overlay["properties"]["@type"],
                    f"{pname} must keep binding {type_iri}; minting a parallel "
                    "@type would leave the kernel class unconstrained",
                )

    def test_every_overlay_shacl_preserves_kernel_property_constraints(self) -> None:
        """SHACL is conjunctive in principle — but only the OVERLAY is consulted.

        `tools/constraints_parity.py` validates a profile's fixtures against the
        profile TTL alone, so the overlay has to carry the kernel's constraints
        itself rather than relying on the kernel shape also being loaded.
        """
        kernel_shapes: dict[str, dict[str, dict]] = {}
        for path in sorted(self.CORE_SHACL.glob("*.ttl")):
            for target, properties in _shacl_property_declarations(path.read_text()).items():
                kernel_shapes.setdefault(target, {}).update(properties)

        dropped_closures: set[tuple[str, str, str]] = set()
        checked = 0
        for path in sorted(self.PROFILE_SHACL.glob("*/*.ttl")):
            relative = path.relative_to(self.PROFILE_SHACL.parent).as_posix()
            for target, properties in _shacl_property_declarations(path.read_text()).items():
                if target not in kernel_shapes:
                    continue
                checked += 1
                for name, kernel in kernel_shapes[target].items():
                    with self.subTest(overlay=relative, target=target, path=name):
                        self.assertIn(
                            name,
                            properties,
                            f"{relative} targets {target} but dropped the "
                            f"kernel's constraint on {name}",
                        )
                        overlay = properties[name]
                        self.assertGreaterEqual(
                            overlay["min"],
                            kernel["min"],
                            f"{relative} relaxed sh:minCount on {name}",
                        )
                        if kernel["max"] is not None:
                            self.assertIsNotNone(
                                overlay["max"],
                                f"{relative} dropped sh:maxCount on {name}",
                            )
                            self.assertLessEqual(
                                overlay["max"],
                                kernel["max"],
                                f"{relative} relaxed sh:maxCount on {name}",
                            )
                        if kernel["in"] is not None and not (
                            overlay["in"] is not None
                            and kernel["in"] <= overlay["in"]
                        ):
                            dropped_closures.add((relative, target, name))

        self.assertGreater(
            checked, 0, "no profile SHACL shape overlays a kernel class — "
            "compiled/shacl/ is stale or this test stopped measuring anything."
        )
        self.assertEqual(
            self.KNOWN_DROPPED_SHACL_ENUM_CLOSURES,
            dropped_closures,
            "a profile overlay dropped a kernel sh:in closure. Every enum "
            "reference — including one declared in another CUE file — must "
            "reach the overlay's SHACL, because constraints_parity.py "
            "validates a profile's fixtures against that overlay alone.",
        )


class ProfileRangeRegistryTests(unittest.TestCase):
    """A profile owns the ranges of the predicates it owns."""

    def test_kernel_range_registry_declares_no_profile_predicate(self) -> None:
        kernel = (
            REPO_ROOT / "constraints" / "semantics" / "l0-ranges.cue"
        ).read_text()
        for term in (
            "rkaf:publishedInProceeding",
            "rkaf:commentPeriodFor",
            "rkaf:proceedingAffects",
            "dcat:qualifiedRelation",
        ):
            self.assertNotIn(term, kernel)

    def test_reference_class_registry_unions_kernel_and_profile(self) -> None:
        registry = _scan_reference_class_registry(
            REPO_ROOT / "constraints" / "core" / "artifact.cue"
        )
        self.assertEqual("rkaf:Artifact", registry["dcterms:hasFormat"])
        self.assertEqual(
            "rkaf:Proceeding", registry["rkaf:publishedInProceeding"]
        )


class SchemaBindingCollisionTests(unittest.TestCase):
    """A `@type` claimed by two profile overlays is a HARD ERROR.

    Displacing the KERNEL binding is safe and deliberate: the overlay composes
    the kernel shape, so it is a superset. Two sibling profiles are not
    supersets of each other, so there is no defensible winner — whichever loses
    stops being enforced while every gate stays green. The old "first path
    alphabetically wins" rule made that outcome silent AND arbitrary: an
    `eu-rulemaking` overlay sorts ahead of `us-rulemaking`, so adding one would
    have unbound the US schema (and the nine US negatives only it enforces)
    without a single failing test.
    """

    @staticmethod
    def _class_schema(type_iri: str) -> dict:
        return {
            "properties": {"@type": {"const": type_iri}},
            "required": ["@type"],
        }

    def _tree(self, root: Path, profiles: dict[str, str]) -> None:
        core = root / "compiled" / "json-schema" / "core"
        core.mkdir(parents=True)
        (core / "artifact.schema.json").write_text(
            json.dumps({"$defs": {"Artifact": self._class_schema("rkaf:Artifact")}})
        )
        for profile, class_name in profiles.items():
            directory = root / "compiled" / "json-schema" / "profiles" / profile
            directory.mkdir(parents=True)
            (directory / f"{profile}-artifact.schema.json").write_text(
                json.dumps({"$defs": {class_name: self._class_schema("rkaf:Artifact")}})
            )

    def _bindings_over(self, root: Path) -> dict:
        return unittest.mock.patch.multiple(
            conformance_lib,
            ROOT=root,
            COMPILED_JSON_SCHEMA_DIR=root / "compiled" / "json-schema" / "core",
            COMPILED_PROFILE_JSON_SCHEMA_ROOT=(
                root / "compiled" / "json-schema" / "profiles"
            ),
        )

    def test_one_profile_overlay_displaces_the_kernel_binding(self) -> None:
        """Control: the single-overlay case still resolves to the profile."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._tree(root, {"us-rulemaking": "USRegulatoryArtifact"})
            with self._bindings_over(root):
                bindings = conformance_lib.schema_bindings()
        self.assertEqual(
            "USRegulatoryArtifact", bindings["rkaf:Artifact"].class_name
        )

    def test_two_profile_overlays_on_one_type_iri_raise(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._tree(
                root,
                {
                    "eu-rulemaking": "EURegulatoryArtifact",
                    "us-rulemaking": "USRegulatoryArtifact",
                },
            )
            with self._bindings_over(root):
                with self.assertRaises(
                    conformance_lib.DuplicateProfileBindingError
                ) as caught:
                    conformance_lib.schema_bindings()
        message = str(caught.exception)
        self.assertIn("rkaf:Artifact", message)
        self.assertIn("profiles/eu-rulemaking", message)
        self.assertIn("profiles/us-rulemaking", message)

    def test_the_shipped_compiled_tree_has_no_overlay_collision(self) -> None:
        """The rule runs against the real tree, not only a synthetic one.

        `schema_bindings()` raising IS the collision check, so calling it here
        is the assertion: if `compiled/json-schema/profiles/` ever grows a
        second overlay for a class, this fails before any downstream gate gets
        a chance to pass on a silently unbound schema.
        """
        bindings = conformance_lib.schema_bindings()
        self.assertEqual(
            "USRegulatoryArtifact",
            bindings["rkaf:Artifact"].class_name,
            "rkaf:Artifact must resolve to the US rulemaking overlay; binding "
            "it to the kernel would stop enforcing the US grammars",
        )
        self.assertEqual(
            "USLifecycleEvent",
            bindings["rkaf:LifecycleEvent"].class_name,
            "rkaf:LifecycleEvent must resolve to the composed overlay — the "
            "artifact that closes the kind property over the assembled union. "
            "Binding it to the kernel would leave every lifecycle-event kind "
            "unchecked, because the kernel carrier is deliberately open on it.",
        )


class TypedLiteralCarriageTests(unittest.TestCase):
    """The ValueAssertion object slot must survive to EVERY target as a typed
    literal — not as "some object" on one side and "some literal" on the other.

    Shape parity alone would not catch the failure that matters here. JSON
    Schema sees a nested object with an `@type` member; SHACL sees a single
    expanded RDF literal with a datatype. Those are different views of the same
    value, and they agree only if the CLOSED SET is the same on both sides. A
    datatype added to the CUE enum but lost in one emitter would leave one gate
    accepting a value the other rejects, with every fixture still green.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "value-assertion.cue"
        self.document = parse_cue_file(self.source)
        self.registry = _scan_global_enum_registry(self.source)
        self.datatypes = next(
            enum.values
            for enum in self.document.enums
            if enum.name == "ValueDatatype"
        )

    def test_json_schema_carries_value_and_datatype(self) -> None:
        composed = json.loads(
            target_json_schema(self.document, registry=self.registry)
        )
        value = composed["$defs"]["ValueAssertion"]["properties"]["rkaf:assertsValue"]
        self.assertEqual(value["type"], "object")
        self.assertEqual(value["properties"]["@value"], {"type": "string"})
        self.assertEqual(
            value["properties"]["@type"], {"$ref": "#/$defs/ValueDatatype"}
        )
        self.assertEqual(sorted(value["required"]), ["@type", "@value"])
        self.assertIs(
            value["additionalProperties"],
            False,
            "the value object must be CLOSED. The CUE struct is closed, so "
            "`cue vet` rejects an extra member; an open JSON Schema object "
            "would accept documents CUE and SHACL reject.",
        )
        self.assertEqual(
            composed["$defs"]["ValueDatatype"]["enum"],
            self.datatypes,
            "the JSON Schema datatype closure drifted from the CUE enum",
        )
        self.assertIn("rkaf:assertsValue", composed["$defs"]["ValueAssertion"]["required"])

    def test_shacl_closes_the_same_datatype_set(self) -> None:
        shacl = target_shacl(
            self.document,
            reference_classes=_scan_reference_class_registry(self.source),
            source_file=self.source,
            registry=self.registry,
        )
        self.assertIn("sh:path rkaf:assertsValue ;", shacl)
        self.assertIn("sh:nodeKind sh:Literal ;", shacl)
        emitted = set(re.findall(r"sh:datatype (\S+) \]", shacl))
        self.assertEqual(
            emitted,
            set(self.datatypes),
            "SHACL and JSON Schema must close the value object's datatype over "
            "the SAME set; a difference means one gate accepts what the other "
            "rejects",
        )

    def test_rust_and_typescript_carry_the_typed_literal(self) -> None:
        rust = target_rust(
            self.document, registry=self.registry, source_file=self.source
        )
        self.assertIn(
            "pub asserts_value: crate::TypedLiteral<ValueDatatype>,",
            rust,
            "the Rust carrier must type the literal, not degrade it to String",
        )
        typescript = target_typescript(
            self.document, registry=self.registry, source_file=self.source
        )
        self.assertIn(
            '"rkaf:assertsValue": { "@value": string; "@type": ValueDatatype };',
            typescript,
        )
        # Not just the type — a runtime check that the datatype is in the set.
        self.assertIn("@type outside the closed datatype set", typescript)
        for datatype in self.datatypes:
            self.assertIn(f'"{datatype}"', typescript)

    def test_value_object_rejects_members_outside_json_ld(self) -> None:
        """The compiled value object is CLOSED, so JSON Schema rejects exactly
        what `cue vet` rejects.

        Two members matter, for different reasons:

          * `@language` — the RDF-corrupting one. A language-tagged literal
            expands with the declared datatype DROPPED, so SHACL's
            `sh:datatype` alternatives reject it. An open object left JSON
            Schema accepting a document SHACL rejected, which is the exact
            disagreement §2.2's closed datatype set exists to prevent. The
            corpus negative
            `fixtures/negatives/value-assertion-language-tagged-negative.jsonld`
            pins this end to end across both gates.
          * an arbitrary member (`rkaf:bogus`) — a WIRE-FORM-only divergence.
            JSON-LD expansion silently drops it, so the RDF is a well-formed
            typed literal and SHACL passes. That is why it is asserted HERE and
            not as a corpus negative: `tools/validate_negatives.py` requires
            every negative fixture to produce a SHACL violation, which this
            document by construction cannot. JSON Schema is the only gate that
            can catch it, so JSON Schema is where it is pinned.
        """
        composed = json.loads(
            target_json_schema(self.document, registry=self.registry)
        )
        target = composed["$defs"]["ValueAssertion"]
        target["$defs"] = composed["$defs"]
        base = {
            "@id": "urn:rkaf:test:value-assertion",
            "@type": "rkaf:ValueAssertion",
            "rkaf:assertionOrigin": "rkaf:humanAsserted",
            "rkaf:assertsSubject": "urn:rkaf:test:subject",
            "rkaf:assertsPredicate": "urn:rkaf:test:predicate",
            "rkaf:assertionPolarity": "rkaf:affirmed",
        }
        validator = Draft202012Validator(target)
        self.assertEqual(
            list(
                validator.iter_errors(
                    {**base, "rkaf:assertsValue": {"@value": "x", "@type": "xsd:string"}}
                )
            ),
            [],
            "a bare value object must still validate",
        )
        for extra in ({"@language": "en"}, {"rkaf:bogus": "y"}):
            with self.subTest(extra=extra):
                node = {
                    **base,
                    "rkaf:assertsValue": {
                        "@value": "x",
                        "@type": "xsd:string",
                        **extra,
                    },
                }
                self.assertTrue(
                    list(validator.iter_errors(node)),
                    f"the value object must reject the extra member {extra}",
                )

    def test_value_object_without_closed_datatype_enum_is_a_compile_error(
        self,
    ) -> None:
        """A value object whose `@type` is not a closed enum must raise.

        This is the guardrail that DOES exist. The fixture below declares
        `@value`, so it IS a value object; what it lacks is a closed datatype
        enum on `@type`. Without one, SHACL has no datatype set to close over
        and every compiled target would accept any datatype IRI — a silently
        weaker artifact, which is what `CompileError` exists to prevent.

        Note this test does NOT cover the not-a-value-object case; that case
        does not raise. See
        `test_non_value_object_nested_struct_hoists_and_is_documented_lossy`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "constraints" / "core"
            root.mkdir(parents=True)
            (root / "bad.cue").write_text(
                "package rkaf\n\n"
                "#Bad: {\n"
                '\t"@type": "rkaf:Bad"\n'
                '\t"rkaf:nested": {\n'
                '\t\t"@value": string\n'
                '\t\t"@type":  "xsd:date"\n'
                "\t}\n"
                "}\n"
            )
            with self.assertRaises(CompileError) as raised:
                parse_cue_file(root / "bad.cue")
            self.assertIn("closed datatype enum", str(raised.exception))

    def test_non_value_object_nested_struct_hoists_and_is_documented_lossy(
        self,
    ) -> None:
        """A nested struct WITHOUT `@value` does not raise — it hoists, lossily.

        This pins a KNOWN DEGRADATION, not desired behavior. The projector
        flattens the inner fields onto the outer shape and types the outer
        property as a plain string. Because the hoist is field-wise, an inner
        `"@type"` OVERWRITES the outer shape's class discriminator: `#Bad`
        below compiles to a schema asserting `@type == "rkaf:Inner"`, so a
        binding minted from it would validate the wrong class.

        The behavior is preserved deliberately —
        `constraints/adversarial/access-scope-leakage.cue` is authored against
        it — but it was previously documented as a `CompileError` in three
        places while doing the opposite. Asserting it explicitly means a future
        tightening shows up as a deliberate change to this test rather than a
        silent behavior swap.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "constraints" / "core"
            root.mkdir(parents=True)
            (root / "bad.cue").write_text(
                "package rkaf\n\n"
                "#Bad: {\n"
                '\t"@type": "rkaf:Bad"\n'
                '\t"rkaf:nested": {\n'
                '\t\t"rkaf:inner": string\n'
                '\t\t"@type":      "rkaf:Inner"\n'
                "\t}\n"
                "}\n"
            )
            # No CompileError: the not-a-value-object case falls through.
            document = parse_cue_file(root / "bad.cue")
            composed = json.loads(target_json_schema(document))
            shape = composed["$defs"]["Bad"]
            self.assertEqual(
                shape["properties"]["@type"],
                {"const": "rkaf:Inner"},
                "KNOWN DEGRADATION: the nested `@type` overwrote the outer "
                "class discriminator, which should have stayed `rkaf:Bad`. If "
                "this assertion starts failing, the hoist was tightened — "
                "update the comments in tools/constraints_compile.py and the "
                "CHANGELOG entry that describe it.",
            )
            # The inner field was hoisted onto the OUTER shape, and the nested
            # property degraded to an unconstrained string.
            self.assertEqual(shape["properties"]["rkaf:inner"], {"type": "string"})
            self.assertEqual(shape["properties"]["rkaf:nested"], {"type": "string"})


class PropositionSeparationTests(unittest.TestCase):
    """Core §2.3 — immutable proposition content stays structurally separate
    from acceptance, disposition, confidence, and attestation.

    The vision's rule is that an assertion's identity never includes mutable
    state. That is only checkable if the two halves are NAMED, which is why
    `#AssertionProposition` and `#ConsumerDisposition` exist as separate CUE
    definitions rather than as comments over one flat struct. These tests pin
    the boundary so a later edit cannot quietly move a field across it.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "assertion.cue"
        self.document = parse_cue_file(self.source)
        self.shapes = {shape.name: shape for shape in self.document.shapes}

    def _fields(self, name: str) -> set[str]:
        return {prop.name for prop in self.shapes[name].properties}

    def test_proposition_and_disposition_are_disjoint(self) -> None:
        proposition = self._fields("AssertionProposition")
        disposition = self._fields("ConsumerDisposition")
        self.assertEqual(proposition, set(ASSERTION_PROPOSITION_FIELDS))
        self.assertEqual(disposition, set(CONSUMER_DISPOSITION_FIELDS))
        self.assertEqual(
            proposition & disposition,
            set(),
            "a field may not be both proposition content and consumer state",
        )

    def test_envelope_carries_no_proposition_content(self) -> None:
        envelope = self._fields("AssertionEnvelope")
        self.assertEqual(
            envelope & set(ASSERTION_PROPOSITION_FIELDS),
            set(),
            "the envelope is context for a proposition, never the proposition",
        )
        self.assertLessEqual(
            set(CONSUMER_DISPOSITION_FIELDS),
            envelope,
            "the envelope composes the consumer-disposition half",
        )

    def test_both_proposition_forms_compose_both_halves(self) -> None:
        for name in ("relationship-assertion", "value-assertion"):
            with self.subTest(form=name):
                document = parse_cue_file(
                    REPO_ROOT / "constraints" / "core" / f"{name}.cue"
                )
                shape = next(iter(document.shapes))
                fields = {prop.name for prop in shape.properties}
                self.assertLessEqual(set(ASSERTION_PROPOSITION_FIELDS), fields)
                self.assertLessEqual(set(ASSERTION_ENVELOPE_FIELDS), fields)

    def test_neither_form_stores_an_acceptance_decision(self) -> None:
        """Approval, rejection, dispute, and revocation live on Attestation.

        A proposition-bearing assertion that carried any of them would make its
        own content depend on a social judgment — exactly the conflation Core
        §2.1 and §2.3 forbid.
        """
        attestation = parse_cue_file(
            REPO_ROOT / "constraints" / "core" / "attestation.cue"
        )
        decision_terms = {
            prop.name
            for shape in attestation.shapes
            for prop in shape.properties
        } - {"@type", "rkaf:hasEffectivePeriod", "rkaf:lastVerifiedAt",
             "rkaf:verifiedBy", "rkaf:hasAccessScope"}
        for name in ("relationship-assertion", "value-assertion", "assertion"):
            with self.subTest(form=name):
                document = parse_cue_file(
                    REPO_ROOT / "constraints" / "core" / f"{name}.cue"
                )
                fields = {
                    prop.name
                    for shape in document.shapes
                    for prop in shape.properties
                }
                self.assertEqual(
                    fields & decision_terms,
                    set(),
                    "an assertion must not carry an Attestation's decision "
                    "fields; acceptance is a separate, scoped, temporal record",
                )


class ProvenanceRoleSeparationTests(unittest.TestCase):
    """Core §2.4 — four provenance roles, four records, no conflation.

    source claimant / extraction provenance / model derivation lineage / human
    approval each answer a different question. The failure this guards against
    is one record answering two of them, which is how an extractor starts
    looking like an authority and how an unreviewed candidate starts looking
    approved.
    """

    def _document(self, stem: str):
        return parse_cue_file(REPO_ROOT / "constraints" / "core" / f"{stem}.cue")

    def _required(self, stem: str, shape_name: str) -> set[str]:
        document = self._document(stem)
        shape = next(s for s in document.shapes if s.name == shape_name)
        return {prop.name for prop in shape.properties if not prop.optional}

    def test_extraction_activity_requires_no_approver(self) -> None:
        """An unreviewed model candidate must be representable.

        rkaf:AILineage requires rkaf:humanApprover; that is the REVIEWED
        derivation record. ExtractionActivity is the run record, and requiring
        an approver here would make "a model produced this and nobody has
        looked at it yet" unsayable — which the vision names as a thing the
        system must be able to say.
        """
        document = self._document("extraction-activity")
        shape = next(s for s in document.shapes if s.name == "ExtractionActivity")
        fields = {prop.name for prop in shape.properties}
        conditional_fields = {
            prop.name
            for branch in shape.conditionals
            for prop in branch.then_require
        }
        for approval_term in (
            "rkaf:humanApprover",
            "rkaf:humanRationale",
            "rkaf:decision",
            "rkaf:attestor",
            "rkaf:attestedAt",
        ):
            self.assertNotIn(approval_term, fields | conditional_fields)

    def test_extraction_activity_names_no_provider_type(self) -> None:
        """Provider neutrality is a property of the SOURCE, not of prose.

        Every reference is a Rulespec-owned IRI, a version string, or an opaque
        digest. A vendor name reaching the kernel would make the contract's
        identity depend on someone else's response shape.
        """
        # Declarations only. The prose deliberately NAMES what it excludes
        # ("no provider request object, response object, SDK type…"); scanning
        # comments would flag the exclusion itself.
        source = (
            REPO_ROOT / "constraints" / "core" / "extraction-activity.cue"
        ).read_text()
        text = "\n".join(
            line.split("//")[0] for line in source.splitlines()
        ).lower()
        for vendor_token in (
            "openai", "anthropic", "azure", "bedrock", "vertex", "cohere",
            "huggingface", "ollama", "sdk", "chatcompletion", "sentence_transformers",
        ):
            self.assertNotIn(vendor_token, text)

    def test_claimant_attribution_has_no_uncertainty_value(self) -> None:
        """`#ClaimantAttribution` describes the DOCUMENT, never the extractor.

        Every member states something about how the source attributed the
        claim, including `rkaf:claimantNotStated` ("the source made no
        attribution"). A carrier whose own attribution taxonomy carries an
        `unclear` case therefore has no landing spot here, and §2.4 resolves
        that normatively: OMIT the record; put extractor uncertainty in a
        `rkaf:ConfidenceRecord` or an `rkaf:ExtractionActivity`.

        Pinned so that adding an uncertainty value becomes a deliberate edit to
        both the enum and the spec sentence, not a quiet widening that lets an
        extractor's doubt masquerade as a statement about the document.
        """
        values = next(
            enum.values
            for enum in self._document("source-claimant").enums
            if enum.name == "ClaimantAttribution"
        )
        self.assertEqual(
            values,
            [
                "rkaf:claimantNamedInSource",
                "rkaf:claimantImpliedBySource",
                "rkaf:claimantIsDocumentIssuer",
                "rkaf:claimantNotStated",
            ],
        )
        for token in ("unclear", "unknown", "ambiguous", "uncertain", "undetermined"):
            for value in values:
                self.assertNotIn(
                    token,
                    value.lower(),
                    f"`{value}` reads as extractor uncertainty. §2.4 requires "
                    "the record to be OMITTED in that case; if this set is "
                    "widened, the spec sentence must change with it.",
                )

    def test_claimant_and_extractor_share_no_terms(self) -> None:
        claimant = {
            prop.name
            for shape in self._document("source-claimant").shapes
            for prop in shape.properties
        } - {"@type"}
        extractor = {
            prop.name
            for shape in self._document("extraction-activity").shapes
            for prop in shape.properties
        } - {"@type"}
        self.assertEqual(
            claimant & extractor,
            set(),
            "who the source says asserts it and which run extracted it are "
            "different questions; sharing a term would let one answer stand in "
            "for the other",
        )

    def test_envelope_links_each_role_by_its_own_edge(self) -> None:
        envelope = {
            prop.name
            for shape in self._document("assertion").shapes
            if shape.name == "AssertionEnvelope"
            for prop in shape.properties
        }
        for edge in (
            "rkaf:hasSourceClaimant",       # source claimant
            "rkaf:hasExtractionProvenance", # extraction run
            "prov:wasDerivedFrom",          # derivation chain
        ):
            self.assertIn(edge, envelope)
        # Model-derivation lineage arrives through the AI-touched conditionals,
        # not as an unconditional field: lineage is REQUIRED for AI-touched
        # origins and forbidden otherwise (§5.3, §3.5).
        conditional_fields = {
            prop.name
            for shape in self._document("assertion").shapes
            if shape.name == "AssertionEnvelope"
            for branch in shape.conditionals
            for prop in branch.then_require
        }
        self.assertIn("rkaf:hasAILineage", conditional_fields)
        # Human approval is NOT an envelope edge. It is an Attestation whose
        # target is the assertion, so the assertion does not change when a
        # reviewer decides.
        self.assertNotIn("rkaf:hasApproval", envelope)
        self.assertNotIn("rkaf:decision", envelope)


class SourceFragmentIdentityTests(unittest.TestCase):
    """Core §4.2 — a SourceFragment names ONE region of ONE Artifact state.

    Fragment identity is three REQUIRED bindings — the exact artifact, the
    selector, and the kind of selector it is — plus the coordinate system, which
    is required ON the offset-bearing selector rather than on the fragment.
    `rkaf:sourceArtifactDigest` is the separate STATE binding: RECOMMENDED in
    general, obligatory for evidence, and deliberately not required by
    cardinality (§4.2 says so normatively, and five positives depend on it).

    These tests pin each binding to the compiled artifacts, because every one of
    them was a comment before it was a constraint, and a comment does not stop a
    producer from shipping a fragment that names a region only by luck. The
    cross-node rule that stops the selector contract being opt-in is hand
    authored; `CrossNodeAgreementShapeTests` exercises it.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "source-fragment.cue"
        self.document = parse_cue_file(self.source)
        self.shapes = {shape.name: shape for shape in self.document.shapes}
        self.shacl = (
            REPO_ROOT / "compiled" / "shacl" / "core" / "source-fragment.ttl"
        ).read_text()
        self.schema = json.loads(
            (
                REPO_ROOT
                / "compiled"
                / "json-schema"
                / "core"
                / "source-fragment.schema.json"
            ).read_text()
        )

    def _property(self, shape: str, name: str):
        return next(
            prop for prop in self.shapes[shape].properties if prop.name == name
        )

    def test_artifact_binding_is_an_iri_with_a_class_range(self) -> None:
        """`oa:hasSource` names an Artifact, not any IRI at all.

        Before this change the field was a bare `string`: a fragment could
        point at a workspace, a proceeding, a free-text label, or nothing
        resolvable, and every target accepted it. The lexical floor lives in
        the CUE; the class range lives in the range registry and reaches SHACL
        as `sh:class`, which is the only target that can follow a reference.

        This is the ONE exception to §9.1's "Rulespec declines L1/L3
        constraints over OA predicate ranges", and §9.1's OA row names it as
        such — a fragment of a workspace or an actor addresses no document
        region at all.
        """
        prop = self._property("SourceFragment", "oa:hasSource")
        self.assertFalse(prop.optional)
        self.assertEqual(prop.pattern, IRI_PATTERN)
        ranges = _scan_reference_class_registry(self.source)
        self.assertEqual(ranges.get("oa:hasSource"), "rkaf:Artifact")
        self.assertRegex(
            self.shacl,
            r"sh:path oa:hasSource ;[^\n]*sh:class rkaf:Artifact",
        )
        self.assertEqual(
            self.schema["$defs"]["SourceFragment"]["properties"]["oa:hasSource"][
                "pattern"
            ],
            IRI_PATTERN,
        )

    def test_position_selector_declares_its_coordinate_system(self) -> None:
        """An offset with no declared unit is not a coordinate.

        `4180` names three different positions depending on whether the
        producer counted Unicode code points, UTF-8 bytes, or UTF-16 code
        units, and they diverge at the first non-ASCII character. The unit is
        required on the SELECTOR rather than on the fragment because it belongs
        to whatever counts in it — a fragment carrying a quote selector and a
        position selector has exactly one coordinate system, and it is the
        position selector's.
        """
        prop = self._property("TextPositionSelector", "rkaf:coordinateSystem")
        self.assertFalse(prop.optional, "the unit is not optional on offsets")
        self.assertEqual(prop.enum_ref, "CoordinateSystem")
        values = next(
            enum.values
            for enum in self.document.enums
            if enum.name == "CoordinateSystem"
        )
        self.assertIn("rkaf:unicode-codepoint", values)
        self.assertIn("rkaf:utf8-byte", values)
        self.assertIn("rkaf:utf16-code-unit", values)
        self.assertRegex(
            self.shacl,
            r"sh:path rkaf:coordinateSystem ; sh:minCount 1 ;[^\n]*sh:in \(",
        )
        # The fragment does NOT carry the unit: a second declaration there
        # would let a fragment and its selector disagree about what an offset
        # means, with no rule to break the tie.
        self.assertNotIn(
            "rkaf:coordinateSystem",
            {prop.name for prop in self.shapes["SourceFragment"].properties},
        )

    def test_position_selector_rejects_an_inverted_range(self) -> None:
        """A region whose end precedes its start selects nothing."""
        orders = self.shapes["TextPositionSelector"].orders
        self.assertEqual(
            [(order.lower_property, order.upper_property) for order in orders],
            [("oa:start", "oa:end")],
        )
        self.assertIn("sh:lessThanOrEquals oa:end", self.shacl)
        self.assertEqual(
            self.schema["$defs"]["TextPositionSelector"]["x-rkaf-order"],
            [{"lower": "oa:start", "upper": "oa:end"}],
        )

    def test_both_digest_bindings_are_digests(self) -> None:
        """The state binding and the region binding are sha256, not free text.

        `rkaf:sourceArtifactDigest` pins the Artifact state the coordinates
        address; `rkaf:fragmentContentDigest` pins the region text they select.
        A digest that is not lexically a digest cannot be compared against
        `rkaf:hasContentDigest` on the Artifact, so it detects nothing.
        """
        digest_pattern = r"^sha256:[0-9a-f]{64}$"
        for name in ("rkaf:sourceArtifactDigest", "rkaf:fragmentContentDigest"):
            with self.subTest(property=name):
                prop = self._property("SourceFragment", name)
                self.assertTrue(prop.optional)
                self.assertEqual(prop.pattern, digest_pattern)
                self.assertIn(f'sh:path {name} ; sh:maxCount 1 ; sh:pattern "{digest_pattern}"', self.shacl)


class ArtifactVersionIdentityTests(unittest.TestCase):
    """Core §4.1 — version lineage must be cited, never inferred.

    The vision forbids inferring lineage from a shared title, topic, RIN,
    identifier fragment, embedding score, or retrieval rank. A prohibition no
    schema can check is one producers discover in review, so the CUE turns it
    into two conditionals: a version or revision claim MUST cite the source
    regions that state it, and a cited claim MUST come from a digest-addressable
    state.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "artifact.cue"
        self.document = parse_cue_file(self.source)
        self.shape = next(
            shape for shape in self.document.shapes if shape.name == "Artifact"
        )
        self.shacl = (
            REPO_ROOT / "compiled" / "shacl" / "core" / "artifact.ttl"
        ).read_text()
        self.schema = json.loads(
            (
                REPO_ROOT / "compiled" / "json-schema" / "core" / "artifact.schema.json"
            ).read_text()
        )["$defs"]["Artifact"]

    def _guards(self) -> dict[str, set[str]]:
        return {
            branch.when_property: {prop.name for prop in branch.then_require}
            for branch in self.shape.conditionals
        }

    def test_both_lineage_predicates_require_cited_evidence(self) -> None:
        guards = self._guards()
        for predicate in ("dcterms:isVersionOf", "prov:wasRevisionOf"):
            with self.subTest(predicate=predicate):
                self.assertIn(predicate, guards)
                self.assertIn("rkaf:versionLineageEvidence", guards[predicate])

    def test_cited_lineage_requires_a_content_digest(self) -> None:
        guards = self._guards()
        self.assertIn("rkaf:versionLineageEvidence", guards)
        self.assertIn("rkaf:hasContentDigest", guards["rkaf:versionLineageEvidence"])

    def test_lineage_evidence_resolves_to_source_regions(self) -> None:
        """"Evidence" means a SourceFragment, not any IRI.

        A version claim citing an actor, a score, or a bare label would satisfy
        a presence check while proving nothing. The class range is what makes
        the citation resolve to exact coordinates in an actual document.
        """
        ranges = _scan_reference_class_registry(self.source)
        self.assertEqual(
            ranges.get("rkaf:versionLineageEvidence"), "rkaf:SourceFragment"
        )
        self.assertRegex(
            self.shacl,
            r"sh:path rkaf:versionLineageEvidence ;[^\n]*sh:class rkaf:SourceFragment",
        )

    def test_format_siblings_are_not_a_version_claim(self) -> None:
        """Cross-posting must NOT trip the lineage rules.

        `dcterms:hasFormat` / `isFormatOf` relate two renderings of the SAME
        state. Guarding on them would force every registry cross-posting to
        invent lineage evidence for a version relation it never asserted.
        """
        guards = self._guards()
        self.assertNotIn("dcterms:hasFormat", guards)
        self.assertNotIn("dcterms:isFormatOf", guards)

    def test_no_universal_work_class_is_minted(self) -> None:
        """`dcterms:isVersionOf` keeps NO class range, deliberately.

        §4.1 declines to mint a universal Rulespec Work / Expression /
        Manifestation hierarchy: the stable resource keeps whatever public type
        owns it. A class range here would be that hierarchy arriving through
        the range registry instead of through the spec, and it would reject
        every producer composing ELI, BIBFRAME, or Schema.org.
        """
        ranges = _scan_reference_class_registry(self.source)
        self.assertNotIn("dcterms:isVersionOf", ranges)
        self.assertNotIn(
            "sh:path dcterms:isVersionOf ; sh:class", self.shacl.replace("\n", " ")
        )
        self.assertNotRegex(
            self.shacl,
            r"sh:path dcterms:isVersionOf ;[^\n]*sh:class",
        )


class AILineageApprovalSeparationTests(unittest.TestCase):
    """Core §2.4, §5.3 — lineage records derivation, never approval.

    `rkaf:aiSuggested` MEANS "unreviewed candidate". While `rkaf:AILineage`
    required `rkaf:humanApprover`, every such assertion had to name a reviewer,
    so the only way to record an honest candidate was to invent one. These
    tests pin the resolution from both sides: the approver is optional, and a
    lineage carrying the traces of a review still has to name the reviewer.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "ai-lineage.cue"
        self.document = parse_cue_file(self.source)
        self.shape = next(
            shape for shape in self.document.shapes if shape.name == "AILineage"
        )
        self.properties = {prop.name: prop for prop in self.shape.properties}
        self.schema = json.loads(
            (
                REPO_ROOT
                / "compiled"
                / "json-schema"
                / "core"
                / "ai-lineage.schema.json"
            ).read_text()
        )["$defs"]["AILineage"]
        self.shacl = (
            REPO_ROOT / "compiled" / "shacl" / "core" / "ai-lineage.ttl"
        ).read_text()

    def test_an_unreviewed_candidate_is_representable(self) -> None:
        self.assertTrue(self.properties["rkaf:humanApprover"].optional)
        self.assertNotIn("rkaf:humanApprover", self.schema.get("required", []))
        # The UNCONDITIONAL property row must carry no `sh:minCount`. The
        # rationale guard below legitimately emits one inside its Pattern-C
        # branch, so a bare substring search would pass whether the approver
        # were required or not; anchor on the top-level row instead.
        rows = re.findall(
            r"^  sh:property \[ sh:path rkaf:humanApprover ;(.*)$",
            self.shacl,
            re.MULTILINE,
        )
        self.assertEqual(len(rows), 1)
        self.assertNotIn("sh:minCount", rows[0])
        self.assertIn("sh:maxCount 1", rows[0])

    def test_the_ai_touched_conditional_accepts_an_approver_free_lineage(
        self,
    ) -> None:
        """The envelope requires LINEAGE, not approval.

        If the AI-touched guard had been rewritten to demand an approver — or
        if it required a second record alongside the lineage — the resolution
        would be cosmetic: an unreviewed candidate would still be unsayable.
        """
        envelope = next(
            shape
            for shape in parse_cue_file(
                REPO_ROOT / "constraints" / "core" / "assertion.cue"
            ).shapes
            if shape.name == "AssertionEnvelope"
        )
        guarded = {
            branch.when_equals: {prop.name for prop in branch.then_require}
            for branch in envelope.conditionals
        }
        for origin in AI_TOUCHED_ORIGINS:
            with self.subTest(origin=origin):
                self.assertEqual(guarded[origin], {"rkaf:hasAILineage"})

    def test_a_stated_rationale_still_names_its_human(self) -> None:
        """A review attributed to nobody is worse than no review.

        `rkaf:humanRationale` is a human's stated reason for accepting the
        output. Carried without `rkaf:humanApprover`, the record READS as
        approved while leaving no one accountable — a strictly worse failure
        than an honest unreviewed candidate.
        """
        guards = {
            branch.when_property: {prop.name for prop in branch.then_require}
            for branch in self.shape.conditionals
        }
        self.assertEqual(
            guards.get("rkaf:humanRationale"), {"rkaf:humanApprover"}
        )
        self.assertIn("sh:path rkaf:humanRationale ; sh:minCount 1", self.shacl)

    def test_the_input_context_hash_is_a_digest(self) -> None:
        self.assertEqual(
            self.properties["rkaf:inputContextHash"].pattern,
            r"^sha256:[0-9a-f]{64}$",
        )

    def test_lineage_carries_no_approval_decision(self) -> None:
        """Approval lives on Attestation, and only there."""
        for approval_term in (
            "rkaf:decision",
            "rkaf:attestor",
            "rkaf:attestorKind",
            "rkaf:attestedAt",
            "rkaf:attestationScope",
            "rkaf:revokedAt",
        ):
            self.assertNotIn(approval_term, self.properties)


class ConceptAssignmentTests(unittest.TestCase):
    """Core §4.7 — assignments are evidence-bearing, and the flow is one-way.

    Two properties carry the whole design. First, exactly two kinds of thing
    are taggable and they are not interchangeable. Second, evidence flows UP
    from segments to documents and never back down: a document tag may
    shortlist candidates for a segment and can never prove one. Without the
    second rule a single mistaken document tag propagates to every segment and
    the segments then confirm the document.
    """

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "concept-assignment.cue"
        self.document = parse_cue_file(self.source)
        self.shape = next(
            shape
            for shape in self.document.shapes
            if shape.name == "ConceptAssignment"
        )
        self.properties = {prop.name: prop for prop in self.shape.properties}
        self.shacl = (
            REPO_ROOT / "compiled" / "shacl" / "core" / "concept-assignment.ttl"
        ).read_text()
        self.schema = json.loads(
            (
                REPO_ROOT
                / "compiled"
                / "json-schema"
                / "core"
                / "concept-assignment.schema.json"
            ).read_text()
        )["$defs"]["ConceptAssignment"]

    def _guards(self) -> dict[tuple[str, str | None], set[str]]:
        return {
            (branch.when_property, branch.when_equals): {
                prop.name for prop in branch.then_require
            }
            for branch in self.shape.conditionals
        }

    def test_exactly_two_subject_kinds_are_taggable(self) -> None:
        values = next(
            enum.values
            for enum in self.document.enums
            if enum.name == "AssignmentSubjectType"
        )
        self.assertEqual(values, ["rkaf:Artifact", "rkaf:SourceFragment"])
        self.assertIn(
            "sh:path rkaf:assignmentSubjectType ; sh:minCount 1 ; sh:maxCount 1 ; "
            "sh:in ( rkaf:Artifact rkaf:SourceFragment )",
            self.shacl,
        )
        for name in ("rkaf:assignmentSubject", "rkaf:assignmentSubjectType"):
            self.assertFalse(self.properties[name].optional)

    def test_a_segment_tag_needs_evidence_from_that_segment(self) -> None:
        """The rule that stops a document tag from confirming itself."""
        guards = self._guards()
        self.assertEqual(
            guards.get(("rkaf:assignmentSubjectType", "rkaf:SourceFragment")),
            {"rkaf:assignmentEvidence"},
        )
        self.assertIn(
            "sh:path rkaf:assignmentSubjectType ; sh:hasValue rkaf:SourceFragment",
            self.shacl,
        )

    def test_direct_and_derived_carry_different_obligations(self) -> None:
        guards = self._guards()
        self.assertEqual(
            guards.get(("rkaf:assignmentDerivation", "rkaf:directAssignment")),
            {"rkaf:assignmentEvidence"},
        )
        self.assertEqual(
            guards.get(("rkaf:assignmentDerivation", "rkaf:derivedAssignment")),
            {"rkaf:supportingAssignment"},
        )

    def test_aggregation_names_the_documented_rule(self) -> None:
        """"A documented rule may combine segment tags" needs WHICH rule."""
        guards = self._guards()
        self.assertEqual(
            guards.get(("rkaf:supportingAssignment", None)),
            {"rkaf:assignmentPolicyVersion"},
        )

    def test_evidence_and_supports_resolve_to_real_records(self) -> None:
        ranges = _scan_reference_class_registry(self.source)
        self.assertEqual(
            ranges.get("rkaf:assignmentEvidence"), "rkaf:SourceFragment"
        )
        self.assertEqual(
            ranges.get("rkaf:supportingAssignment"), "rkaf:ConceptAssignment"
        )
        self.assertRegex(
            self.shacl,
            r"sh:path rkaf:assignmentEvidence ;[^\n]*sh:class rkaf:SourceFragment",
        )
        self.assertRegex(
            self.shacl,
            r"sh:path rkaf:supportingAssignment ;[^\n]*sh:class rkaf:ConceptAssignment",
        )

    def test_the_envelope_is_composed_not_restated(self) -> None:
        """Trust context has one home, and the assignment reuses it.

        A parallel `rkaf:assignmentConfidence` or `rkaf:assignmentApprover`
        would create a second place to look for the same fact and a second
        place to forget to look.
        """
        for field in ASSERTION_ENVELOPE_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, self.properties)
        for invented in (
            "rkaf:assignmentConfidence",
            "rkaf:assignmentApprover",
            "rkaf:assignmentDecision",
            "rkaf:assignmentLineage",
        ):
            self.assertNotIn(invented, self.properties)

    def test_no_proposition_core_is_composed(self) -> None:
        """An assignment's proposition is the subject-concept pair.

        Composing `#AssertionProposition` would demand an
        `rkaf:assertsPredicate` that every assignment fills with the same
        placeholder — a required field carrying no information.
        """
        for field in ASSERTION_PROPOSITION_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn(field, self.properties)

    def test_derivation_is_orthogonal_to_construction_origin(self) -> None:
        """`assignmentDerivation` and `assertionOrigin` answer different
        questions: how the RECORD was structured versus what CONSTRUCTED it. A
        model may propose a direct assignment; a deterministic rule may compute
        a derived one. Collapsing them would make "a model said so" and "it was
        aggregated" the same fact."""
        derivation = next(
            enum.values
            for enum in self.document.enums
            if enum.name == "AssignmentDerivation"
        )
        origins = next(
            enum.values
            for enum in parse_cue_file(
                REPO_ROOT / "constraints" / "core" / "assertion.cue"
            ).enums
            if enum.name == "AssertionOrigin"
        )
        self.assertEqual(set(derivation) & set(origins), set())


class ConceptSchemeTests(unittest.TestCase):
    """Core §4.7.1 — SKOS owns scheme semantics; Rulespec adds facet and owner."""

    def setUp(self) -> None:
        self.source = REPO_ROOT / "constraints" / "core" / "concept.cue"
        self.document = parse_cue_file(self.source)
        self.shapes = {shape.name: shape for shape in self.document.shapes}
        self.shacl = (
            REPO_ROOT / "compiled" / "shacl" / "core" / "concept.ttl"
        ).read_text()

    def _properties(self, shape: str) -> dict:
        return {prop.name: prop for prop in self.shapes[shape].properties}

    def test_a_scheme_declares_which_facet_it_controls(self) -> None:
        """Facets merge when nothing says which one a scheme answers.

        Topic, industry, organization, place, document role, and legal status
        all hold terms; only the declared facet tells them apart. The facet is
        an IRI rather than a kernel enum because Rulespec has no standing to
        own a universal facet taxonomy.
        """
        facet = self._properties("ConceptScheme")["rkaf:schemeFacet"]
        self.assertFalse(facet.optional)
        self.assertEqual(facet.pattern, IRI_PATTERN)
        self.assertIsNone(facet.enum_ref)
        self.assertIsNone(facet.inline_enum_values)

    def test_a_scheme_is_registry_governed_or_workspace_defined(self) -> None:
        branches = self.shapes["ConceptScheme"].disjunctions
        self.assertEqual(len(branches), 1)
        self.assertEqual(
            [
                {prop.name for prop in branch.properties}
                for branch in branches[0]
            ],
            [{"rkaf:managedByRegistry"}, {"rkaf:definedInScope"}],
        )
        self.assertIn("sh:path rkaf:managedByRegistry ; sh:minCount 1", self.shacl)
        self.assertIn("sh:path rkaf:definedInScope ; sh:minCount 1", self.shacl)

    def test_both_concept_flavors_carry_a_scheme(self) -> None:
        for shape in ("RegisteredConcept", "LocalConcept"):
            with self.subTest(shape=shape):
                in_scheme = self._properties(shape)["skos:inScheme"]
                self.assertFalse(in_scheme.optional)

    def test_skos_membership_keeps_no_rulespec_class_range(self) -> None:
        """A concept may live in an external thesaurus.

        `skos:inScheme` and `rkaf:assignedConcept` are deliberately absent from
        the range registry: constraining them to `rkaf:ConceptScheme` /
        `rkaf:RegisteredConcept` would reject every producer composing an
        external SKOS vocabulary, which is the composition §9.4 requires.
        """
        ranges = _scan_reference_class_registry(self.source)
        self.assertNotIn("skos:inScheme", ranges)
        self.assertNotIn("rkaf:assignedConcept", ranges)

    def test_promotion_requires_a_written_definition(self) -> None:
        for shape in ("RegisteredConcept", "LocalConcept"):
            with self.subTest(shape=shape):
                guards = {
                    (branch.when_property, branch.when_equals): {
                        prop.name for prop in branch.then_require
                    }
                    for branch in self.shapes[shape].conditionals
                }
                self.assertEqual(
                    guards.get(("rkaf:conceptStatus", "rkaf:promoted")),
                    {"skos:definition"},
                )

    def test_skos_mapping_properties_are_available_and_nothing_was_removed(
        self,
    ) -> None:
        """SKOS separates in-scheme relations from cross-scheme mappings.

        Without the `*Match` half a producer aligning to an external thesaurus
        had to reach for `skos:broader` and misstate the alignment as if both
        concepts lived in one vocabulary. The three earlier in-scheme values
        stay legal: this is an addition, and every mapping valid before the
        change is still valid.
        """
        values = next(
            enum.values
            for enum in parse_cue_file(
                REPO_ROOT / "constraints" / "core" / "concept-mapping.cue"
            ).enums
            if enum.name == "SkosMappingPredicate"
        )
        for added in ("skos:broadMatch", "skos:narrowMatch", "skos:relatedMatch"):
            self.assertIn(added, values)
        for preserved in (
            "skos:closeMatch",
            "skos:exactMatch",
            "skos:broader",
            "skos:narrower",
            "skos:related",
            "skos:mappingRelation",
        ):
            self.assertIn(preserved, values)

    def test_the_hand_authored_shape_closes_the_same_mapping_set(self) -> None:
        """SHACL is conjunctive, so the two lists must agree exactly.

        `shapes/rkaf-shapes-conceptregistry.ttl` and the compiled shape both
        emit `sh:in` over `rkaf:mappingRelation`. A value present in one and
        absent from the other is rejected by the merged suite no matter what
        the compiled artifact says, which would make the CUE source a lie.
        """
        authored = (
            REPO_ROOT / "shapes" / "rkaf-shapes-conceptregistry.ttl"
        ).read_text()
        closure = re.search(
            r"sh:path rkaf:mappingRelation ;.*?sh:in \((.*?)\) ;",
            authored,
            re.DOTALL,
        )
        self.assertIsNotNone(closure)
        authored_values = set(closure.group(1).split())
        cue_values = set(
            next(
                enum.values
                for enum in parse_cue_file(
                    REPO_ROOT / "constraints" / "core" / "concept-mapping.cue"
                ).enums
                if enum.name == "SkosMappingPredicate"
            )
        )
        self.assertEqual(authored_values, cue_values)


TURTLE_PREAMBLE = """
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix oa:   <http://www.w3.org/ns/oa#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rkaf: <https://rulespec.org/ns/v1#> .
@prefix ex:   <urn:rkaf:test:> .
"""


class CrossNodeAgreementShapeTests(unittest.TestCase):
    """Hand-authored rules that compare ONE node's value to ANOTHER node's class.

    Layer 2 emits per-property constraints. A rule of the form "the thing this
    IRI resolves to must be a Y" or "these two nodes must agree" has no carrier
    there, so three of them live in `shapes/rkaf-shapes-core.ttl` beside the
    subclass axioms. Each one closes an evasion that passed every compiled
    target, so these tests run the shapes rather than reading them: a shape that
    parses but never fires would satisfy a text assertion and satisfy nothing
    else.

    Each case is paired — the evasion is rejected AND the honest record that
    differs from it by one fact is accepted. An over-broad shape fails the
    second half.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import rdflib

        cls.rdflib = rdflib
        cls.shapes = rdflib.Graph()
        cls.shapes.parse(
            str(REPO_ROOT / "shapes" / "rkaf-shapes-core.ttl"), format="turtle"
        )
        for name in ("source-fragment", "concept-assignment", "artifact"):
            cls.shapes.parse(
                str(REPO_ROOT / "compiled" / "shacl" / "core" / f"{name}.ttl"),
                format="turtle",
            )

    def _conforms(self, turtle: str) -> bool:
        from pyshacl import validate

        data = self.rdflib.Graph()
        data.parse(data=TURTLE_PREAMBLE + turtle, format="turtle")
        conforms, _, _ = validate(
            data_graph=data,
            shacl_graph=self.shapes,
            inference="rdfs",
            advanced=True,
            meta_shacl=False,
        )
        return conforms

    # ---------------------------------------------------------------- §4.2

    _ARTIFACT = """
    ex:artifact a rkaf:Artifact ;
      rkaf:hasArtifactIdentifier "urn:rkaf:test:artifact" ;
      rkaf:artifactIdentifierScheme rkaf:partner-defined .
    """

    def test_a_declared_position_selector_must_be_a_typed_one(self) -> None:
        """Declaring the kind and attaching nothing typed is the evasion.

        `rkaf:coordinateSystem` and the offset ordering are required by
        `rkaf:TextPositionSelectorShape`, which targets `oa:TextPositionSelector`
        — so both fire only on a node the producer chose to type. Omitting the
        `@type` left an unreproducible region passing every target.
        """
        evasion = (
            self._ARTIFACT
            + """
            ex:fragment a rkaf:SourceFragment ;
              oa:hasSource ex:artifact ;
              oa:hasSelector ex:selector ;
              rkaf:selectorKind oa:TextPositionSelector .
            ex:selector oa:start 4180 ; oa:end 4222 .
            """
        )
        self.assertFalse(
            self._conforms(evasion),
            "an untyped node carrying offsets satisfied the position-selector "
            "declaration",
        )

        honest = (
            self._ARTIFACT
            + """
            ex:fragment a rkaf:SourceFragment ;
              oa:hasSource ex:artifact ;
              oa:hasSelector ex:selector ;
              rkaf:selectorKind oa:TextPositionSelector .
            ex:selector a oa:TextPositionSelector ;
              oa:start 4180 ; oa:end 4222 ;
              rkaf:coordinateSystem rkaf:unicode-codepoint .
            """
        )
        self.assertTrue(self._conforms(honest))

    def test_other_selector_kinds_keep_their_bare_value_form(self) -> None:
        """The rule is SCOPED, and the scope is load-bearing.

        `sourcefragment-with-freshness-positive` attaches the bare string
        "§ 273.2" under `rkaf:uslm-section`. A blanket "every declared kind
        needs a typed selector" rule would reject it, so widening the shape has
        to fail here before it reaches the fixture gate.
        """
        self.assertTrue(
            self._conforms(
                self._ARTIFACT
                + """
                ex:fragment a rkaf:SourceFragment ;
                  oa:hasSource ex:artifact ;
                  oa:hasSelector "§ 273.2" ;
                  rkaf:selectorKind rkaf:uslm-section .
                """
            )
        )

    # -------------------------------------------------------------- §4.7.3

    _FRAGMENT = """
    ex:fragment a rkaf:SourceFragment ;
      oa:hasSource ex:artifact ;
      oa:hasSelector ex:selector ;
      rkaf:selectorKind oa:TextQuoteSelector .
    ex:selector a oa:TextQuoteSelector ; oa:exact "countable household income" .
    """

    @staticmethod
    def _assignment(subject: str, subject_type: str, tail: str) -> str:
        return f"""
        ex:assignment a rkaf:ConceptAssignment ;
          rkaf:assignmentSubject {subject} ;
          rkaf:assignmentSubjectType {subject_type} ;
          rkaf:assignedConcept ex:concept ;
          skos:inScheme ex:scheme ;
          rkaf:assignmentRole rkaf:assignmentSubstantive ;
          rkaf:assignmentDerivation rkaf:derivedAssignment ;
          rkaf:supportingAssignment ex:other-assignment ;
          rkaf:assignmentPolicyVersion "test/1.0.0" ;
          rkaf:assertionOrigin rkaf:humanAsserted ;
          {tail}
        ex:other-assignment a rkaf:ConceptAssignment ;
          rkaf:assignmentSubject ex:artifact ;
          rkaf:assignmentSubjectType rkaf:Artifact ;
          rkaf:assignedConcept ex:concept ;
          skos:inScheme ex:scheme ;
          rkaf:assignmentRole rkaf:assignmentPrimary ;
          rkaf:assignmentDerivation rkaf:directAssignment ;
          rkaf:assignmentEvidence ex:fragment ;
          rkaf:assertionOrigin rkaf:humanAsserted .
        """

    def test_a_mislabelled_fragment_subject_still_needs_evidence(self) -> None:
        """The subject-type conditional keys on a literal the producer writes.

        Changing one enum value from `rkaf:SourceFragment` to `rkaf:Artifact`
        bought a segment assignment the document-tag treatment while its subject
        IRI still resolved to a fragment — so the document tag proved the
        section tag, which §4.7.3 forbids outright.
        """
        self.assertFalse(
            self._conforms(
                self._ARTIFACT
                + self._FRAGMENT
                + self._assignment("ex:fragment", "rkaf:Artifact", ".")
            ),
            "relabelling the subject type evaded the local-evidence rule",
        )
        self.assertTrue(
            self._conforms(
                self._ARTIFACT
                + self._FRAGMENT
                + self._assignment(
                    "ex:fragment",
                    "rkaf:SourceFragment",
                    "rkaf:assignmentEvidence ex:fragment .",
                )
            )
        )

    def test_an_absent_subject_node_is_not_an_accusation(self) -> None:
        """A standalone assignment document must validate as it always did.

        The rule is written as "the subject does not resolve to a fragment OR
        evidence is present", so a graph that simply does not contain the
        subject node stays silent. Written the other way round it would reject
        every assignment shipped without its subject.
        """
        self.assertTrue(
            self._conforms(
                self._ARTIFACT
                + self._FRAGMENT
                + self._assignment("ex:absent-subject", "rkaf:Artifact", ".")
            )
        )

    def test_cited_evidence_must_name_the_subject_artifact(self) -> None:
        """"Some fragment somewhere" is not local evidence.

        The class range is satisfied by any `rkaf:SourceFragment` at all, so one
        preamble sentence in an unrelated handbook could carry every segment tag
        in a corpus — the self-confirming loop the evidence rule exists to
        break.
        """
        other_document = """
        ex:artifact-b a rkaf:Artifact ;
          rkaf:hasArtifactIdentifier "urn:rkaf:test:artifact-b" ;
          rkaf:artifactIdentifierScheme rkaf:partner-defined .
        ex:fragment-b a rkaf:SourceFragment ;
          oa:hasSource ex:artifact-b ;
          oa:hasSelector ex:selector-b ;
          rkaf:selectorKind oa:TextQuoteSelector .
        ex:selector-b a oa:TextQuoteSelector ; oa:exact "unrelated preamble" .
        """
        self.assertFalse(
            self._conforms(
                self._ARTIFACT
                + self._FRAGMENT
                + other_document
                + self._assignment(
                    "ex:fragment",
                    "rkaf:SourceFragment",
                    "rkaf:assignmentEvidence ex:fragment-b .",
                )
            ),
            "evidence from another Artifact satisfied the local-evidence rule",
        )
        self.assertTrue(
            self._conforms(
                self._ARTIFACT
                + self._FRAGMENT
                + other_document
                + self._assignment(
                    "ex:fragment",
                    "rkaf:SourceFragment",
                    "rkaf:assignmentEvidence ex:fragment .",
                )
            )
        )


class L2DispatchPrefixTests(unittest.TestCase):
    """Both L2 dispatchers bind the SAME set of `@type` prefixes.

    Core §4.2 compiles class shapes for two OA selector classes. Filtering the
    embedded registry on `rkaf:` left both unbound, so the shipped Rust
    validator and the conformance reporter each reported `pass` on a selector
    with an inverted range or no declared unit — and the only numeric
    `x-rkaf-order` in the repo was in a class neither of them registered, which
    made the numeric ordering branch dead code.

    The two dispatchers are independent implementations, so nothing but a test
    keeps them agreeing.
    """

    def test_the_python_registry_binds_both_selector_classes(self) -> None:
        bindings = conformance_lib.schema_bindings()
        self.assertEqual(
            bindings["oa:TextPositionSelector"].class_name, "TextPositionSelector"
        )
        self.assertEqual(
            bindings["oa:TextQuoteSelector"].class_name, "TextQuoteSelector"
        )

    def test_the_rust_build_script_binds_the_same_prefixes(self) -> None:
        build_rs = (
            REPO_ROOT / "crates" / "rkaf-validate" / "build.rs"
        ).read_text()
        filter_line = re.search(
            r"if !\((?P<test>.*?starts_with.*?)\)\s*\{\s*continue;",
            build_rs,
            re.DOTALL,
        )
        self.assertIsNotNone(
            filter_line, "build.rs no longer filters `@type` by prefix"
        )
        rust_prefixes = set(re.findall(r'starts_with\("([^"]+)"\)', filter_line["test"]))
        self.assertEqual(rust_prefixes, set(conformance_lib.L2_TYPE_PREFIXES))

    def test_the_only_numeric_ordering_class_is_dispatched(self) -> None:
        """The numeric branch of the ordering check must be reachable.

        `x-rkaf-order` is type-agnostic — the same CUE expression guards an ISO
        date interval and an integer offset pair. If every class carrying a
        NUMERIC order were unbound, the numeric comparison would be untested
        code claiming to enforce something.
        """
        numeric_ordered = set()
        for path in conformance_lib.compiled_json_schema_paths():
            for class_name, class_schema in json.loads(
                path.read_text()
            ).get("$defs", {}).items():
                if not isinstance(class_schema, dict):
                    continue
                properties = class_schema.get("properties", {})
                for order in class_schema.get("x-rkaf-order", []):
                    lower = properties.get(order["lower"], {})
                    if lower.get("type") in ("integer", "number"):
                        numeric_ordered.add(
                            properties.get("@type", {}).get("const", class_name)
                        )
        self.assertTrue(
            numeric_ordered, "no class carries a numeric x-rkaf-order any more"
        )
        bound = set(conformance_lib.schema_bindings())
        self.assertTrue(
            numeric_ordered <= bound,
            f"numeric-ordered classes are not L2-dispatched: {numeric_ordered - bound}",
        )


if __name__ == "__main__":
    unittest.main()
