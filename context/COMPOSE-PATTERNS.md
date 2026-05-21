# Rulespec Compose Patterns

Six common AI-governance needs that look like they want new vocabulary, with the existing-primitive composition that satisfies each. Companion to [ADR 0149](../../thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md) (stack-level).

Each pattern shows: the apparent need, the composed primitives, line-level citations, and the bright-line test for when an extension profile (not core vocabulary) is warranted.

---

## Pattern 1 — "I need a typed projection record" (property graph, vector index, summary index, retrieval index, materialized view)

**Composed primitives:** `rkaf:GeneratedWorkProduct` + `rkaf:projectsTo` + PROV-O (`prov:wasDerivedFrom`, `prov:wasGeneratedBy`, `prov:generatedAtTime`) + `rkaf:AILineage` (when AI-generated) + `rkaf:hasArtifactIdentifier` with scheme `rkaf:hash-sha256`.

**Where they live:**
- `constraints/core/generated-work-product.cue` — GWP shape: `justifiedByAssertion`, `consumerLifecycleState`, `proposedUsageEligibility`.
- `spec/rkaf-vocabulary.md:46` — `rkaf:projectsTo` predicate.
- `context/rkaf-context.jsonld:869-878` — PROV-O context imports.
- `spec/rkaf-core.md §4.1` — `rkaf:hash-sha256` artifact-identifier scheme.
- `spec/projectors/{json-schema,json-ld,openapi}.md` — Layer 4 projector contract (five-operation interface).
- `thoughts/plans/2026-05-12-rkaf-layer4-projectors-v0.2.md` — typed `Projector` Rust trait.

**Sketch:**

```jsonld
{
  "@type": "rkaf:GeneratedWorkProduct",
  "@id": "ex:projection-2026-05-20-property-graph",
  "rkaf:projectsTo": "ex:case-graph-canonical-rev-A1B2",
  "prov:wasDerivedFrom": { "@id": "ex:case-graph-canonical-rev-A1B2" },
  "prov:wasGeneratedBy": { "@id": "ex:property-graph-projector-v1.3" },
  "prov:generatedAtTime": "2026-05-20T14:30:00Z",
  "rkaf:hasArtifactIdentifier": {
    "rkaf:artifactIdentifierScheme": "rkaf:hash-sha256",
    "rkaf:artifactIdentifierValue": "sha256:<hex>"
  }
}
```

**When this is enough:** the projection is a disposable consumer artifact. The substrate records "what was derived from what, by what, when, addressable by which hash." Staleness detection is downstream: compare the recorded `wasDerivedFrom` hash against the current canonical-graph hash.

**When an extension profile is warranted:** never for core Rulespec. Consumers that need RAG-specific projection-type taxonomies extend `GeneratedWorkProduct` in their overlay namespace.

---

## Pattern 2 — "I need an AI proposal / promotion workflow" (raw extraction → review → canonical assertion)

**Composed primitives:** `rkaf:Assertion.assertionOrigin` (six-value closed enum) + `rkaf:AILineage` + `rkaf:Attestation` + `rkaf:LifecycleEvent` (`rkaf:promotion` / `rkaf:demotion` kinds) + `rkaf:EvidenceBinding`.

**Where they live:**
- `constraints/core/assertion.cue:4-9` — `#AssertionOrigin` enum: `humanAsserted | aiSuggested | aiPromoted | humanQualified | humanRevalidation | imported`.
- `constraints/core/assertion.cue:14-27` — CUE conditional enforcing `hasAILineage` on AI-touched origins.
- `constraints/core/ai-lineage.cue` — `modelId`, `modelVersion`, `promptTemplateRef`, `temperature`, `seed`, `inputContextHash`, `humanApprover`, `humanRationale`.
- `constraints/core/attestation.cue` — `decision` enum (`approved | approvedWithConditions | rejected | abstained | ...`), `rationale`, `scope`, temporal bounds.
- `constraints/core/lifecycle-event.cue:8-11` — `lifecycleEventKind` includes `rkaf:promotion` and `rkaf:demotion`.

