# §9 Composition Discipline — Decision Framework

**Status:** Reference document · **Anchor:** [`spec/rkaf-core.md`](../../spec/rkaf-core.md) §9.1–§9.4 · **Origin:** post-ADR-0149 audit pass (fs-pmf4 spike + cross-stack-scout + 2× code-scout reviews) · **Date:** 2026-05-20

This memo captures the framework, taxonomy, and per-prefix precedents that should govern future §9 composition decisions. It does not introduce new normative content; it documents the discipline behind decisions that have landed (ELI in ADR-0149; aspirational-prefix triage in PKA-03og) and decisions yet to land (DPV composition; F-comp-3/F-comp-4 OA + SKOS predicate landings; F1+F2 OA renames).

## 1. The measurement metric

Composition decisions are evaluated on:

```
priority = (User Value [real + theoretical]) × (Architectural Debt Reduction)
```

**Not** on implementation cost, session count, or developer-time estimate. Time-cost framing surfaces during execution; it does not govern the decision.

- **User Value (real)** — current consumers, named buyers, partner demand, procurement-evaluator signal.
- **User Value (theoretical)** — buyers Rulespec is positioning for; AI-agent interop with broader linked-data ecosystem; future composition wedges.
- **Architectural Debt Reduction** — does the change *reduce net debt* (replace overclaim with verified interop, convert vague alignment to concrete typed point, remove dead weight) or *accrue net debt* (lock in an untested binding, consume closed-taxonomy budget without validation)?

A composition that scores positive on all three components is unambiguous; a composition that scores positive on user value but accrues debt without validation is a deferral candidate, not a landing candidate.

## 2. The four composition modes

§9 as written presents a two-mode taxonomy (§9.1 Imports vs §9.2 Alignments). The actual corpus implements four modes:

1. **Direct predicate import** — predicate declared in `context/rkaf-context.jsonld`, used in CUE shape or projected schema. Examples: `prov:wasGeneratedBy`/`wasAttributedTo`/`wasDerivedFrom`/`generatedAtTime` (4 defs); `eli:consolidates`/`consolidated_by` (2 defs, post-ADR-0149).

2. **Class-tag composition** — external IRI used as `@type` value or as a typed-string enum value. The rkaf-namespaced predicate carries the external term as data. Examples: `oa:TextQuoteSelector` as `rkaf:selectorKind` enum value; `skos:Concept` as a multi-typed `@type`; `skos:exactMatch` as `rkaf:mappingPredicate` enum value.

3. **URI-value composition** — external URI carried inside an rkaf-namespaced predicate, gated by a scheme enum. Example: ELI URIs in `rkaf:hasArtifactIdentifier`, where `rkaf:artifactIdentifierScheme: "rkaf:eli"` declares the scheme and the URI carries the external structure.

4. **Pattern citation / prior art** — architectural priors with no predicate or URI flow. Example: Nanopublications cited as overlay-shape pattern (assertion graph + provenance graph + publication-info graph); LegalRuleML cited for defeasibility-preservation discipline.

Each mode has different debt characteristics. Mode 1 is the highest-commitment (predicate is declared in the project's authoritative context); mode 4 is the lowest (no namespace declaration needed). When a §9 row's actual integration is mode-2 or mode-3, declaring the prefix at mode-1 cost (in `rkaf-context.jsonld`) is debt without value.

## 3. The four-cohort treatment

When evaluating a §9 alignment claim against the user-value × debt-reduction metric, decisions fall into four cohorts:

### Cohort A — Compose now

**Trigger:** real user value (named buyers, current consumers, procurement signal) AND debt-reducing composition shape (replaces overclaim with verified interop point; matches an established low-debt precedent).

**Treatment:** land predicate-level composition. Decline L1/L3 constraints over the external predicate's range (partner producers conform to the external ontology's own domain/range). Pin the external ontology's version in the §9 alignment row. Same shape as the ELI precedent.

**Precedent:** `eli:consolidates` (ADR-0149), `dpv:` into
`rkaf:AccessScope`, and the 2026-07-24 promotion of `foaf:primaryTopic` plus
DCAT 3 qualified relations for the named Spicy Regs document/agenda consumer.

### Cohort B — Clarify existing right answer

**Trigger:** the alignment is already correctly composed at mode 2/3/4 and the existing shape is debt-reducing. Forcing mode-1 composition would *accrue* debt (partial alignment fragmenting interop with full-ontology consumers).

**Treatment:** make the existing composition mode legible in the §9 row. Do not change the implementation.

**Precedent:** `odrl:` (overlay-projector composition is the right answer; §9.2 row needs to make this explicit).

### Cohort C — Demote to See also

**Trigger:** theoretical user value is real (legitimate future audience, named ontology family) but no current consumer demand to validate a specific binding shape. Composing now would lock in an untested binding (closed-taxonomy commitment becomes irreversible across release boundaries).

**Treatment:** move from "Imports" or "Alignments" to a "See also — partner ontologies for future projection" subsection. Preserves option value at zero current debt. Composition lands when a partner arrives with a real use case (same path ELI took).

**Precedent (post-PKA-03og):** `lrml:`, `rrmv:`, `eco:`, `sepio:`, `cito:`, `dcterms:`.

### Cohort D — Drop prefix declaration

**Trigger:** zero current value AND the declared prefix in `rkaf-context.jsonld` is dead weight (no fixtures, no CUE, no spec body usage outside the §9 row itself). The prefix declaration reads as an overclaim — a future-tense commitment that hasn't landed.

