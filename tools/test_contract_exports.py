#!/usr/bin/env python3
"""Tests for the packaged contract exports.

`tools/build_contract_exports.py --check` is the drift gate: it proves the two
generated modules are what the sources say. This suite proves the properties a
consumer actually relies on, which byte equality cannot state:

  * the lattice is the lattice, in the order the CUE declares — read here
    straight from `usage-eligibility.cue`, not through the compiler the
    generator uses, so a compiler defect cannot confirm itself;
  * every enum constant agrees with the compiled JSON Schema shipped beside it;
  * every term the CUE declares is in the registry (the completeness the
    downstream ImportError check depends on) and every retired one is not;
  * the resource accessors resolve, and refuse to walk out of the packaged
    data.
"""

from __future__ import annotations

import json
import re
import unittest

# Imported first: this module puts `src/` on `sys.path`, the way every tools/
# shim does, because the distribution is deliberately not installed for the
# repository's own gates (see requirements.txt).
from tools.build_contract_exports import (
    CONSTRAINTS_DIR,
    CONTEXT_FILE,
    ROOT,
    attribute_name,
    constant_name,
    scan_terms,
    strip_cue_comments,
)

from rulespec_conformance.contract import (  # noqa: E402
    RKAF_NAMESPACE,
    USAGE_ELIGIBILITY,
    VERSION,
    enums,
    resources,
    terms,
)

COMPACT_IRI = re.compile(r"(?<!urn:)\brkaf:([A-Za-z][A-Za-z0-9_-]*)")

# Fields Rulespec retired. `shapes/rkaf-shapes-core.ttl` holds each at
# `sh:maxCount 0`, so data carrying one is invalid — and the registry must
# refuse the name rather than hand a consumer a string that looks fine.
RETIRED_TERMS = (
    "assignedConcept",
    "assignmentRole",
    "conceptStatus",
    "mappingRelation",
    "sourceConcept",
    "targetConcept",
)

# Names minted by the negative corpus and the Rust test modules to be wrong.
NON_TERMS = ("proceedingBogus", "WhateverNotARealContract", "NotATestCase")


class UsageEligibilityLatticeTests(unittest.TestCase):
    """The one enum whose ORDER the CUE calls normative."""

    def _lattice_from_source(self) -> tuple[str, ...]:
        source = CONSTRAINTS_DIR / "core" / "usage-eligibility.cue"
        text = strip_cue_comments(source.read_text(encoding="utf-8"))
        return tuple(f"rkaf:{name}" for name in COMPACT_IRI.findall(text))

    def test_matches_the_cue_disjunction_in_declaration_order(self) -> None:
        self.assertEqual(USAGE_ELIGIBILITY, self._lattice_from_source())

    def test_is_a_seven_member_lattice_from_not_eligible_to_official_use(self) -> None:
        self.assertEqual(len(USAGE_ELIGIBILITY), len(set(USAGE_ELIGIBILITY)))
        self.assertEqual(USAGE_ELIGIBILITY[0], "rkaf:notEligible")
        self.assertEqual(USAGE_ELIGIBILITY[-1], "rkaf:officialUse")

    def test_is_reachable_from_the_package_root_and_the_enums_module(self) -> None:
        self.assertIs(USAGE_ELIGIBILITY, enums.USAGE_ELIGIBILITY)
        self.assertIs(USAGE_ELIGIBILITY, enums.ENUMS["UsageEligibility"])


class EnumExportTests(unittest.TestCase):
    def test_every_enum_agrees_with_the_schema_compiled_from_the_same_cue(self) -> None:
        """Two projections of one source. Disagreement means two trees."""
        compared = 0
        for cue_name, values in enums.ENUMS.items():
            parts = enums.ENUM_SOURCES[cue_name].split("/")
            family, stem = "/".join(parts[1:-1]), parts[-1].removesuffix(".cue")
            schema = resources.json_schema(stem, family=family)
            packaged = schema.get("$defs", {}).get(cue_name, {}).get("enum")
            if packaged is None:
                continue
            compared += 1
            self.assertEqual(tuple(packaged), values, cue_name)
        self.assertGreater(compared, 0)

    def test_every_declared_enum_source_exists(self) -> None:
        for cue_name, relpath in enums.ENUM_SOURCES.items():
            self.assertTrue((ROOT / relpath).is_file(), f"{cue_name}: {relpath}")

    def test_constant_names_survive_acronyms(self) -> None:
        self.assertEqual(constant_name("UsageEligibility"), "USAGE_ELIGIBILITY")
        self.assertEqual(
            constant_name("USProceedingLifecycleEventKind"),
            "US_PROCEEDING_LIFECYCLE_EVENT_KIND",
        )
        self.assertEqual(
            constant_name("ProvisionalAIUsageEligibility"),
            "PROVISIONAL_AI_USAGE_ELIGIBILITY",
        )

    def test_unions_are_flattened_to_their_members(self) -> None:
        """`#WarrantKind` is six families; a consumer needs the members."""
        warrant_kind = enums.ENUMS["WarrantKind"]
        self.assertIn("rkaf:statutory", warrant_kind)
        self.assertIn("rkaf:peerReview", warrant_kind)
        self.assertEqual(len(warrant_kind), len(set(warrant_kind)))