**State map:**

| Workflow state | Rulespec representation |
|---|---|
| Raw AI extraction (pending review) | `Assertion(assertionOrigin: aiSuggested, hasAILineage: <lineage>)` |
| Under review | same Assertion + open `Attestation(decision: abstained, scope: reviewing)` (optional) |
| Approved | `LifecycleEvent(kind: rkaf:promotion, appliesTo: <assertion>)` transitioning to `aiPromoted` or `humanQualified`; `AILineage.humanApprover` + `humanRationale` set; `Attestation(decision: approved, rationale: ...)` issued |
| Rejected | `LifecycleEvent(kind: rkaf:demotion, appliesTo: <assertion>)` or hold at `aiSuggested` indefinitely; `Attestation(decision: rejected, rationale: ...)` |

**Audit retention:** rejected proposals are not deleted. They persist as `Assertion(assertionOrigin: aiSuggested)` with the rejecting `Attestation` linked. Auditors reconstruct the lifecycle from the IRI graph.

**Cross-reference:** the prior `rkaf:Waiver` proposal was falsified on identical grounds (`thoughts/plans/2026-05-13-attestation-temporal-bounds-and-freshness.md §Context`).

---

## Pattern 3 — "I need a versioned retrieval policy artifact"

**Composed primitives:** `rkaf:AccessScope` + `rkaf:usageEligibility` lattice + `rkaf:BridgeConsumerRegistration` + `rkaf:hasWarrant` / `rkaf:hasAuthority` (authority requirement) + bridge rule #1.

**Where they live:**
- `spec/rkaf-core.md §4.6` + `constraints/core/access-scope.cue` — seven-value `accessScopeKind` (incl. `partnerVisible`, `organizationVisible`, `roleRestricted`, `regulatoryRestricted`); regulatory classes (HIPAA-PHI, GDPR-PII, FERPA, CJIS, classified, legally-privileged); attachable to Assertion / Attestation / EvidenceBinding / SourceFragment.
- `spec/rkaf-behavior.md §1.2 Step 5` — eligibility lattice and consumer capability cap.
- `constraints/core/bridge-consumer-registration.cue` — `capability_cap`, `supported_evaluation_anchors`, `registry_version_ranges`, `automatic_migration_support`.
- `spec/rkaf-core.md §8.4` (normative) — consumers MUST preserve AccessScope through "retrieval, projection, summarization, federation, and AI-assisted consumption."
- `constraints/adversarial/access-scope-leakage.cue` + `fixtures/adversarial/access-scope-leakage-negative.jsonld` — adversarial coverage.

**Coverage:**

| Retrieval-policy need | Rulespec coverage |
|---|---|
| Who may retrieve which assertions | `AccessScope` (kind + permittedRole + regulatory class) |
| What operations the retrieved assertion may participate in | `usageEligibility` lattice (7 levels: search → publication → officialUse) |
| What the consumer can do at all | `BridgeConsumerRegistration.capability_cap` |
| What authority must back the retrieved assertion | `hasWarrant` / `hasAuthority` + bridge rule #1 |
| Auditability of the policy | `BridgeValidationResult.findings` (IRI-addressable, retained) |

**Recipe — "regulatoryRestricted AccessScope composing DPV privacy classification (GDPR/HIPAA)":**

```jsonld
{
  "@context": "../../context/rkaf-context.jsonld",
  "@id": "ex:access-scope-hipaa-phi",
  "@type": "rkaf:AccessScope",
  "rkaf:accessScopeKind": "rkaf:regulatoryRestricted",
  "rkaf:regulatoryClass": ["rkaf:HIPAA-PHI"],
  "dpv:hasPersonalDataCategory": [
    "https://w3id.org/dpv/dpv-pd#MedicalHealth"
  ],
  "dpv:hasLegalBasis": "https://w3id.org/dpv/legal/us#HIPAA"
}
```

