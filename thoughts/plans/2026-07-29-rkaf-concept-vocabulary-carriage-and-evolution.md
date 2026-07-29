<!-- markdownlint-disable MD013 -->

# Rulespec concept vocabulary carriage and evolution plan

> **Status:** Approved upstream prerequisite
>
> **Date:** 2026-07-29
>
> **Master plan:** [RefSpec and Rulespec vocabulary gap closure plan](https://github.com/Formspec-Labs/RefSpec/blob/main/plans/vocabulary-gap-closure-plan.md)
>
> **Target:** The next unpublished Rulespec prerelease after `0.2.0-pre.8`

## Goal

Give Rulespec-authored concept schemes and concepts complete portable SKOS
carriage, restore precise concept-evolution semantics, and provide the
language-tagged open-label assertion required by RefSpec.

This plan implements only reusable semantic meaning and its validation.
RefSpec owns imports, indexes, facet compatibility, candidate and output
authorization, evaluation, and deployment.

## 1. Decisions

### 1.1 Use SKOS Core, not SKOS-XL

Use native JSON-LD language maps over RDF 1.1 SKOS Core literals:

- `skos:prefLabel` maps each BCP 47 language key to one string;
- alternate and hidden labels, definitions, examples, and SKOS notes map each
  language key to one-or-many strings;
- untagged text and the JSON-LD `@none` key are rejected;
- `und` is used only when the language is genuinely unknown;
- BCP 47 carries language and script, including tags such as `zh-Hant`; and
- `skos:notation` contains one-or-more
  `{"@value": "...", "@type": "<absolute datatype IRI>"}` objects.

Factor the BCP 47 language-tag validation already used by
`rkaf:ValueAssertion` into one CUE definition. Do not maintain two regexes.

Existing untagged authored text fails migration fixtures. Rulespec is
pre-release; the generated Rust and TypeScript interfaces may make this
breaking correction without a compatibility shim.

### 1.2 Apply SKOS integrity rules

For each concept:

- require at least one language-tagged `skos:prefLabel`;
- allow exactly one preferred-label string per language;
- prohibit the same lexical value and language from appearing in more than one
  of `skos:prefLabel`, `skos:altLabel`, and `skos:hiddenLabel`;
- allow multiple alternate and hidden labels per language;
- allow zero or more definitions and notes, with language retained; and
- allow zero or more `skos:broader`, `skos:narrower`, and `skos:related`
  absolute IRIs.

Apply the applicable label rules to `rkaf:ConceptScheme`. Do not require an
external `skos:ConceptScheme` to conform to Rulespec's authored-concept carrier.

### 1.3 Keep hierarchy and mapping disjoint

- In-scheme structure uses `skos:broader`, `skos:narrower`, and
  `skos:related`.
- Cross-scheme mapping uses only the five concrete SKOS mapping predicates
  already allowed by `rkaf:ConceptMapping`.
- Label equality creates neither hierarchy nor mapping.
- A mapping assertion never authorizes concept assignment, inference, or
  publication.

### 1.4 Restore semantic concept evolution without consumer workflow

Keep one `rkaf:LifecycleEvent` class and constrain concept operations when
`rkaf:lifecycleEventKind` is `rkaf:conceptLifecycle`. Reuse the useful
predecessor/successor semantics from the archived v0.1
`ConceptLifecyclePacket`, but leave affected work products, migration queues,
cache handling, and consumer cascade behavior outside this portable record.

The operation enum is:

- `rkaf:deprecation`;
- `rkaf:withdrawal`;
- `rkaf:replacement`;
- `rkaf:split`;
- `rkaf:merge`;
- `rkaf:promotion`; and
- `rkaf:demotion`.

The record carries:

- `rkaf:conceptLifecycleOperation`;
- `rkaf:predecessorConcepts`;
- `rkaf:successorConcepts`;
- `rkaf:predecessorConceptRelease`;
- `rkaf:successorConceptRelease`;
- inherited `rkaf:effectiveDate`, `rkaf:emittedBy`, and `rkaf:appliesTo`;
- optional `prov:wasDerivedFrom`; and
- optional existing warrant, attestation, and authority references where the
  assertion envelope already defines them.

Cardinality rules are:

| Operation | Predecessors | Successors |
| --- | --- | --- |
| Deprecation or withdrawal | exactly one | zero |
| Replacement | exactly one | exactly one |
| Split | exactly one | two or more |
| Merge | two or more | exactly one |
| Promotion | exactly one local concept | exactly one registered concept |
| Demotion | exactly one registered concept | exactly one local concept |

Each named concept must appear in the corresponding exact,
complete-membership release. A predecessor and successor release pair must
name distinct release IRIs. Each release's semantic digest proves its manifest
but cannot make one release identity serve as both states. The event does not
mutate either release.

Remove standalone `rkaf:promotion` and `rkaf:demotion` lifecycle-event kinds
and reject them through migration fixtures.

### 1.5 Use one portable open-label predicate

Register `rkaf:openLabel` as a generic predicate whose asserted object is a
language-tagged string in an affirmed `rkaf:ValueAssertion`. The profile also
registers required `rkaf:openLabelFacet` and `rkaf:openLabelRole`.

The RefSpec profile must:

- bind the assertion subject to the artifact or fragment being enriched;
- carry the facet as an absolute IRI and the role as an existing
  concept-assignment-role predicate;
- require a BCP 47 language tag in the final value; when RefSpec declares a
  default language, materialize it into that value before publication;
- preserve evidence, provenance, assertion origin, epistemic basis, and
  provisional usage limits; and
- keep attestation and local adoption separate from pipeline acceptance.

Do not create `rkaf:OpenLabel` or turn an open label into a concept
automatically.

### 1.6 Close existing concept-record parity gaps

Require `rkaf:registeredAt` on every `rkaf:RegisteredConcept`.

Complete `rkaf:ConceptResolutionResult` with:

- required `rkaf:resolutionMethod`, using the existing closed method values;
- required `rkaf:cacheStatus`, closed over `rkaf:fresh`, `rkaf:stale`, and
  `rkaf:notCached`;
- required `rkaf:usageCeiling`;
- optional `rkaf:mappingAssertion`, required whenever the selected method uses
  a mapping; and
- the existing input concept, resolution status, resolved concept, resolution
  time, and resolver identity fields.

Registry and actor IRIs remain externally described. Do not revive the v0.1
`ConceptRegistry` or `ConceptMintingAuthority` object models. Rulespec
authorities and attestations carry governance.

## 2. Implementation batches

### Batch A — Normative text and vocabulary decisions

Update the core and concept-registry specifications before changing CUE:

1. define the SKOS literal carrier and label integrity rules;
2. define polyhierarchy and the hierarchy/mapping boundary;
3. define concept-operation constraints on `rkaf:LifecycleEvent`;
4. define `rkaf:openLabel`, its profile fields, and its
   `rkaf:ValueAssertion` use;
5. close `RegisteredConcept` and `ConceptResolutionResult` parity; and
6. update the vocabulary registry and composition text.

Record any newly discovered ambiguity in this plan or a focused ADR before
changing constraints.

**Gate A:** Every future constraint cites settled normative text.

### Batch B — Complete SKOS carriage

1. Factor reusable absolute-IRI, BCP 47, language-tagged literal, and notation
   definitions in CUE.
2. Update `ConceptScheme`, `RegisteredConcept`, and `LocalConcept`.
3. Update the JSON-LD context for set-valued labels, notes, notation, and
   hierarchy.
4. Regenerate JSON Schema, Rust, TypeScript, SHACL, and OpenAPI targets.
5. Update every affected fixture and generated round-trip test.
6. Add semantic checks for one preferred label per language and label-property
   disjointness when a generated structural target cannot enforce them alone.

**Gate B:** The generated targets agree on valid and invalid multilingual
concepts, and no target silently truncates a list to one value.

### Batch C — Concept evolution

1. Add the lifecycle operation enum and conditional
   `rkaf:LifecycleEvent` constraints.
2. Add the new terms to the context and vocabulary registry.
3. Generate all target types and shapes.
4. Add membership-aware conformance validation against exact
   `ReferenceResourceRelease` records.
5. Keep consumer migration decisions and cascade effects in the L4 consumer
   layer; do not place them in the semantic event.

**Gate C:** Every operation passes its positive fixture and rejects wrong
cardinality, missing release pins, and non-member concept endpoints.

### Batch D — RefSpec open-label profile

1. Register `rkaf:openLabel`, `rkaf:openLabelFacet`, and
   `rkaf:openLabelRole`.
2. Add the RefSpec profile constraint over `rkaf:ValueAssertion`.
3. Require the final value to carry language; verify that a declared default
   language is materialized before Rulespec validation.
4. Add profile fixtures and ensure a typed literal cannot satisfy an open-label
   assertion.

**Gate D:** An accepted open label can round-trip with language and script,
but cannot masquerade as a registered concept or accepted concept assignment.

### Batch E — Conformance and release evidence

1. Run the discovery-based validation gates after each batch.
2. Run synthetic defect checks for every new conditional.
3. Run the complete `make test` suite.
4. Publish a batch report with initial failures, classifications, fixes, final
   results, and generated-artifact digests.
5. Update `VERSION`, README version text, changelog, manifests, and exact
   release digests together only after Batches A through D pass.

**Gate E:** A clean checkout reproduces all generated targets and passes the
same full suite.

## 3. Required fixtures

### Positive

- English and Spanish preferred labels on one concept.
- A `zh-Hant` preferred label proving script carriage.
- Two alternate labels in one language.
- Hidden labels, definitions, all five note types, and notation.
- One concept with two broader parents.
- Two concepts in different schemes with the same preferred label and no
  mapping.
- Deprecation, withdrawal, one-to-one replacement, one-to-many split,
  many-to-one merge, local-to-registered promotion, and
  registered-to-local demotion.
- An open-label `ValueAssertion` with a BCP 47 language tag.
- An open-label assertion using a profile-pinned default language.

### Negative

- Two preferred labels with the same language.
- The same label and language in preferred and alternate labels.
- Invalid BCP 47 and non-absolute hierarchy IRIs.
- Cross-scheme `skos:broader`.
- A split with one successor.
- A merge with one predecessor.
- A replacement without successor release membership.
- A promotion whose predecessor is not local or successor is not registered.
- A typed `ValueAssertion` using `rkaf:openLabel`.
- An untagged open label without an explicit default-language policy.

### Round-trip and parity

- JSON-LD expansion and compaction retain every literal, language, datatype,
  and hierarchy edge.
- Rust and TypeScript preserve all list members and literal variants.
- JSON Schema, SHACL, CUE, and the custom semantic checks return the same
  verdict for every fixture.
- Vocabulary and L0 audits recognize the added properties without treating
  literal labels as concept identifiers.

## 4. Files and generated surfaces

Implementation will touch the smallest coherent set in these areas:

- normative concept-registry, core, conformance, and vocabulary specifications;
- `constraints/core/` concept, lifecycle, and value-assertion sources;
- the RefSpec profile constraint and its fixtures;
- JSON-LD context and every generated target;
- vocabulary, parity, negative-fixture, semantic-carrier, and conformance
  audits; and
- version, changelog, and release evidence after all gates pass.

Do not hand-edit a generated file without changing its CUE source and
regenerating it.

## 5. Commit and delivery boundaries

Keep the rollback story clear:

1. this companion plan;
2. normative SKOS carriage text and implementation;
3. concept-evolution text and implementation;
4. `rkaf:openLabel` and the RefSpec profile;
5. conformance report and release metadata.

The current Rulespec branch is ahead of its remote. Local commits do not
publish these changes. Pushing, tagging, publishing packages, or updating
RefSpec's pinned Rulespec revision requires separate authorization.

## 6. Definition of done

The Rulespec prerequisite is complete when:

1. project-authored schemes and concepts preserve multilingual labels,
   definitions, notes, notation, and polyhierarchy;
2. label integrity and hierarchy/mapping boundaries are machine-tested;
3. concept deprecation, withdrawal, replacement, split, merge, promotion, and
   demotion identify exact predecessor and successor releases;
4. a RefSpec open label has one portable predicate and language rule;
5. every source and generated target agrees;
6. the full Rulespec suite passes from a clean checkout; and
7. RefSpec can pin the exact revision, constraint digest, and profiles without
   a local substitute.
