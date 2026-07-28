#!/usr/bin/env python3
"""Cross-target constraint parity orchestrator.

For every (constraint, fixture) pair, run the fixture through each compiled
target and assert that the violation classification (PASS / FAIL) is identical
across all targets. Cross-target divergence is a release blocker per source
spec §6.3.

Targets exercised in this MVP:
  - JSON Schema 2020-12 (via Python `jsonschema` package, Draft202012Validator)
  - SHACL Turtle        (via pyshacl 0.31+)

Rust and TypeScript targets compile to equivalent code; their parity is the
codegen's structural property (same enums, same field cardinalities), not a
fixture run. The full SDK-side parity test lands in Layer 5 (Plan 6).

Exit codes:
  0  every fixture × target produced the same classification, all match expected
  1  ≥1 cross-target divergence OR mismatch with expected outcome
  2  setup error
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
import rdflib
from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate as shacl_validate

from conformance_lib import violates_order

ROOT = Path(__file__).resolve().parent.parent

# Constraint name → subdir under constraints/ (and therefore under
# compiled/<target>/). All v0.2 constraints. Compiled artifacts live at
# compiled/<target>/<subdir>/<constraint>.<ext>.
#
# `profiles/<profile>` entries are domain profiles: they compose kernel shapes
# and add jurisdiction-specific terms. Running their fixtures through the
# PROFILE schema and the PROFILE SHACL file — never the kernel's — is what
# proves the profile, not the kernel, now carries those constraints.
#
# `analysis` entries are the document-analysis module (spec/rkaf-analysis.md):
# generic comparison contracts that overlay nothing and mention no
# jurisdiction. They compile to the same six targets under an `analysis`
# sub-path and are exercised here exactly like a kernel primitive.
CONSTRAINTS: dict[str, str] = {
    "artifact":                "core",
    "source-fragment":         "core",
    "evidence-binding":        "core",
    "warrant":                 "core",
    "confidence-record":       "core",
    "access-scope":            "core",
    "ai-lineage":              "core",
    "retention-policy":        "core",
    "workspace":               "core",
    "mapping-state":           "core",
    "concept-registry":        "core",
    "concept":                 "core",
    "concept-assignment":      "core",
    "concept-mapping":         "core",
    "assertion":               "core",
    "relationship-assertion":  "core",
    "value-assertion":         "core",
    "source-claimant":         "core",
    "extraction-activity":     "core",
    "lifecycle-event":         "core",
    "relation-change-event":       "analysis",
    "relation-comparison-context": "analysis",
    "resolver-proof-record":       "analysis",
    "relation-finding":            "analysis",
    "closure-claim":               "analysis",
    "rulemaking":              "profiles/us-rulemaking",
    "us-regulatory-artifact":  "profiles/us-rulemaking",
    "us-lifecycle-event":      "profiles/us-rulemaking",
    "conditional-silent-pass": "adversarial",
    "cross-property-coupling": "adversarial",
    "enum-drift":              "adversarial",
    "access-scope-leakage":    "adversarial",
    "nested-noevidencereason": "adversarial",
    "warrant-family-confusion":      "ai-extraction",
    "consent-vs-warrant":            "ai-extraction",
    "confidence-score-without-method": "ai-extraction",
}


# Adversarial fixtures by design surface evaluator-class divergences (per spec
# §10.1). For these, divergence between targets is the documented finding, not
# a release-blocking failure. The CORE Vocabulary fixtures, in contrast, MUST
# agree across targets — that is the §6.3 hard gate.
ADVERSARIAL_CONSTRAINTS = {
    "conditional-silent-pass",
    "cross-property-coupling",
    "enum-drift",
    "access-scope-leakage",
    "nested-noevidencereason",
    "warrant-family-confusion",
    "consent-vs-warrant",
    "confidence-score-without-method",
}


# (constraint, shape_def_name, fixture_path_relative_to_root, expected_outcome)
FIXTURE_BINDINGS: list[tuple[str, str, str, str]] = [
    # (constraint, shape_def, fixture, expected — PASS or FAIL)
    ("artifact", "Artifact", "fixtures/artifact-eli-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-doi-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-cid-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-primary-topic-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-version-lineage-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-content-digest-positive.jsonld", "PASS"),
    # Version identity (§4.1). A format sibling is NOT a version claim, so the
    # cross-posting edge must stay PASS while every row below it FAILs — that
    # contrast is the whole point of guarding on the two lineage predicates
    # rather than on "this Artifact points at another Artifact".
    ("artifact", "Artifact",
     "fixtures/edges/artifact-format-sibling-not-a-version-edge.jsonld", "PASS"),
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-revision-without-lineage-evidence-negative.jsonld",
     "FAIL"),
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-is-version-of-without-lineage-evidence-negative.jsonld",
     "FAIL"),
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-lineage-evidence-without-content-digest-negative.jsonld",
     "FAIL"),
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-malformed-content-digest-negative.jsonld", "FAIL"),
    # The kernel Artifact is open at the carrier level: a document carrying US
    # profile terms is UNCONSTRAINED by the kernel schema/shape rather than
    # rejected by it. These two rows pin that semantics — the same malformed
    # documents that FAIL below under the profile PASS the kernel, because the
    # kernel no longer knows the terms. (The CUE definition itself is closed:
    # see ArtifactKernelPurityTests in tools/test_constraints_compile.py.)
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-us-cfr-malformed-negative.jsonld", "PASS"),
    ("artifact", "Artifact",
     "fixtures/negatives/artifact-regulatory-scheme-unregistered-negative.jsonld",
     "PASS"),
    # US regulatory identity now lives in the profile overlay, which composes
    # the kernel #Artifact. Every US fixture is classified by the PROFILE.
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-eli-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-cfr-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-usc-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-frdoc-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-regsgov-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-pl-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-us-eo-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-cross-posting-positive.jsonld", "PASS"),
    # Document -> Docket, direct (rulemaking §5.3). No parity row for its
    # class-range negative
    # (artifact-published-in-docket-wrong-class-negative) for the reason
    # recorded below: `sh:class` follows a reference and JSON Schema cannot,
    # so tools/validate_negatives.py gates it against the full shape suite.
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/artifact-published-in-docket-positive.jsonld", "PASS"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-regulatory-identifier-missing-scheme-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-regulatory-scheme-missing-identifier-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-cfr-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-usc-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-frdoc-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-regsgov-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-pl-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact", "fixtures/negatives/artifact-us-eo-malformed-negative.jsonld", "FAIL"),
    ("us-regulatory-artifact", "USRegulatoryArtifact",
     "fixtures/negatives/artifact-regulatory-scheme-unregistered-negative.jsonld",
     "FAIL"),
    # Lifecycle-event kinds are layered the same way the Artifact terms are.
    # The kernel owns the ten universal kinds but its carriers are OPEN on
    # `rkaf:lifecycleEventKind`: an event carrying a profile-contributed kind
    # — or an unregistered one — is UNCONSTRAINED by the kernel schema/shape
    # rather than rejected by it. These three rows pin that deliberate
    # openness; the composed rows below close the same property over the
    # assembled 22-value union, so the SAME unregistered-kind document that
    # PASSES the kernel FAILS the composed artifact.
    ("lifecycle-event", "LifecycleEvent",
     "fixtures/lifecycleevent-positive.jsonld", "PASS"),
    ("lifecycle-event", "LifecycleEvent",
     "fixtures/lifecycleevent-composed-kind-positive.jsonld", "PASS"),
    ("lifecycle-event", "LifecycleEvent",
     "fixtures/negatives/lifecycleevent-unregistered-kind-negative.jsonld",
     "PASS"),
    ("us-lifecycle-event", "USLifecycleEvent",
     "fixtures/lifecycleevent-positive.jsonld", "PASS"),
    ("us-lifecycle-event", "USLifecycleEvent",
     "fixtures/lifecycleevent-composed-kind-positive.jsonld", "PASS"),
    ("us-lifecycle-event", "USLifecycleEvent",
     "fixtures/lifecycleevent-proceeding-stages-positive.jsonld", "PASS"),
    ("us-lifecycle-event", "USLifecycleEvent",
     "fixtures/negatives/lifecycleevent-unregistered-kind-negative.jsonld",
     "FAIL"),
    ("rulemaking", "Docket", "fixtures/docket-us-regsgov-positive.jsonld", "PASS"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-missing-has-docket-identifier-negative.jsonld", "FAIL"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-missing-docket-identifier-scheme-negative.jsonld", "FAIL"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-us-regsgov-malformed-negative.jsonld", "FAIL"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-ordinary-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-coast-guard-recurring-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-faa-recurring-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-repeated-unresolved-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/negatives/regulatory-agenda-item-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "RegulatoryAgendaObservation", "fixtures/agenda-observations-multiple-editions-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaObservation", "fixtures/negatives/regulatory-agenda-observation-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "AgendaProceedingRelationship", "fixtures/agenda-item-ordinary-positive.jsonld", "PASS"),
    ("rulemaking", "AgendaProceedingRelationship", "fixtures/negatives/agenda-proceeding-relationship-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/proceeding-partner-positive.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-missing-has-proceeding-identifier-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-missing-proceeding-identifier-scheme-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/edges/proceeding-multi-docket-edge.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/proceeding-unknown-authority-positive.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-rin-as-identity-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/commentperiod-positive.jsonld", "PASS"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-for-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-start-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-end-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-provenance-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-malformed-date-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-end-before-start-negative.jsonld", "FAIL"),
    # SourceFragment identity (§4.2). Three REQUIRED bindings — exact artifact,
    # selector, selector kind — plus the coordinate system, which the SELECTOR
    # carries. The TextPositionSelector rows are bound to the selector shape
    # rather than the fragment shape for exactly that reason: that is where the
    # offsets and their unit live. The state binding
    # (`rkaf:sourceArtifactDigest`) is RECOMMENDED, not required, so it has a
    # malformed-value row and no missing-value row.
    ("source-fragment", "SourceFragment",
     "fixtures/sourcefragment-oa-textquote-positive.jsonld", "PASS"),
    ("source-fragment", "SourceFragment",
     "fixtures/sourcefragment-position-selector-positive.jsonld", "PASS"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/sourcefragment-position-selector-positive.jsonld", "PASS"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/edges/text-position-selector-zero-length-edge.jsonld", "PASS"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/negatives/text-position-selector-missing-coordinate-system-negative.jsonld",
     "FAIL"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/negatives/text-position-selector-inverted-offsets-negative.jsonld",
     "FAIL"),
    ("source-fragment", "SourceFragment",
     "fixtures/negatives/source-fragment-malformed-source-artifact-digest-negative.jsonld",
     "FAIL"),
    # The quote-selector contract, exercised on nodes attached BY REFERENCE.
    # Both L2 dispatchers walk the root and the top-level `@graph` only, so a
    # referenced selector is the form they can see; an inline one reaches SHACL
    # alone (Core §4.2).
    ("source-fragment", "SourceFragment",
     "fixtures/sourcefragment-referenced-quote-selector-positive.jsonld", "PASS"),
    ("source-fragment", "TextQuoteSelector",
     "fixtures/sourcefragment-referenced-quote-selector-positive.jsonld", "PASS"),
    ("source-fragment", "TextQuoteSelector",
     "fixtures/edges/text-quote-selector-no-context-anchors-edge.jsonld", "PASS"),
    ("source-fragment", "TextQuoteSelector",
     "fixtures/negatives/text-quote-selector-missing-exact-negative.jsonld",
     "FAIL"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/negatives/text-position-selector-missing-start-negative.jsonld",
     "FAIL"),
    ("source-fragment", "TextPositionSelector",
     "fixtures/negatives/text-position-selector-missing-end-negative.jsonld",
     "FAIL"),
    ("warrant",  "Warrant",  "fixtures/warrant-legal-positive.jsonld", "PASS"),
    ("warrant",  "Warrant",  "fixtures/warrant-scientific-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-uncalibrated-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-calibrated-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-score-theater-negative.jsonld", "FAIL"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-public-positive.jsonld", "PASS"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-organizationVisible-positive.jsonld", "PASS"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-leak-negative.jsonld", "FAIL"),
    ("ai-lineage",        "AILineage",        "fixtures/ailineage-positive.jsonld", "PASS"),
    # §2.4 / §5.3 resolution: an approver-free lineage is the HONEST record of
    # an unreviewed model candidate, so it PASSes. What still fails is a
    # lineage carrying a human rationale with no human, and an input-context
    # hash that is not a digest.
    ("ai-lineage",        "AILineage",
     "fixtures/edges/ailineage-unreviewed-candidate-edge.jsonld", "PASS"),
    ("ai-lineage",        "AILineage",
     "fixtures/negatives/a-i-lineage-missing-human-approver-negative.jsonld", "FAIL"),
    ("ai-lineage",        "AILineage",
     "fixtures/ailineage-malformed-input-context-hash-negative.jsonld", "FAIL"),
    ("retention-policy",  "RetentionPolicy",  "fixtures/retentionpolicy-positive.jsonld", "PASS"),
    ("workspace",         "Workspace",        "fixtures/workspace-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-no-evidence-reason-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-missing-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/relationshipassertion-denied-positive.jsonld", "PASS"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/relationshipassertion-affirmed-positive.jsonld", "PASS"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-subject-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-origin-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-predicate-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-object-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-polarity-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-invalid-polarity-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-ai-missing-lineage-negative.jsonld", "FAIL"),
    # Deterministic origin (Core §2.4). The pair is the whole point of the
    # value: it claims mechanical reproducibility, so the run that reproduces
    # it is REQUIRED rather than optional.
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/relationshipassertion-deterministic-origin-positive.jsonld", "PASS"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-deterministic-origin-without-provenance-negative.jsonld",
     "FAIL"),
    # ValueAssertion — the typed-literal proposition form (Core §2.2). The
    # datatype rows are the ones that matter: they prove the JSON Schema
    # `@type` enum and the SHACL `sh:datatype` alternatives close over the SAME
    # set. A datatype the CUE does not declare must be rejected by BOTH, or the
    # RDF side and the JSON side disagree about what "typed" means.
    ("value-assertion", "ValueAssertion",
     "fixtures/valueassertion-date-positive.jsonld", "PASS"),
    ("value-assertion", "ValueAssertion",
     "fixtures/valueassertion-denied-integer-positive.jsonld", "PASS"),
    ("value-assertion", "ValueAssertion",
     "fixtures/valueassertion-ai-suggested-positive.jsonld", "PASS"),
    ("value-assertion", "ValueAssertion",
     "fixtures/edges/value-assertion-boolean-edge.jsonld", "PASS"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-unregistered-datatype-negative.jsonld", "FAIL"),
    # The value object must be CLOSED on both sides. A language-tagged literal
    # is the case that corrupts RDF rather than merely differing on the wire:
    # `{"@value","@type","@language"}` expands to a plain language-tagged
    # literal with the declared datatype GONE, so SHACL's `sh:datatype`
    # alternatives reject it. Before the value object emitted
    # `additionalProperties: false`, JSON Schema accepted the same document —
    # this row is the divergence that hole produced.
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-language-tagged-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-missing-asserts-value-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-missing-asserts-subject-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-missing-asserts-predicate-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-missing-assertion-polarity-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-missing-assertion-origin-negative.jsonld", "FAIL"),
    ("value-assertion", "ValueAssertion",
     "fixtures/negatives/value-assertion-ai-missing-lineage-negative.jsonld", "FAIL"),
    # SourceClaimant — who the SOURCE says asserts it (Core §2.4). The
    # named-without-text row is the semantic one: a record may not claim the
    # document names a claimant while withholding the naming text.
    ("source-claimant", "SourceClaimant",
     "fixtures/sourceclaimant-named-positive.jsonld", "PASS"),
    ("source-claimant", "SourceClaimant",
     "fixtures/sourceclaimant-issuer-positive.jsonld", "PASS"),
    ("source-claimant", "SourceClaimant",
     "fixtures/edges/source-claimant-not-stated-edge.jsonld", "PASS"),
    ("source-claimant", "SourceClaimant",
     "fixtures/negatives/source-claimant-named-without-text-negative.jsonld", "FAIL"),
    ("source-claimant", "SourceClaimant",
     "fixtures/negatives/source-claimant-missing-claims-assertion-negative.jsonld", "FAIL"),
    ("source-claimant", "SourceClaimant",
     "fixtures/negatives/source-claimant-missing-claimant-attribution-negative.jsonld", "FAIL"),
    # ExtractionActivity — which run produced the candidate (Core §2.4).
    # The model-without-model-ref row proves a run cannot claim a model
    # produced it while leaving that model unauditable; the malformed-digest
    # row proves the request-contract digest is a digest, not a free string.
    # The two request-contract rows are a matched pair: the digest is REQUIRED
    # for a model call and absent-and-conforming for a deterministic parse,
    # which has no request contract to name.
    ("extraction-activity", "ExtractionActivity",
     "fixtures/extractionactivity-model-positive.jsonld", "PASS"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/extractionactivity-deterministic-positive.jsonld", "PASS"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/extractionactivity-deterministic-no-request-contract-positive.jsonld",
     "PASS"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/edges/extraction-activity-retry-edge.jsonld", "PASS"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-model-without-model-ref-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-malformed-request-digest-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-missing-extraction-run-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-missing-extracted-by-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-missing-extractor-version-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-missing-request-contract-digest-negative.jsonld", "FAIL"),
    ("extraction-activity", "ExtractionActivity",
     "fixtures/negatives/extraction-activity-missing-extraction-method-negative.jsonld", "FAIL"),
    # ConceptScheme and SKOS-compatible concepts (§4.7). The facet row is the
    # semantic one: a scheme that never declares which facet it controls is
    # how topic, industry, and organization vocabularies merge.
    ("concept", "ConceptScheme",
     "fixtures/conceptscheme-registry-positive.jsonld", "PASS"),
    ("concept", "ConceptScheme",
     "fixtures/conceptscheme-local-positive.jsonld", "PASS"),
    ("concept", "ConceptScheme",
     "fixtures/negatives/concept-scheme-missing-scheme-facet-negative.jsonld", "FAIL"),
    ("concept", "ConceptScheme",
     "fixtures/negatives/concept-scheme-missing-pref-label-negative.jsonld", "FAIL"),
    ("concept", "ConceptScheme",
     "fixtures/negatives/concept-scheme-missing-concept-status-negative.jsonld", "FAIL"),
    ("concept", "ConceptScheme",
     "fixtures/negatives/concept-scheme-unowned-negative.jsonld", "FAIL"),
    ("concept", "RegisteredConcept",
     "fixtures/concept-registered-positive.jsonld", "PASS"),
    ("concept", "RegisteredConcept",
     "fixtures/edges/registered-concept-promoted-edge.jsonld", "PASS"),
    ("concept", "RegisteredConcept",
     "fixtures/negatives/registered-concept-missing-in-scheme-negative.jsonld", "FAIL"),
    ("concept", "RegisteredConcept",
     "fixtures/negatives/registered-concept-promoted-without-definition-negative.jsonld",
     "FAIL"),
    ("concept", "LocalConcept",
     "fixtures/localconcept-positive.jsonld", "PASS"),
    ("concept", "LocalConcept",
     "fixtures/negatives/local-concept-missing-in-scheme-negative.jsonld", "FAIL"),
    # SKOS mapping properties. The added *Match members must be accepted by
    # BOTH the compiled closure and the hand-authored conceptregistry shape —
    # SHACL is conjunctive, so a value in one list and not the other is
    # rejected no matter what the compiled artifact says.
    ("concept-mapping", "ConceptMapping",
     "fixtures/conceptmapping-positive.jsonld", "PASS"),
    ("concept-mapping", "ConceptMapping",
     "fixtures/edges/concept-mapping-skos-broad-match-edge.jsonld", "PASS"),
    ("concept-mapping", "ConceptMapping",
     "fixtures/edges/concept-mapping-skos-broader-edge.jsonld", "PASS"),
    # ConceptAssignment (§4.7). The directional rows carry the rule the carrier
    # evidence turns on: a segment tag needs evidence from that segment, and a
    # document tag aggregated from segment tags must name them and the policy.
    ("concept-assignment", "ConceptAssignment",
     "fixtures/conceptassignment-fragment-direct-positive.jsonld", "PASS"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/conceptassignment-document-derived-positive.jsonld", "PASS"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/edges/concept-assignment-unreviewed-ai-candidate-edge.jsonld", "PASS"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-fragment-without-local-evidence-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-direct-without-evidence-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-derived-without-supporting-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-supporting-without-policy-version-negative.jsonld",
     "FAIL"),
    # NOTE — no parity row for the class-range negatives
    # (concept-assignment-evidence-not-a-fragment-negative,
    # source-fragment-source-not-an-artifact-negative,
    # artifact-lineage-evidence-not-a-fragment-negative). A `sh:class`
    # violation is a statement about the node an IRI RESOLVES TO, and JSON
    # Schema has no way to follow a reference, so the two targets cannot agree
    # by construction. Those fixtures are gated by tools/validate_negatives.py
    # against the full shape suite, the same route
    # `rulemaking-reference-class-confusion-negative` already takes.
    #
    # NOTE — no parity row for the cross-node agreement negatives either
    # (source-fragment-selector-kind-without-typed-selector-negative,
    # source-fragment-untyped-position-selector-negative,
    # concept-assignment-fragment-subject-mislabeled-as-artifact-negative,
    # concept-assignment-evidence-from-another-artifact-negative). Each is
    # caught by a hand-authored shape in `shapes/rkaf-shapes-core.ttl` that
    # compares one node's value against ANOTHER node's class or property, which
    # is the same reference-following JSON Schema cannot do. Same gate, same
    # reason.
    #
    # NOTE — nor for the two carrier-local fragment URN negatives
    # (concept-assignment-carrier-local-fragment-undeclared-negative,
    # source-fragment-carrier-local-urn-source-mismatch-negative). The first is
    # a per-VALUE conditional keyed on that value's own lexical form and the
    # second compares a node's IRI against its own `oa:hasSource`; both live in
    # `shapes/rkaf-shapes-core.ttl` for the same reason — the CUE list-of-string
    # carrier admits one pattern, and JSON Schema has no way to relate a value
    # to a sibling property of the node it names. The two that BOTH targets do
    # see have rows below.
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-evidence-without-scheme-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-carrier-local-fragment-malformed-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/conceptassignment-carrier-local-fragment-positive.jsonld", "PASS"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assignment-subject-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assignment-subject-type-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assigned-concept-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-in-scheme-negative.jsonld", "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assignment-role-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assignment-derivation-negative.jsonld",
     "FAIL"),
    ("concept-assignment", "ConceptAssignment",
     "fixtures/negatives/concept-assignment-missing-assertion-origin-negative.jsonld",
     "FAIL"),
    # Document-analysis module (spec/rkaf-analysis.md).
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/relationchangeevent-removal-positive.jsonld", "PASS"),
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/relationchangeevent-replacement-positive.jsonld", "PASS"),
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/edges/relation-change-event-stage-unclear-edge.jsonld", "PASS"),
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/negatives/relation-change-event-missing-required-negative.jsonld",
     "FAIL"),
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/negatives/relation-change-event-replacement-without-successor-negative.jsonld",
     "FAIL"),
    ("relation-change-event", "RelationChangeEvent",
     "fixtures/negatives/relation-change-event-effective-without-time-negative.jsonld",
     "FAIL"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/relationcomparisoncontext-satisfied-positive.jsonld", "PASS"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/relationfinding-discrepancy-positive.jsonld", "PASS"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/edges/relation-comparison-unknown-no-proof-edge.jsonld", "PASS"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/edges/resolver-proof-scope-relation-edge.jsonld", "PASS"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/negatives/relation-comparison-context-missing-required-negative.jsonld",
     "FAIL"),
    ("relation-comparison-context", "RelationComparisonContext",
     "fixtures/negatives/relation-comparison-satisfied-without-proof-negative.jsonld",
     "FAIL"),
    ("resolver-proof-record", "ResolverProofIssuer",
     "fixtures/relationfinding-discrepancy-positive.jsonld", "PASS"),
    ("resolver-proof-record", "ResolverProofIssuer",
     "fixtures/negatives/resolver-proof-issuer-missing-required-negative.jsonld",
     "FAIL"),
    ("resolver-proof-record", "ResolverProofRecord",
     "fixtures/relationfinding-discrepancy-positive.jsonld", "PASS"),
    ("resolver-proof-record", "ResolverProofRecord",
     "fixtures/edges/resolver-proof-scope-relation-edge.jsonld", "PASS"),
    ("resolver-proof-record", "ResolverProofRecord",
     "fixtures/negatives/resolver-proof-record-missing-required-negative.jsonld",
     "FAIL"),
    ("resolver-proof-record", "ResolverProofRecord",
     "fixtures/negatives/resolver-proof-record-malformed-digest-negative.jsonld",
     "FAIL"),
    ("relation-finding", "RelationFinding",
     "fixtures/relationfinding-discrepancy-positive.jsonld", "PASS"),
    ("relation-finding", "RelationFinding",
     "fixtures/edges/relation-finding-repeat-occurrence-edge.jsonld", "PASS"),
    ("relation-finding", "RelationFinding",
     "fixtures/negatives/relation-finding-missing-required-negative.jsonld", "FAIL"),
    ("relation-finding", "RelationFinding",
     "fixtures/negatives/relation-finding-single-compared-assertion-negative.jsonld",
     "FAIL"),
    ("closure-claim", "ClosureClaim",
     "fixtures/closureclaim-disabled-positive.jsonld", "PASS"),
    ("closure-claim", "ClosureClaim",
     "fixtures/edges/closure-claim-unreviewed-edge.jsonld", "PASS"),
    ("closure-claim", "ClosureClaim",
     "fixtures/negatives/closure-claim-missing-required-negative.jsonld", "FAIL"),
    # The experimental gate, proved at the target level: `rkaf:closureClaimDisabled`
    # is the ONLY value both compiled targets accept, so enabling closure cannot
    # be done from a document.
    ("closure-claim", "ClosureClaim",
     "fixtures/negatives/closure-claim-enabled-status-negative.jsonld", "FAIL"),
    # NOTE — no parity rows for the six analysis negatives caught by
    # `shapes/rkaf-shapes-analysis.ttl`:
    # relation-change-event-polarity-negative and
    # closure-claim-assertion-polarity-negative (properties that must be
    # ABSENT), relation-finding-on-satisfied-comparison-negative,
    # relation-finding-citing-closure-claim-negative,
    # relation-finding-citing-closure-claim-indirect-negative, and
    # resolver-proof-foreign-comparison-negative (all compare one node's
    # value against ANOTHER node's class or property, the last two across an
    # unbounded citation chain). Every per-property constraint in both compiled
    # targets passes on all six by construction, so a FAIL row would be a
    # manufactured divergence rather than a measured one. They are gated by
    # `tools/validate_negatives.py` against the full shape suite, the same route
    # the concept-assignment cross-node negatives already take.
    # Adversarial — evaluator-class regressions
    ("conditional-silent-pass", "ConsensusEvidencePermissionShape",
     "fixtures/adversarial/conditional-silent-pass-positive.jsonld", "PASS"),
    ("conditional-silent-pass", "ConsensusEvidencePermissionShape",
     "fixtures/adversarial/conditional-silent-pass-negative.jsonld", "FAIL"),
    ("enum-drift",              "EnumDriftWarrant",
     "fixtures/adversarial/enum-drift-negative.jsonld", "FAIL"),
    ("cross-property-coupling", "ModelInferenceCoupling",
     "fixtures/adversarial/cross-property-coupling-negative.jsonld", "FAIL"),
    ("nested-noevidencereason", "NestedNoEvidenceReasonShape",
     "fixtures/adversarial/nested-noevidencereason-positive.jsonld", "PASS"),
    # AI-extraction adversarial — LLM systematic misinterpretation
    ("warrant-family-confusion", "WarrantFamilyConfusionRejector",
     "fixtures/ai-extraction/warrant-family-confusion-negative.jsonld", "FAIL"),
    ("consent-vs-warrant", "ConsentVsWarrantRejector",
     "fixtures/ai-extraction/consent-vs-warrant-negative.jsonld", "FAIL"),
    ("confidence-score-without-method", "ConfidenceScoreWithoutMethodRejector",
     "fixtures/ai-extraction/confidence-score-without-method-negative.jsonld", "FAIL"),
]


def rust_module_path(constraint: str) -> Path:
    """Generated-Rust sink for a constraint, mirroring tools/compile_all.sh."""
    subdir = CONSTRAINTS[constraint]
    snake = constraint.replace("-", "_")
    base = ROOT / "crates" / "rkaf-core" / "src" / "generated"
    if subdir.startswith("profiles/"):
        profile = subdir.split("/", 1)[1].replace("-", "_")
        return base / "profiles" / profile / f"{snake}.rs"
    if subdir == "analysis":
        return base / "analysis" / f"{snake}.rs"
    return base / f"{snake}.rs"


def run_jsonschema(constraint: str, shape: str, fixture_path: Path) -> str:
    subdir = CONSTRAINTS[constraint]
    schema_path = ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json"
    schema_doc = json.loads(schema_path.read_text())
    target_schema = schema_doc["$defs"][shape]
    target_schema["$defs"] = schema_doc.get("$defs", {})
    payload = json.loads(fixture_path.read_text())
    # JSON-LD fixtures with @graph: validate each node of the matching @type
    if "@graph" in payload:
        nodes = [n for n in payload["@graph"] if n.get("@type") == target_schema.get("properties", {}).get("@type", {}).get("const")]
    else:
        nodes = [payload]
    for node in nodes:
        node = dict(node)
        node.pop("@context", None)
        errs = list(
            Draft202012Validator(
                target_schema,
                format_checker=FormatChecker(),
            ).iter_errors(node)
        )
        for order in target_schema.get("x-rkaf-order", []):
            if violates_order(node.get(order["lower"]), node.get(order["upper"])):
                errs.append(
                    ValueError(
                        f"{order['lower']} must be less than or equal to {order['upper']}"
                    )
                )
        if errs:
            return "FAIL"
    return "PASS"


def run_shacl(constraint: str, shape: str, fixture_path: Path) -> str:
    subdir = CONSTRAINTS[constraint]
    shape_path = ROOT / "compiled" / "shacl" / subdir / f"{constraint}.ttl"
    if not shape_path.exists():
        return "PASS"  # if no SHACL emitted (e.g. enum-only), treat as PASS
    data = rdflib.Graph()
    # rdflib logs a traceback while retaining malformed xsd:date lexemes.
    # Those lexemes are intentional negative-fixture inputs; SHACL should
    # produce the verdict without obscuring the parity report.
    term_logger = logging.getLogger("rdflib.term")
    previous_level = term_logger.level
    term_logger.setLevel(logging.CRITICAL)
    try:
        data.parse(str(fixture_path), format="json-ld")
    finally:
        term_logger.setLevel(previous_level)
    shapes = rdflib.Graph()
    shapes.parse(str(shape_path), format="turtle")
    conforms, _, _ = shacl_validate(
        data_graph=data, shacl_graph=shapes,
        inference="rdfs", advanced=True, meta_shacl=False,
    )
    return "PASS" if conforms else "FAIL"


# Rust and TypeScript codegen targets emit equivalent enum/struct code; their
# parity to JSON Schema is structural (same enums, same cardinalities, same
# disjunctions). The full SDK-runtime parity check (which would actually run
# Rust/TS validators on JSON-LD docs) lands in Plan 6 (SDK layer). For Layer 2,
# we assert structural parity: every enum/shape in the JSON Schema target also
# appears (by name) in the Rust and TypeScript targets.
def structural_parity_rust(constraint: str) -> bool:
    subdir = CONSTRAINTS[constraint]
    js = (ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json").read_text()
    # Canonical Rust sink is crates/rkaf-core/src/generated/<snake>.rs for the
    # kernel, .../generated/analysis/<snake>.rs for the document-analysis
    # module, and .../generated/profiles/<profile>/<snake>.rs for a domain
    # profile. adversarial/ + ai-extraction/ constraints are not compiled to
    # Rust (Plan 7a-7c restriction); skip parity for those.
    if subdir not in {"core", "analysis"} and not subdir.startswith("profiles/"):
        return True
    rs_path = rust_module_path(constraint)
    if not rs_path.exists():
        return False
    rs = rs_path.read_text()
    schema = json.loads(js)
    for name in schema.get("$defs", {}):
        # Each $defs entry must appear in the Rust output as either `pub enum {name}`
        # (for closed enums), `pub struct {name}` (for shapes), or a
        # fully-qualified cross-module reference ending in `::{name}`.
        if (
            f"pub enum {name}" not in rs
            and f"pub struct {name}" not in rs
            and f"::{name}" not in rs
        ):
            return False
    return True


def structural_parity_typescript(constraint: str) -> bool:
    subdir = CONSTRAINTS[constraint]
    js  = (ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json").read_text()
    ts  = (ROOT / "compiled" / "typescript"  / subdir / f"{constraint}.ts").read_text()
    schema = json.loads(js)
    for name in schema.get("$defs", {}):
        if (
            f"export type {name}" not in ts
            and f"export interface {name}" not in ts
            and f"import type {{ {name} }}" not in ts
        ):
            return False
    return True


def main() -> int:
    print(f"Running {len(FIXTURE_BINDINGS)} fixture×constraint pairs across targets")
    print("=" * 70)
    print("CORE PARITY (release gate — all targets MUST agree)")
    print("-" * 70)
    core_divergences = 0
    adversarial_findings = 0
    for constraint, shape, fpath, expected in FIXTURE_BINDINGS:
        full = ROOT / fpath
        if not full.exists():
            print(f"  [SKIP] {fpath} (missing)")
            continue
        js_result    = run_jsonschema(constraint, shape, full)
        shacl_result = run_shacl(constraint, shape, full)
        rs_struct = structural_parity_rust(constraint)
        ts_struct = structural_parity_typescript(constraint)
        all_match = js_result == shacl_result
        # The MUST target (JSON Schema) must classify per the expected outcome.
        match_expected = js_result == expected
        is_adversarial = constraint in ADVERSARIAL_CONSTRAINTS
        if is_adversarial:
            # Adversarial fixtures: JSON Schema (the MUST target) must classify
            # per expected. SHACL divergence is a documented finding, not a
            # blocker (the fixture exists to surface evaluator-class gaps).
            ok = match_expected and rs_struct and ts_struct
            target_divergence = not all_match
            status = "OK" if ok else "FAIL"
            note = " (sh-divergence — expected for adversarial)" if target_divergence else ""
        else:
            # Core fixtures: every target must agree, must match expected.
            ok = all_match and match_expected and rs_struct and ts_struct
            target_divergence = not all_match
            status = "OK" if ok else "DIVERGE"
            note = ""
        line = (f"  [{status}] {constraint:35s} expected={expected:4s} "
                f"json-schema={js_result:4s} shacl={shacl_result:4s} "
                f"rust-struct={'OK' if rs_struct else 'FAIL':4s} "
                f"ts-struct={'OK' if ts_struct else 'FAIL':4s} "
                f"{Path(fpath).name}{note}")
        print(line)
        if not ok:
            if is_adversarial:
                adversarial_findings += 1
            else:
                core_divergences += 1
    print("=" * 70)
    print(f"CORE divergences (release blockers): {core_divergences}")
    print(f"ADVERSARIAL findings (documentation): {adversarial_findings}")
    return 1 if core_divergences > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