`dpv:hasPersonalDataCategory` carries a set of DPV personal-data-category IRIs (DPV-PD sub-vocabulary). `dpv:hasLegalBasis` carries a single IRI identifying the applicable legal basis. `dpv:hasPurpose` is optional and names the processing purpose. L1 does not constrain DPV predicate ranges; these are cross-namespace annotations only. See `fixtures/edges/access-scope-with-dpv-composition-positive.jsonld` for a worked example and `spec/rkaf-core.md §9.2` for the version-pinned alignment row (DPV 2.3).

**What is NOT in Rulespec and is intentionally outside scope:** `scoreWeights`, `temporalStrategy`, `conflictHandlingMode`, `allowedGraphs` / `deniedGraphs`. These are retrieval-engine configuration. They belong in the consumer's overlay or, if governance is required, in an incubated extension profile at `profiles/retrieval/`.

**When an extension profile is warranted:** three unrelated named consumers each demand a versioned governance artifact carrying retrieval-engine config. Until then, application code or consumer-local config is the right home.

---

## Pattern 4 — "I need source-document temporal validity" (amendment / repeal / consolidation)

**Composed primitives:** `rkaf:EffectivePeriod` + `rkaf:LifecycleEvent` (five amendment-class kinds) + `rkaf:supersedesAssertion` + `eli:consolidates` (for multi-predecessor consolidation, directly imported from ELI 1.5) + `rkaf:RevalidationEvent` + `rkaf:PointInTimeException` + `CascadeClosureV1` + bridge rule #5. ELI / AKN / LegalRuleML alignment carries the legal-source semantics.

**Where they live:**
- `constraints/core/effective-period.cue` — `effectivePeriodStart` (required), `effectivePeriodEnd`, `retroactiveFrom`, `sunsetAt`.
- `constraints/core/lifecycle-event.cue` — `lifecycleEventKind` covers `rkaf:amendment | rkaf:supersession | rkaf:rescission | rkaf:materialRevision | rkaf:editorialRevision`.
- `context/rkaf-context.jsonld` — `rkaf:supersedesAssertion` (many-to-many; supersession edge, predecessors become historical).
- `context/rkaf-context.jsonld` — `eli:consolidates` / `eli:consolidated_by` (many-to-many; consolidation edge, predecessors remain legally extant). Predicate definitions in ELI 1.5 core (`http://data.europa.eu/eli/ontology#`); rdfs:comment explicitly directs repeated use for multi-predecessor consolidation.
- `spec/rkaf-behavior.md §2.1` — `CascadeClosureV1` propagating amendment effects through C1–C10 trigger edges.
- `spec/rkaf-behavior.md §3.5` — bridge rule #5 enforcing `staleForCurrentUse` transitions.
- `spec/rkaf-core.md §9.2` — ELI / ELI-I alignment normative statement (names `eli:consolidates` and the consolidation-vs-supersession semantic distinction).
- `thoughts/plans/2026-05-12-rkaf-layer3-registries-v0.2.md:63-80` — Source Authority Registry plan including `dcterms:replaces` / `dcterms:isReplacedBy` + `freshnessSignal`.

**Recipe — "Source S2 amends source S1, effective 2026-06-01":**

```jsonld
[
  {
    "@id": "ex:source-S2",
    "@type": "rkaf:Assertion",
    "rkaf:supersedesAssertion": [{ "@id": "ex:source-S1" }],
    "rkaf:hasEffectivePeriod": {
      "@type": "rkaf:EffectivePeriod",
      "rkaf:effectivePeriodStart": "2026-06-01"
    }
  },
  {
    "@id": "ex:lifecycle-amendment-S1-to-S2",
    "@type": "rkaf:LifecycleEvent",
    "rkaf:lifecycleEventKind": "rkaf:amendment",
    "rkaf:appliesTo": { "@id": "ex:source-S1" },
    "rkaf:occurredAt": "2026-06-01"
  }
]
```

**In-flight protection:** `rkaf:PointInTimeException` preserves prior-version applicability for in-flight cases. `RevalidationEvent` + `RevalidationClosureEvent` track downstream re-checks after the amendment.

**Recipe — "Consolidated text C2026 incorporates three predecessor acts A, B, C":**

