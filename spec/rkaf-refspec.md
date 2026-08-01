# Rulespec RefSpec Application Profile — v0.1

**Status:** Pre-release, normative profile.
**Companion specifications:** `spec/rkaf-core.md`,
`spec/rkaf-concept-registry.md`, and the RefSpec Rulespec Application Profile.

## 1. Purpose and ownership

This profile defines the portable Rulespec form of an open vocabulary label
accepted by the Regulatory Evidence Framework (REF). It does not define REF
candidate generation, review workflow, output profiles, deployment, or
evaluation.

Rulespec owns the `rkaf:openLabel` predicate and the structural and semantic
requirements on the resulting `rkaf:ValueAssertion`. Rulespec publishes this
profile with the independently released Extrapolator, not with Rulespec Core.
RefSpec owns:

- the facet IRIs and their definitions;
- the complete facet, role, release, mapping, and open-label permission tuples;
- candidate and accepted-output authorization;
- default-language configuration and materialization;
- operational provenance, evaluation, and deployment decisions.

An assertion that satisfies this Rulespec profile is portable and
well-formed. It is not thereby selected, approved, or authorized for use.
RefSpec permission tuples select which outputs may enter an accepted view.
Rulespec `rkaf:Attestation`, `rkaf:LocalAdoption`, and
`rkaf:usageEligibility` carry review and use authorization.

## 2. Open-label assertion

An open label is a grounded literal result for a declared facet and assignment
role when no controlled concept is selected. It MUST be represented as one
`rkaf:ValueAssertion` with:

- `rkaf:assertsSubject` naming the `rkaf:Artifact` or
  `rkaf:SourceFragment` being described;
- `rkaf:assertsPredicate` equal to `rkaf:openLabel`;
- `rkaf:assertionPolarity` equal to `rkaf:affirmed`;
- `rkaf:assertsValue` using the language-tagged branch defined by
  `spec/rkaf-core.md` §2.2;
- exactly one `rkaf:openLabelFacet`, whose value is the absolute IRI of the
  question the label answers; and
- exactly one `rkaf:openLabelRole`, whose value is one of
  `rkaf:assignmentPrimary`, `rkaf:assignmentSubstantive`,
  `rkaf:assignmentMention`, or `rkaf:assignmentContextual`.

`rkaf:openLabelFacet` identifies a facet; it does not claim concept-scheme
membership. An open-label assertion MUST NOT also be typed
`rkaf:LocalConcept` or `rkaf:RegisteredConcept`, and it MUST NOT use
`skos:inScheme` to make the value appear controlled. Promotion to a governed
concept creates a separate concept, release membership, and lifecycle record;
it does not mutate the open-label assertion.

The facet and role are independent axes. A producer MUST NOT infer a role from
the facet, infer a facet from the wording, or combine the facet from one
RefSpec permission row with the role from another.

## 3. Language and script

The final `rkaf:assertsValue` MUST contain exactly one `@value` string and one
well-formed BCP 47 `@language` tag. It MUST NOT use the typed-literal branch,
an untagged string, or `@none`. Script belongs in the language tag, for example
`zh-Hant`; this profile defines no parallel script property.

RefSpec may require a candidate language or may declare a default language for
a specific output-profile permission. When a default applies, the producer
MUST materialize that default into the final `@language` member before
publishing the Rulespec assertion. A downstream consumer must therefore never
need RefSpec configuration to recover the accepted literal's language.

The tag `und` is permitted only when the language is genuinely unknown after
the applicable RefSpec language policy runs. It is not a substitute for an
omitted required language or for a configured default that the producer
failed to materialize.

## 4. Provenance and evidence

An open-label assertion inherits every durable `rkaf:ValueAssertion`
requirement, including `rkaf:assertionOrigin`, `rkaf:epistemicBasis`, and the
conditional AI-lineage rules. In addition, it MUST carry exactly one
`rkaf:hasExtractionProvenance` reference to the
`rkaf:ExtractionActivity` that produced or recorded the label and exactly one
`rkaf:assertedAt` time.

At least one fragment-backed `rkaf:EvidenceBinding` MUST target the assertion.
That binding MUST carry one or more `rkaf:bindsSourceFragment` values plus the
required evidence role and evidentiary function. At least one such binding
MUST use `rkaf:supports`. A binding containing only
`rkaf:noEvidenceReason` does not satisfy this profile: an accepted open label
is grounded source output, not an axiom, consensus statement, or untested
hypothesis.

Review, acceptance, and deployment state MUST NOT be copied onto the
`rkaf:ValueAssertion`. RefSpec links the assertion identifier from its own
immutable decision and configuration records.

## 5. Default-language example

Given a RefSpec output permission whose declared default language is `es`, the
accepted Rulespec result materializes that language:

```json
{
  "@id": "urn:example:assertion:open-label-1",
  "@type": "rkaf:ValueAssertion",
  "rkaf:assertsSubject": "urn:example:artifact:1",
  "rkaf:assertsPredicate": "rkaf:openLabel",
  "rkaf:assertionPolarity": "rkaf:affirmed",
  "rkaf:assertsValue": {
    "@value": "calidad del aire",
    "@language": "es"
  },
  "rkaf:openLabelFacet": "urn:ref:facet:general-subject",
  "rkaf:openLabelRole": "rkaf:assignmentSubstantive",
  "rkaf:assertionOrigin": "rkaf:aiSuggested",
  "rkaf:epistemicBasis": "rkaf:sourceExplicit",
  "rkaf:hasExtractionProvenance": "urn:example:activity:1",
  "rkaf:hasAILineage": "urn:example:ai-lineage:1",
  "rkaf:assertedAt": "2026-07-29T16:00:00Z",
  "rkaf:usageEligibility": "rkaf:reviewQueueOnly"
}
```

The required fragment-backed `rkaf:EvidenceBinding` is a separate graph node,
as required by the universal inverse evidence path.

## 6. Conformance boundary

The executable profile is downstream of the Rulespec kernel: it may compose
`rkaf:ValueAssertion`, but the kernel MUST NOT depend on RefSpec. Generated
portable targets and graph-wide validation MUST agree on:

- the fixed `rkaf:openLabel` predicate and affirmed polarity;
- the language-tagged-only value branch;
- required absolute-IRI facet and closed assignment-role value;
- required extraction provenance and assertion time; and
- the fragment-backed supporting-evidence rule.

The generated `rkaf-core` Rust crate MUST NOT contain or re-export the profile.
An Extrapolator release may pin the portable profile schema alongside an exact
RefSpec `VocabularyRelease`; that operation does not transfer vocabulary
authority to Rulespec Core.

RefSpec validators separately enforce that the exact facet, role, open-label
mode, configuration, and accepted-output permission all match one complete
RefSpec row. Rulespec validators MUST NOT attempt to reconstruct or duplicate
those operational tuples.