**Treatment:** remove the prefix from `context/rkaf-context.jsonld`. If the alignment is a pattern citation (mode 4), keep the §9.2 prose row as architectural prior-art without a namespace claim. Re-declare when the layer that needs it ships.

**Historical precedent (post-PKA-03og):** `dcat:` was initially dropped while
no Reference Corpora consumer existed; it moved to Cohort A on 2026-07-24 when
Spicy Regs supplied a concrete qualified-relation carrier and corpus.
`nano:` (pattern citation, not predicate import) and `schemaorg:` (SEO
projector not built) remain current examples.

## 4. Audit findings — what landed where

The 2026-05-20 audit pass classified each of the 17 cross-namespace prefixes against the four cohorts:

| Cohort | Prefixes | Status |
|---|---|---|
| **A — Compose** | `prov:`, `eli:`, `oa:`, `skos:`, `dpv:`, `foaf:primaryTopic`, scoped DCAT 3 qualified relations | Active imports with named consumers |
| **B — Clarify** | `odrl:` (overlay-projector pattern) | Spec edit in PKA-03og |
| **C — Demote** | `lrml:`, `rrmv:`, `eco:`, `sepio:`, `cito:`, `dcterms:` | Spec edit in PKA-03og |
| **D — Drop** | `nano:` (as prefix), `schemaorg:` | Spec edit + context cleanup in PKA-03og; `dcat:` promoted to A on 2026-07-24 |

`aknt:` and `uslm:` are special: their integration *exists* but is renamespaced under rkaf-namespaced enum strings (`rkaf:aknt-eId`, `rkaf:uslm-section`, `rkaf:uslm`) — mode 2/3 composition with the foreign prefix declared for forward compatibility. PKA-03og treats them as keep-with-explicit-note.

## 5. Why DPV is the next Cohort A landing

DPV (W3C Data Privacy Vocabulary) is the single highest-leverage aspiration the audit surfaced. The case:

- **Real user value:** GDPR/HIPAA buyers exist now and recognize DPV alignment as a procurement-evaluator signal. PKAF's positioning (regulated-environment trust substrate) maps directly to the audience that scans for DPV composability.
- **Theoretical user value:** AI agents reasoning about privacy posture can compose standard DPV vocabulary without PKAF-specific training. Privacy-tooling ecosystem (DPV-based linting, GDPR conformance checkers, HIPAA mappers) gains an automatic alignment point with PKAF substrate.
- **Debt reduction:** the §9.2 row at `spec/rkaf-core.md:290` claims alignment but the corpus has zero `dpv:` composition. Composing converts an overclaim into a concrete typed interop point.
- **Debt accrual:** minimal. `accessScopeKind` closed enum remains PKAF's primary discipline (cascade integration, conformance gates). `dpv:` predicates layer on top as non-functional cross-namespace annotations, matching the ELI precedent (decline L1/L3 constraints over DPV's range; partner producers conform to DPV's own taxonomy).
- **Composition shape:** add `dpv:hasPersonalDataCategory`, `dpv:hasLegalBasis`, optionally `dpv:hasPurpose` as optional cross-namespace predicates on `rkaf:AccessScope`. For `accessScopeKind = regulatoryRestricted` cases, conformance SHOULD compose `dpv:hasPersonalDataCategory`. L1 doesn't enforce.

This is the move that earns the §9.2 DPV row.

## 6. Decision precedents for future §9 candidates

When a new alignment candidate is proposed (e.g., a partner asks "can PKAF compose with ontology X?"), the framework is:

1. **What composition mode would land?** (1/2/3/4)
2. **What's the user-value evidence?** Real consumer demand or theoretical future fit?
3. **What's the debt shape?** Does composition reduce net debt (replace overclaim, verify interop) or accrue net debt (untested binding, closed-taxonomy commitment)?
4. **Which cohort does it fall into?** A/B/C/D per §3 above.
5. **What's the precedent?** Cite ELI or the scoped DCAT/FOAF promotion (A),
   ODRL (B), CITO/LegalRuleML (C), and Nano/Schema.org (D) as the established
   treatments.

Cohort A landings should match the ELI shape: predicate-level imports in context, L1/L3 decline to constrain external range, alignment row pins the external ontology's version. Cohort B/C/D are spec edits, not implementation work.

## 7. Cross-references

- **Anchor ADR:** [`thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md`](../../../thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md) (stack root)
- **Spike that produced the precedent:** [`thoughts/plans/2026-05-21-eli-consolidates-spike.md`](../plans/2026-05-21-eli-consolidates-spike.md)
- **Spec anchor:** [`spec/rkaf-core.md`](../../spec/rkaf-core.md) §9.1–§9.4 (lines 262–308)
- **Active tickets** (as of 2026-05-20):
  - `fs-pmf4` (closed) — ELI-consolidates spike
  - `PKA-03og` — §9 reshape (four-cohort treatment of §9; absorbs `fs-e9sw` and `fs-e9sw`'s superseded scope)
  - `PKA-ehze` — F1+F2: `rkaf:hasSelector` → `oa:hasSelector` + `rkaf:bindsArtifact` → `oa:hasSource`
  - `PKA-f03y` — F-comp-3: compose `oa:exact`/`prefix`/`suffix`
  - `PKA-2szi` — F-comp-4: compose `skos:prefLabel`/`altLabel`/`broader`/`narrower`
  - `PKA-4pir` — F4 / F-comp-2: post-v1.0 AILineage→PROV-O activity composition
  - **DPV composition** — new P2 ticket to be filed alongside this memo