```jsonld
[
  {
    "@id": "ex:consolidated-text-C2026",
    "@type": "rkaf:Assertion",
    "eli:consolidates": [
      { "@id": "ex:source-A" },
      { "@id": "ex:source-B" },
      { "@id": "ex:source-C" }
    ],
    "rkaf:hasEffectivePeriod": {
      "@type": "rkaf:EffectivePeriod",
      "rkaf:effectivePeriodStart": "2026-01-01"
    }
  }
]
```

`eli:consolidates` is non-functional in ELI core — repeated use is canonical. Predecessors `ex:source-A`, `ex:source-B`, `ex:source-C` remain legally extant; the consolidated text is an editorial restatement, not a supersession event. If a predecessor were also being replaced (not just incorporated), add `rkaf:supersedesAssertion` for that specific edge; the two predicates compose. See `fixtures/edges/consolidates-multi-predecessor-edge.jsonld` for a worked example.

**Consolidation vs supersession — when to use which:**

| Concept | Predicate | Semantics | Predecessor status |
|---|---|---|---|
| Editorial consolidation | `eli:consolidates` | "I am a merged restatement incorporating these versions" | Remain legally extant |
| Supersession | `rkaf:supersedesAssertion` | "I replace these; they are now historical" | Become superseded |
| Amendment (event-graph) | `rkaf:LifecycleEvent` with `lifecycleEventKind: rkaf:amendment` | Records the act of changing | N/A (event-typed) |

**Do not roll your own `rkaf:SourceVersion`.** ELI 1.5 / ELI-I + Akoma Ntoso + LegalRuleML + USLM are canonical. Align rather than duplicate.

---

## Pattern 5 — "I need a typed AI-answer audit trace"

**Composed primitives:** `rkaf:BridgeValidationResult.findings` + `rkaf:GeneratedWorkProduct.justifiedByAssertion` + `rkaf:EvidenceBinding.bindsSourceFragment` + `rkaf:AILineage` + `rkaf:ConfidenceRecord` + `rkaf:hasAccessScope` + `rkaf:EffectivePeriod` + `rkaf:PointInTimeException` + PROV-O.

**Where they live:**
- `spec/rkaf-core.md §2` (normative) — three-axis claim model that consumers MUST preserve.
- `spec/rkaf-core.md §8.1-8.7` (normative) — seven AI-substrate obligations.
- `constraints/core/bridge-validation-result.cue` — `authorityChainTraversal`, `findings` (IRI-addressable), `conceptResolutionResults`.
- `constraints/core/generated-work-product.cue` — `justifiedByAssertion`, `consumerLifecycleState`.
- `constraints/core/evidence-binding.cue` — `bindsSourceFragment`, `lastVerifiedAt`, `verifiedBy`.
- `crates/rkaf-runtime/src/bridge.rs` — bridge rules 7 and 10 enforce justification chain + GWP metadata at L4.

**Coverage:**

| Trace need | Rulespec representation |
|---|---|
| Which assertions backed the answer | `GeneratedWorkProduct.justifiedByAssertion` (IRI set) |
| Which source fragments backed each assertion | `EvidenceBinding.bindsSourceFragment` (per assertion) |
| Authority chain traversed | `BridgeValidationResult.authorityChainTraversal` |
| AI model lineage | `AILineage` (model, version, prompt, seed, input hash) |
| Confidence | `ConfidenceRecord` with `confidenceBasis` |
| Access scope context | `hasAccessScope` on each referenced node |
| Temporal context | `hasEffectivePeriod` + `PointInTimeException` |
| Generation timestamp | `prov:generatedAtTime` (on GWP) |

**Packaging for exchange (not vocabulary):** when a consumer needs to ship the trace as one signed object, the right approach is one of:

1. **Trellis envelope** wrapping a JSON-LD frame over the existing IRI graph. The Trellis envelope already provides signing, custody, and replay semantics; AnswerTraceBundle as a class would have duplicated this.
2. **W3C Verifiable Credential 2.0** with the trace as the credential subject.
3. **Nanopublication** for FAIR exchange.

