from __future__ import annotations

import json
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tools import conformance_lib
from tools.constraints_compile import (
    CompileError,
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

# The generic Assertion envelope (constraints/core/assertion.cue). Every one of
# these MUST reach RelationshipAssertion through CUE composition — the envelope
# has exactly one source — and must still arrive in every compiled target.
#
# Composition may DE-DUPLICATE; it must never LOOSEN. A derived shape is
# therefore allowed to restate an envelope field in order to NARROW it (see
# RELATIONSHIP_ASSERTION_NARROWINGS below); what it may not do is arrive at a
# weaker compiled artifact than the CUE source enforces.
ASSERTION_ENVELOPE_FIELDS = (
    "rkaf:assertionOrigin",
    "rkaf:usageEligibility",
    "rkaf:hasApplicability",
    "rkaf:hasJustification",
    "rkaf:hasWarrant",
    "rkaf:hasAuthority",
    "prov:wasDerivedFrom",
    "rkaf:consumerLifecycleState",
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
        # composed document's local enum rather than failing on it.
        rego = target_rego(relationship_doc)
        self.assertIn("package rkaf.relationship_assertion", rego)
        self.assertIn(
            'assertion_polarity_values := ["rkaf:affirmed", "rkaf:denied"]',
            rego,
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

    # Domain values still declared by a kernel file, with the reason each one
    # has not moved yet. An entry here is a KNOWN, REPORTED debt, not a licence:
    # the assertion below pins the exact set, so a new leak fails even though
    # these remain.
    #
    # lifecycle-event.cue — `#LifecycleEventKind` mixes ten universal kinds with
    # twelve `rkaf:proceeding*` kinds. Splitting it is blocked, not merely
    # unfinished: the compiled kernel shape closes the enum with
    # `sh:in (...)` on `sh:targetClass rkaf:LifecycleEvent`, SHACL is
    # conjunctive, and `spec/rkaf-rulemaking.md` §6 commits the module to
    # `rkaf:LifecycleEvent` ("this module defines no parallel event class").
    # A profile overlay on the same class can therefore only ever intersect
    # the kernel's ten values, never restore the twelve. Minting a parallel
    # class instead would also drop proceeding events out of
    # `nodes_by_type("rkaf:LifecycleEvent")` in crates/rkaf-runtime, silently
    # removing them from cascade and staleness evaluation.
    KNOWN_KERNEL_DOMAIN_VALUES = {
        "lifecycle-event.cue": {
            "rkaf:proceedingConcluded",
            "rkaf:proceedingDisapproved",
            "rkaf:proceedingFinal",
            "rkaf:proceedingLongterm",
            "rkaf:proceedingPrerule",
            "rkaf:proceedingProposed",
            "rkaf:proceedingReinstated",
            "rkaf:proceedingRemanded",
            "rkaf:proceedingStayed",
            "rkaf:proceedingSupplemental",
            "rkaf:proceedingVacated",
            "rkaf:proceedingWithdrawn",
        },
    }

    # The ten kinds `#LifecycleEventKind` is allowed to keep: they name events
    # that happen to a governed assertion in ANY jurisdiction. FROZEN — this
    # allowlist is what turns the debt assertion below from a `rkaf:proceeding*`
    # prefix scan into a real gate. A new kernel kind that is neither on this
    # list nor already-recorded debt fails whatever it is called, so smuggling a
    # domain value in under a name like `rkaf:hearingScheduled` is caught too.
    UNIVERSAL_LIFECYCLE_EVENT_KINDS = frozenset({
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
    })

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

    def test_kernel_domain_value_debt_does_not_grow(self) -> None:
        """Pin the kernel's domain-value debt by ALLOWLIST, not by prefix.

        Two nets, because a prefix scan alone only catches debt that keeps
        announcing itself:

        1. Every kernel file, scanned for `rkaf:proceeding*` — the shape the
           recorded debt actually has today.
        2. `#LifecycleEventKind` measured against the frozen list of ten
           universal kinds. ANY value that is neither universal nor already
           recorded fails, whatever it is named.
        """
        found: dict[str, set[str]] = {}
        for cue in sorted(self.KERNEL_DIR.glob("*.cue")):
            values = set(re.findall(r'"(rkaf:proceeding\w*)"', cue.read_text()))
            if values:
                found[cue.name] = values
        self.assertEqual(
            self.KNOWN_KERNEL_DOMAIN_VALUES,
            found,
            "the set of proceeding-scoped values left in the kernel changed. "
            "Adding one is a regression; removing all of them means "
            "KNOWN_KERNEL_DOMAIN_VALUES should be emptied along with the "
            "blocker note above it.",
        )

        lifecycle = parse_cue_file(self.KERNEL_DIR / "lifecycle-event.cue")
        kinds = next(
            enum for enum in lifecycle.enums if enum.name == "LifecycleEventKind"
        )
        self.assertEqual(
            self.KNOWN_KERNEL_DOMAIN_VALUES["lifecycle-event.cue"],
            set(kinds.values) - self.UNIVERSAL_LIFECYCLE_EVENT_KINDS,
            "#LifecycleEventKind gained a kind that is neither one of the ten "
            "universal lifecycle kinds nor part of the recorded proceeding "
            "debt. A jurisdiction-specific event kind belongs in a profile; if "
            "the new kind really is universal, add it to "
            "UNIVERSAL_LIFECYCLE_EVENT_KINDS deliberately.",
        )
        self.assertTrue(
            self.UNIVERSAL_LIFECYCLE_EVENT_KINDS.issubset(set(kinds.values)),
            "#LifecycleEventKind dropped a universal kind; the allowlist and "
            "the enum must stay in step or this gate silently stops measuring.",
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
        self.assertEqual([], artifact.conditionals)

        schema = json.loads(target_json_schema(document))
        kernel = schema["$defs"]["Artifact"]
        for term in self.US_TERMS:
            self.assertNotIn(term, kernel["properties"])
        self.assertNotIn("allOf", kernel)
        self.assertNotIn("USRegulatoryIdentifierScheme", schema["$defs"])

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

    # Kernel SHACL enum closures the profile overlays currently DROP, keyed by
    # (overlay TTL relative to compiled/shacl/, target class, property).
    #
    # Adversarial-review finding F2: `target_shacl()` takes no cross-file enum
    # registry, so a property whose enum is defined in another CUE file loses
    # its `sh:in`. `rkaf:artifactIdentifierScheme` is declared by the kernel
    # `#Artifact`, and the overlay composes that shape, so the overlay's copy
    # arrives closure-free. `tools/constraints_parity.py` then validates the
    # us-regulatory-artifact rows against that overlay ALONE, comparing a
    # strict JSON Schema to a weakened shape.
    #
    # An entry here is KNOWN, REPORTED debt, not a licence: the assertion pins
    # the exact set, so a NEWLY dropped closure fails. Threading the registry
    # into `target_shacl` empties this set — which also fails, prompting whoever
    # lands it to delete the pin. See the `target_shacl` docstring for why the
    # obvious fix is not applied here: it unmasks a missing `@type` coercion on
    # `rkaf:capabilityCap` / `rkaf:lifecycleState` in the JSON-LD context.
    KNOWN_DROPPED_SHACL_ENUM_CLOSURES = {
        (
            "profiles/us-rulemaking/us-regulatory-artifact.ttl",
            "rkaf:Artifact",
            "rkaf:artifactIdentifierScheme",
        ),
    }

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
                    self.assertEqual(
                        definition,
                        overlay["properties"][name],
                        f"{pname} redefines kernel property {name}; an overlay "
                        "may ADD constraints, never restate one differently",
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
            "the set of kernel sh:in closures dropped by a profile overlay "
            "changed. Growing it is a regression; shrinking it to empty means "
            "finding F2 is fixed and KNOWN_DROPPED_SHACL_ENUM_CLOSURES should "
            "be emptied along with the note above it.",
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


if __name__ == "__main__":
    unittest.main()