class TermRegistryTests(unittest.TestCase):
    def test_every_term_the_cue_declares_is_registered(self) -> None:
        """The completeness a downstream ImportError check depends on."""
        declared: set[str] = set()
        for path in sorted(CONSTRAINTS_DIR.rglob("*.cue")):
            text = strip_cue_comments(path.read_text(encoding="utf-8"))
            declared.update(COMPACT_IRI.findall(text))
        missing = sorted(t for t in declared if f"rkaf:{t}" not in terms.TERMS)
        self.assertEqual(missing, [])

    def test_every_rkaf_enum_member_is_registered(self) -> None:
        unregistered = sorted(
            value
            for values in enums.ENUMS.values()
            for value in values
            if value.startswith("rkaf:") and value not in terms.TERMS
        )
        self.assertEqual(unregistered, [])

    def test_each_term_is_an_attribute_carrying_its_compact_iri(self) -> None:
        for local_name in scan_terms():
            term = getattr(terms, attribute_name(local_name))
            self.assertEqual(term, f"rkaf:{local_name}")
            self.assertEqual(term.local, local_name)
            self.assertEqual(term.iri, RKAF_NAMESPACE + local_name)

    def test_the_registry_and_the_attributes_are_the_same_set(self) -> None:
        self.assertEqual(len(terms.TERMS), len(terms._TERM_NAMES))
        self.assertEqual(
            terms.TERMS,
            frozenset(f"rkaf:{name}" for name in scan_terms()),
        )

    def test_a_term_is_a_string_everywhere_it_has_to_be(self) -> None:
        payload = {terms.usageEligibility: terms.officialUse}
        self.assertEqual(
            json.loads(json.dumps(payload)),
            {"rkaf:usageEligibility": "rkaf:officialUse"},
        )

    def test_retired_terms_are_refused(self) -> None:
        for retired in RETIRED_TERMS:
            with self.assertRaises(AttributeError):
                getattr(terms, retired)

    def test_names_invented_to_be_wrong_are_refused(self) -> None:
        for invented in NON_TERMS:
            with self.assertRaises(AttributeError):
                getattr(terms, invented)

    def test_the_refusal_names_the_term_it_refused(self) -> None:
        with self.assertRaises(AttributeError) as raised:
            terms.definitelyNotAnRkafTerm
        self.assertIn("rkaf:definitelyNotAnRkafTerm", str(raised.exception))

    def test_kebab_case_members_are_reachable_under_underscores(self) -> None:
        self.assertEqual(terms.us_cfr, "rkaf:us-cfr")
        self.assertIn(terms.us_cfr, enums.ENUMS["USRegulatoryIdentifierScheme"])

    def test_the_namespace_is_the_one_the_context_declares(self) -> None:
        context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        self.assertEqual(context["@context"]["rkaf"], RKAF_NAMESPACE)


class ResourceTests(unittest.TestCase):
    def test_the_version_is_the_repository_version(self) -> None:
        self.assertEqual(VERSION, (ROOT / "VERSION").read_text(encoding="utf-8").strip())

    def test_compiled_schemas_and_shacl_resolve_by_family(self) -> None:
        self.assertIn("artifact", resources.json_schema_names())
        self.assertIn("relation-finding", resources.json_schema_names("analysis"))
        self.assertIn(
            "rulemaking", resources.json_schema_names("profiles/us-rulemaking")
        )
        self.assertEqual(
            resources.json_schema("artifact")["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertIn("sh:NodeShape", resources.shacl("artifact"))
        self.assertIn("artifact", resources.shacl_names())

    def test_platform_artifact_spec_and_closed_schema_resolve(self) -> None:
        self.assertIn("# Rulespec platform artifacts 1.0", resources.platform_artifact_spec())
        schema = resources.json_schema("platform-artifact", family="platform")
        definition = schema["$defs"]["PlatformSourceCatalogArtifact"]
        self.assertIs(definition["additionalProperties"], False)
        self.assertEqual(definition["properties"]["inputs"]["type"], "array")

    def test_the_hand_authored_shape_suite_resolves(self) -> None:
        self.assertIn("rkaf-shapes-core", resources.shape_names())
        self.assertIn("sh:NodeShape", resources.shapes("rkaf-shapes-core"))

    def test_the_context_resolves_and_declares_the_rkaf_prefix(self) -> None:
        self.assertEqual(resources.context()["@context"]["rkaf"], RKAF_NAMESPACE)

    def test_a_missing_resource_says_which_one(self) -> None:
        with self.assertRaises(FileNotFoundError) as raised:
            resources.json_schema("no-such-primitive")
        self.assertIn("no-such-primitive", str(raised.exception))

    def test_a_path_that_walks_out_of_the_data_is_refused(self) -> None:
        for escape in ("../VERSION", "/etc/passwd"):
            with self.assertRaises(ValueError):
                resources.read_text(escape)


if __name__ == "__main__":
    unittest.main()