In all three cases the trace *contents* are the existing Rulespec primitives joined by IRI. No new vocabulary.

**Do not introduce `rkaf:AnswerTraceBundle` as a vocabulary class.** A bundle class invites consumers to populate a summary blob instead of properly linking the underlying IRI graph — directly violating §8.4 ("AI consumers MUST treat retrieved source material as data, not instruction" and the preservation-through-retrieval mandate).

---

## Pattern 6 — "I need to mark edges as computed / materialized / ephemeral"

**Composed primitives:** PROV-O (`prov:wasDerivedFrom`, `prov:wasGeneratedBy`, `prov:generatedAtTime`, `prov:Bundle`) + `rkaf:AILineage` (for AI-computed edges) + `rkaf:lifecycleEvent.cascadeAlgorithm` (for cascade-computed edges) + `rkaf:hasArtifactIdentifier` (hash-sha256, for base-graph addressing) + SHACL-AF §8.4 inference-graph convention (for rule-derived edges).

**Where they live:**
- `context/rkaf-context.jsonld:869-878` — PROV-O imports.
- `constraints/core/ai-lineage.cue` — full model-generated-edge lineage.
- `constraints/core/lifecycle-event.cue:22-24` — `cascadeAlgorithm` field.
- `spec/rkaf-core.md §4.1` — `rkaf:hash-sha256` identifier scheme.
- `spec/rkaf-core.md §9.4` (normative) — composition discipline: "do not reinvent — if a public ontology owns the local problem, Rulespec uses it."

**Standard pattern (rule-derived edges):**

Place rule-derived triples in a separate JSON-LD named graph or SHACL-AF inference graph. Attach PROV-O metadata to that graph as a `prov:Entity`:

```jsonld
{
  "@id": "ex:inferred-graph-2026-05-20T14:30:00Z",
  "@type": "prov:Entity",
  "prov:wasDerivedFrom": {
    "@id": "ex:canonical-graph-rev-A1B2",
    "rkaf:hasArtifactIdentifier": {
      "rkaf:artifactIdentifierScheme": "rkaf:hash-sha256",
      "rkaf:artifactIdentifierValue": "sha256:<hex>"
    }
  },
  "prov:wasGeneratedBy": { "@id": "ex:cascade-closure-v1" },
  "prov:generatedAtTime": "2026-05-20T14:30:00Z"
}
```

**Standard pattern (AI-computed edges):** use `AILineage` on the edge-bearing artifact; the lineage carries model, prompt, seed, and approver.

**Standard pattern (cascade-computed edges):** the in-memory cascade computation (`crates/rkaf-runtime/src/cascade.rs::CascadeClosureV1`) does not produce serialized edges. If a consumer needs to *persist* a cascade-closure snapshot, wrap it in a `GeneratedWorkProduct` with the PROV-O metadata above; `lifecycleEvent.cascadeAlgorithm` already names the algorithm.

**Ephemerality / cache invalidation:** consumer-side concern. Storage adapters track ephemerality in their own metadata. The substrate exposes the `wasDerivedFrom` hash so the consumer can compute staleness; it does not declare ephemerality.

**Do not introduce `rkaf:MaterializedEdge`.** §9.4 requires composing public ontologies (PROV-O, SHACL-AF) when they own the local problem.

---

## Cross-reference: decision principles

A proposed addition belongs in core Rulespec only if:

1. It is broadly useful across multiple consuming systems.
2. It cannot be adequately represented with existing Rulespec primitives or imported standards (PROV-O, DCAT, ELI, AKN, LegalRuleML, SHACL-AF, SKOS, ODRL, DPV).
3. It materially improves governance, auditability, conformance, or safety.
4. It can be validated with positive / negative / edge fixtures and Pattern-C SHACL constraints.
5. It does not turn Rulespec into an application framework, hardcode RAG / property-graph infrastructure, or fragment alignment with mature legal-data standards.

Otherwise: extension profile, downstream service contract, or consumer-side overlay.

See [ADR 0149](../../thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md) for the full review session that produced these patterns.
