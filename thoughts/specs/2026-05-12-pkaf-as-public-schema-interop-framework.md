# Rulespec (RKAF) — Knowledge Assertion Framework

**Strategic specification — Working Draft, pre-release**

> **Naming note.** The framework was previously called PKAF (Policy Knowledge Assertion Framework). It is renamed to **Rulespec** as of this spec, with **RKAF** as the formal acronym (Rulespec Knowledge Assertion Framework). The rename reflects that "rules" (in the broad business-rules / decision-rules / financial-rules / regulatory-rules sense) is the actual center of gravity — broader than "policy" but more honest than "knowledge" alone. The vocabulary prefix changes from `pkaf:` to `rkaf:`; the IRI namespace from `https://w3id.org/pkaf/...` to `https://rulespec.org/...`. Existing v0.1.x file paths under `PKAF/spec/` and `PKAF/context/` retain their current names until the on-disk repo rename is executed; this spec uses the new branding throughout, and references existing v0.1.x files by their current on-disk paths.

> **Stack positioning.** Rulespec joins **Formspec** (data collection), **Workspec** (work/process orchestration, formerly WOS), and **Rulespec** (rule governance) as the three -spec siblings of the formspec-stack. Forms collect data, work runs processes, rules govern decisions. Trellis (cryptographic anchoring) and FEL (expression language) sit alongside as supporting substrates. Rulespec is governed and developed independently of any single adopter, including the formspec-stack.

> **Scope disambiguation.** "Rule" in Rulespec means a *governed, evidence-grounded structured claim or decision*. Rulespec is **not** a rules engine, **not** rules-as-code, **not** an execution language. It is a data ontology and federation substrate for claims and the metadata that grounds them. Engines, compilers, retrieval systems, and execution layers MAY consume Rulespec but are not part of it.

| | |
|---|---|
| **This version** | `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` |
| **Status** | Pre-release. Breaking changes expected; signaled via CHANGELOG. No semver compatibility guarantees yet. |
| **Repo** | Rulespec will be extracted to its own public repository under the formspec organization and submoduled back into `formspec-stack/`. |
| **Editors** | TBD — single-vendor authorship is incompatible with the federation thesis; see §13. |
| **Companion documents** | `spec/pkaf-core-v0.1.md`, `spec/pkaf-concept-registry-v0.1.2.md`, `reports/v0.1.1-release-manifest.md` |

## Abstract

Rulespec is a public federation substrate for **evidence-grounded structured claims** — assertions bound to addressable source fragments, traced through warrant chains (legal authority being one warrant family among many), scoped by applicability, gated by eligibility, visible under access scope, and tracked through lifecycle events. Policy is one use case; scientific reproducibility, journalism citation, contracting transparency, audit trails, regulatory filing, and AI training-data provenance are siblings.

The framework comprises seven layers — Vocabulary, Constraints, Registries, Projectors, SDKs, Conformance, Reference Corpora — bound by a versioned contract. SHACL becomes one constraint compilation target rather than the source of truth. Cryptographic anchoring is dependency-inverted: Rulespec defines the abstract contract; bindings (Trellis, COSE, Verifiable Credentials, Sigstore, IPFS) depend on Rulespec. AI tooling is treated as a substrate accelerator, not a decision-making authority — vocabulary and projector discipline is calibrated to LLM-tractability so AI-assisted authoring and consumption are first-class without bypassing human review.

Partners join the federation at any of six adoption depths. The first reference consumer, WOS Studio (Authoring), commits to deep adoption: its core schemas are derived from Rulespec Vocabulary, its types align with Rulespec taxonomies, its emitted artifacts wear Rulespec overlays. Studio's depth proves the substrate is real; the depth gradient lets partners join at the depth that fits them.

## Status of this document

This is a **strategic specification** in Rulespec's `thoughts/specs/` planning tree. It is **non-normative on payload semantics** (those remain in `spec/pkaf-core-v0.1.md` and successors) and **normative on the framework's structural commitments** — the seven layers, the anchoring dependency inversion, the depth gradient, the AI-accelerator posture, the federation pattern.

This document does not change Rulespec v0.1.x normative payload content. Editor's drafts of each framework layer derive from this document and ship under Rulespec's next release cycle.

The W3C-style spec format is used because **unambiguous agent-readability** is exactly its value: humans and AI agents reading this document get a single non-ambiguous source for the framework's structural commitments. Specs are for clarity. Tooling (SDK, CLI, datasets) is for adoption. Ship both.

## Table of contents

1. [Introduction](#1-introduction)
2. [Conformance](#2-conformance)
3. [Terminology](#3-terminology)
4. [Framework architecture](#4-framework-architecture)
5. [Layer 1 — Vocabulary](#5-layer-1--vocabulary)
6. [Layer 2 — Constraints](#6-layer-2--constraints)
7. [Layer 3 — Registries](#7-layer-3--registries)
8. [Layer 4 — Projectors](#8-layer-4--projectors)
9. [Layer 5 — SDKs](#9-layer-5--sdks)
10. [Layer 6 — Conformance](#10-layer-6--conformance)
11. [Layer 7 — Reference Corpora](#11-layer-7--reference-corpora)
12. [Versioning](#12-versioning)
13. [Governance](#13-governance)
14. [Reference consumer pattern](#14-reference-consumer-pattern)
15. [Federation flywheel](#15-federation-flywheel)
16. [Sequencing](#16-sequencing)
17. [Appendix A — Studio-derived primitive promotions](#appendix-a--studio-derived-primitive-promotions)
18. [Appendix B — Relationship to existing standards](#appendix-b--relationship-to-existing-standards)
19. [Appendix C — Why SHACL is not the constraint source of truth](#appendix-c--why-shacl-is-not-the-constraint-source-of-truth)
20. [Appendix D — Adoption depth gradient](#appendix-d--adoption-depth-gradient)
21. [Appendix E — Partner onboarding](#appendix-e--partner-onboarding)
22. [References](#references)

---

## 1. Introduction

### 1.1 What this is

Rulespec is the public substrate for any system that needs to make, transport, validate, or act on **evidence-grounded structured claims**. The structural primitives — assertion, artifact, source fragment, evidence binding, warrant (with legal authority as one specialization), eligibility, applicability, access scope, lifecycle, supersession, concept, adoption, justification, attestation, confidence record, bridge — are the same across every domain where the question "what backs this claim?" is load-bearing.

The framework's job is to make those primitives interoperable across heterogeneous tools and services without consolidating around a single vendor's stack.

### 1.2 Why this is the moment

Two simultaneous shifts make a public federation substrate tractable now:

1. **AI-assisted authoring is real.** LLMs can extract structured claims from policy text, regulatory filings, scientific papers, contract language, and audit logs at scale. The bottleneck is no longer extraction; it's *trust* — knowing what the AI extracted, what source backed it, what authority justified it, what scope it applies in, what to do when the source is superseded. Rulespec's primitives are exactly that trust layer.
2. **Cross-org interop has an actual market.** Regulated environments (government, healthcare, finance, civic-tech) need to exchange structured claims across organizational boundaries with provenance preserved. Today every pair of partners ships custom integration. Rulespec lets one integration cover N partners.

The framework treats AI as a **substrate accelerator**, not a decision-making authority — see §1.5. Vocabulary and projector discipline are calibrated so AI-assisted authoring and consumption are first-class workflows without bypassing human review.

### 1.3 The federation thesis [Normative]

Rulespec is a **federation substrate**, not a centralized standard. The framework defines the shared semantic ground; partners build their own tools, choose their own adoption depth, and interoperate through registries and projectors.

Three structural commitments make federation tractable:

1. **Shared vocabulary.** Partners agree on the semantic primitives. Disagreements resolve through the §13 RFC process, not through fork.
2. **Shared infrastructure.** Federable registries (Source Authority, Concept, Bridge Contract) let partners look up authoritative classifications, resolve concept mappings, and verify each other's contract claims without bilateral integration.
3. **Multiple adoption depths.** Partners join at the depth that fits them — overlay-only, vocabulary-aligned, schema-derived, or substrate-replacing. The framework MUST accommodate all depths simultaneously.

This distinguishes Rulespec from single-vendor platforms (which require partner submission to vendor authority) and consortium standards (which require partner submission to a consensus that often arrives too slowly to matter). The posture is: *commit to the shared semantic ground; choose your own depth; build your own tools; interoperate at the substrate*.

### 1.4 Gap analysis [Informative]

| Standard | Purpose | Coverage gap |
|---|---|---|
| **ELI** (European Legislation Identifier) | EU framework for legal-resource identifiers, legislation metadata, URI patterns, machine-readable legal metadata | Legal-resource identity + metadata only; **Rulespec imports rather than reinvents** (see §5.9, Appendix B) |
| **ELI-DL / ELI-I** | ELI extensions for draft legislation and legislative impacts/amendments | Same scope as ELI; load-bearing for lifecycle + supersession over legal artifacts |
| **RRMV** (Reporting Requirement Metadata Vocabulary) | EU legal ontology for modeling reporting requirements in legal provisions | Reporting-requirement modeling within legal sources; **Rulespec aligns** for the requirement→assertion mapping (see §5.6) |
| **Akoma Ntoso / LegalDocML** | XML model for legislation, parliamentary, judicial, executive documents | Source-document structure only; complements `SourceFragment` selectors (see §5.5) |
| **USLM** (United States Legislative Markup) | US legislative XML model | US legal source structure; same role as Akoma Ntoso for the US |
| **LegalRuleML** | OASIS standard for formal legal norms with defeasibility, deontic operators, exceptions, temporality | Formal rule encoding only; **Rulespec aligns** for the legal-warrant family (see §5.6) |
| **W3C PROV-O** | Provenance ontology | Provenance only; **Rulespec imports** for warrant chain provenance and AI lineage (see §5.9) |
| **W3C Web Annotation Ontology (OA)** | Selector vocabulary for annotations | Selector machinery only; **Rulespec imports** for `SourceFragment` (see §5.5, §5.9) |
| **W3C SKOS** | Concept schemes, thesauri, mapping relations | Concept relations only; **Rulespec imports** for the Concept Registry (see §5.9) |
| **Nanopublications** | Portable assertion + provenance + publication-info graphs | Publication pattern only; **Rulespec aligns** the overlay-attachment pattern with nanopublication shape (see §4.3, Appendix B) |
| **ECO** (Evidence & Conclusion Ontology) / **SEPIO** | Scientific evidence types and assertion methods | Scientific-claim provenance only; **Rulespec aligns** for the scientific-warrant family (see §5.6) |
| **EuroVoc / ESCO** | EU multilingual thesauri (legal/policy concepts; skills/occupations) | Concept registries only; usable as ConceptRegistry seed data (see §11) |
| **DCTERMS** | Dublin Core metadata terms (`replaces` / `isReplacedBy` / `creator` / etc.) | Generic metadata; **Rulespec aligns** supersession predicates with `dcterms:replaces` (see §5.9) |
| **W3C ODRL** | Permission / prohibition / duty modeling | Rights-expression only; **Rulespec aligns** AccessScope with ODRL pattern (see §5.8, §5.9) |
| **W3C DPV** | Privacy semantics overlay | Privacy only; **Rulespec aligns** for AccessScope `regulatoryRestricted` cases (see §5.8) |
| **W3C Verifiable Credentials** | Credential issuance + verification | One possible **anchoring binding** (§4.6); not a Rulespec dependency |
| **HL7 FHIR** | Healthcare interop | Closest precedent for the federation pattern; **Rulespec projects to** FHIR profiles (see §8.3) |
| **NIEM** | US government data exchange | Heavy, enterprise-y; **Rulespec projects to** NIEM IEPDs (see §8.3) |
| **Schema.org / Schema.org/Legislation** | Lightweight web markup | Public discovery only; **Rulespec aligns** for SEO-grade public publication (Appendix B) |
| **DCAT / VoID** | Data catalog vocabulary | Dataset metadata only; **Rulespec aligns** for Reference Corpora publication (see §11) |
| SHACL / ShEx | Constraint languages | No domain ontology, no tooling beyond validators |
| OpenAPI / AsyncAPI | Interface description | No semantic interop |
| Lynx LKG (H2020) | Legal knowledge graph for compliance documents | Closest "legal knowledge graph" prior art; reference, not import |
| OCDS | Open contracting | Domain-specific; possible projector target |
| EU eProcurement Ontology / ePO | EU procurement data | Domain-specific; possible projector target if procurement becomes a reference domain |

No existing artifact occupies the intersection of *evidence-grounded structured claims as a vendor-neutral federation substrate, with first-class multi-format tooling, multi-depth adoption, and AI-tractable authoring*. FHIR is the closest analogue — generalized beyond healthcare, with explicit depth-graded adoption and AI-first vocabulary discipline.

**Rulespec's posture across this landscape is deliberate**: import the foundational ontologies (PROV-O, OA, SKOS, JSON-LD, SHACL), align with the domain-specific ones where they own the local problem (ELI for legal resources, RRMV for reporting requirements, Akoma Ntoso/USLM for legal source structure, LegalRuleML for formal legal rules, ECO/SEPIO for scientific evidence, DPV for privacy, ODRL for rights, DCTERMS for supersession), and project to the carrier-format ones at the partner edge (FHIR, NIEM, OpenAPI, JSON Schema). **Do not reinvent.** §5.9 and Appendix B make these relationships normative.

### 1.5 AI as substrate accelerator [Normative]

Rulespec treats AI as a **substrate accelerator**, not a decision-making authority. Concretely:

1. **AI is a first-class user of the framework.** LLM-driven extraction of structured claims from sources is a primary expected workflow. Vocabulary discipline is calibrated accordingly: closed enums (LLMs steer well off closed taxonomies), no ambiguity (LLMs hallucinate around ambiguity), structured-output coercibility (Vocabulary terms map cleanly to JSON Schema for tool-use APIs).
2. **AI does not decide.** Authoring decisions, approval, ratification, and conformance declaration remain with humans and partner organizations. AI proposes; humans dispose.
3. **The Vocabulary captures the accelerator/authority distinction.** The existing `rkaf:aiSuggested` / `rkaf:aiPromoted` / `rkaf:humanQualified` / `rkaf:humanRevalidation` `AssertionOrigin` values already encode this; the v0.2 promotion of `rkaf:AILineage` (Appendix A) carries the operational detail (model, prompt, confidence, human approver, human rationale).
4. **Projectors emit AI-tractable artifacts by default.** The JSON Schema projector (§8.2) is required to produce schemas that LLMs can use as structured-output targets without preprocessing.
5. **Conformance suites include AI-extraction adversarial fixtures** to surface vocabulary terms that LLMs systematically misinterpret.
6. **Source text is data, not instruction.** AI consumers MUST treat retrieved source material as data, never as instruction to the model. Rulespec overlays MUST NOT grant tool authority to source content. Implementations MUST preserve source warrant, access scope, applicability, lifecycle, and usage eligibility metadata through retrieval, summarization, projection, and generation. Semantic similarity MUST NOT be treated as a substitute for warrant; an assertion the model retrieves because it looks relevant is not authorized merely because it was retrieved.
7. **Anchoring proves integrity, not truth.** Cryptographic anchoring (§4.6) commits that a graph existed, that an actor signed it, that bytes have not changed. It does NOT establish that a claim is true, that a warrant is valid, or that an assertion is operationally eligible. Implementations MUST NOT collapse these distinctions.

The framework does not require AI involvement at any depth. Partners may operate purely human authoring workflows. The accelerator posture means AI workflows are *not penalized* — Vocabulary terms are not designed in ways that break under structured-output extraction.

### 1.6 The three-axis claim model [Normative]

Rulespec separates three orthogonal postures over any claim. These axes are independent; collapsing them is the most common modeling failure in adjacent frameworks.

| Posture | Question | Encoded by |
|---|---|---|
| **Truth** | What evidence and warrant support this claim? | `Assertion`, `EvidenceBinding`, `Warrant`, `SourceFragment`, `Artifact`, `ConfidenceRecord` |
| **Social** | Who attests, objects, adopts, disputes, or publishes this claim? | `Attestation`, `LocalAdoption`, `Justification`, `Supersession` |
| **Consumer** | What may this consuming system do with this claim? | `UsageEligibility`, `ApplicabilityScope`, `AccessScope`, `BridgeValidationResult` |

A claim may be well-evidenced but locally rejected. A claim may be weakly evidenced but community-endorsed. A claim may be truth-supported and operationally ineligible. Rulespec implementations MUST preserve all three axes independently. Implementations that conflate them (e.g., treating community endorsement as warrant, or treating warrant validity as operational eligibility) do not conform.

### 1.7 Out of scope

This specification does not:

- Replace Rulespec v0.1.x normative payload semantics. Those remain authoritative as the editorial baseline.
- Prescribe a constraint source-of-truth language; §6 enumerates candidates and selection criteria.
- Specify cryptographic anchoring binding implementations. The framework defines the abstract contract (§4.6); bindings are external (Trellis, COSE, VC, Sigstore, IPFS, etc.) and live in their own specifications.
- Specify governance bylaws; §13 commits to selecting a governance shell once adoption signal supports the move.
- Prescribe versioning ceremony beyond what §12 commits to. Pre-release; CHANGELOG-driven.

### 1.8 Audience

Spec editors of Rulespec's next release; implementers of Rulespec SDKs and projectors; partners evaluating Rulespec for federation participation; the WOS Studio team committing to depth-D3 adoption as the first reference consumer; binding implementers (Trellis, COSE, VC, Sigstore, IPFS, etc.) wiring Rulespec into cryptographic anchoring substrates.

## 2. Conformance

### 2.1 Document conventions

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in [BCP 14] [[RFC2119](#references)] [[RFC8174](#references)] when, and only when, they appear in all capitals, as shown here.

Sections marked **[Normative]** carry conformance weight on the framework's structural commitments. Sections marked **[Informative]** are explanatory.

### 2.2 Framework conformance contract [Normative]

A Rulespec Framework implementation conforms if and only if it:

1. Implements the Vocabulary layer (§5) at the version pinned by its declared contract.
2. Validates against the Constraints layer (§6) using at least one published constraint compilation target.
3. Resolves identity references against the Registries layer (§7).
4. Either implements at least one Projector (§8) **or** declares "vocabulary-only" conformance.
5. Passes the public Conformance fixture suite (§10) at the declared conformance level.
6. Pins its Rulespec version in every emitted artifact carrying Rulespec semantics.
7. Declares its **adoption depth** per the §4.5 gradient.

Conformance is declared by **consumers**, not authoring tools. See §10.5.

## 3. Terminology

Terms inherited from Rulespec Core v0.1 retain their definitions there; this section adds framework-layer terms.

**Access scope** — The visibility boundary attached to an assertion, attestation, evidence binding, or source fragment. Encodes that an assertion may be public while its evidence is private, that an attestation may be organization-visible while its target is publication-eligible, that a source fragment may be restricted while its existence is disclosable. Implementations MUST preserve access scope through projection, retrieval, summarization, and federation; consumers MUST NOT leak content their access scope forbids.

**Authority grant** — A binding-layer concept: the authority that a specific *identity* (user, role, service principal, workspace) has been granted to perform an operation within a consumer system. Distinct from Rulespec's `Warrant` (which is the grounding of a *claim* against its source). Authority grants belong to identity-binding territory (see §4.6) — Rulespec references identities by IRI but does not model the grant itself. Naming-hygiene note: emerging identity-aware tooling sometimes uses "authority" for both content-grounding and user-role grants; Rulespec reserves the term `Warrant` (and its specialization `Authority` on `rkaf:hasAuthority`) for content-grounding and leaves `Authority grant` to bindings.

**Freshness** — Plan 7d. When a primitive (Attestation, SourceFragment, EvidenceBinding, BridgeValidationResult) was last reconfirmed against its source, encoded as `rkaf:lastVerifiedAt` + `rkaf:verifiedBy`. Orthogonal to lifecycle state. Consumers MAY narrow `usageEligibility` based on a declared max-staleness window. Lifecycle decisions MUST NOT be gated by freshness, and freshness MUST NOT be gated by lifecycle — they answer different questions ("is this in force?" vs. "when did we last check?").

**Adoption depth** — The degree to which a partner integrates Rulespec into its stack. Six discrete depths are defined by the gradient in §4.5. No depth is privileged at the framework level.

**Anchoring contract** — The abstract framework-side contract for cryptographic anchoring of Rulespec assertions and overlays. Implementations are external bindings (Trellis, COSE, VC, Sigstore, IPFS, etc.). Rulespec defines the contract; bindings depend on Rulespec.

**Artifact** — An immutable, addressable unit of source material — a regulatory text version, a published paper, a contract revision, a dataset snapshot, a transcript, an audit log file. Artifacts are the granularity at which sources are versioned and cited. Artifacts MUST be content-addressable (hash, IPFS CID, persistent URI) so that citation is stable across time.

**Confidence record** — A first-class structured representation of confidence over an assertion. Distinguishes uncalibrated model score, calibrated model score, human confidence, review consensus, and source reliability — each captured separately with its method, basis, and evaluator. Avoids "score theater" by requiring calibration status and basis to be explicit. Promoted to Layer 1 in this framework release.

**Evidence binding** — The link between an assertion and the source fragment(s) that ground it. An assertion lacking an evidence binding (or an explicit `noEvidenceReason` permitted by its safety level) is not operationally valid. Evidence bindings carry their warrant kind (methodological, statutory, editorial, etc.) and their access scope.

**Federation** — The pattern by which multiple independently-operated tools and services interoperate around a shared semantic substrate without bilateral integration.

**Federation** — The pattern by which multiple independently-operated tools and services interoperate around a shared semantic substrate without bilateral integration.

**Federation flywheel** — The reinforcing dynamic by which each new partner reduces marginal integration cost for the next, increases registry value for all, and strengthens governance neutrality.

**Native schema** — The schema a partner uses for its own internal artifacts. Rulespec does not validate native schemas at depths Cite-Align; at depth Derive and beyond, native schemas are *generated from* Rulespec Vocabulary via the §8 projector pattern.

**Overlay** — The Rulespec assertions, citations, authority chains, eligibility records, lifecycle packets, and provenance records attached to a native artifact. The overlay is the unit of cross-system interop at every adoption depth.

**Partner** — Any tool, service, or organization participating in the Rulespec federation at any adoption depth. Partner status is conferred by declaring conformance per §2.2 and publishing per §10.4. Open enrollment.

**Profile** — A partner-specific subset and refinement of Rulespec Vocabulary expressing the partner's domain. Studio's profile is the first reference profile.

**Projector** — A bidirectional adapter between Rulespec Vocabulary and a target schema format. Enables Rulespec semantics to ride on artifacts in any supported format and (at depth Derive) enables a partner's native schemas to be generated from Rulespec Vocabulary.

**Reference consumer** — An adopting partner published as a worked example of deep Rulespec adoption. WOS Studio (Authoring) is the first reference consumer at depth Derive; see §14.

**Reference corpus** — A public Rulespec-typed dataset shipped with the framework as a worked example and as adoption infrastructure. See §11.

**Registry** — A queryable, federable instance of one of the three Rulespec registry kinds (Source Authority, Concept, Bridge Contract). Registries provide identity resolution, supersession lookup, warrant-class resolution, and access-scope checks across partners.

**Source fragment** — An addressable region within an Artifact — a section, a paragraph, a clause, a row, a method-section subsection, an interview turn. Source fragments are referenced by selector (XPath / CSS / RFC 5147 text fragment / structured-document section ID / arbitrary partner-defined selector) plus the Artifact identifier. Selector stability across Artifact revisions is a partner obligation; supersession edges between Artifact versions resolve fragment continuity.

**Substrate accelerator** — The framework's posture toward AI: AI tooling is calibrated to be a first-class accelerator of authoring and consumption workflows, but is never the decision-making authority. See §1.5.

**Warrant** — The grounding relation between a claim and what supports it. A universal primitive of which legal `Authority` is one specialization. Other warrant kinds: `methodological` (a scientific method), `empirical` (a dataset or measurement), `editorial` (peer review or editorial process), `cryptographic` (a signature or commitment), `consensus` (community agreement), `sourceReliability` (source-class reputation), `statutory` / `regulatory` / `delegated` / `organizational` / `contractual` / `publication` (the legal/regulatory family inherited from Rulespec Core v0.1). `hasWarrant` is the universal predicate; `hasAuthority` is its specialization for legal/regulatory/organizational contexts.

**Warrant kind** — Closed taxonomy enumerating the kinds of warrant a claim may carry. Hop-local: a multi-hop warrant chain may transition between kinds (e.g., `regulatory → delegated → statutory` in a legal chain; `editorial → methodological → empirical` in a scientific chain).

## 4. Framework architecture

### 4.1 Layer model [Normative]

Rulespec is **seven layers**. Each layer is independently shippable, independently versionable, and individually conformance-testable.

```
┌───────────────────────────────────────────────────────────┐
│  7. Reference Corpora — public Rulespec-typed datasets         │
├───────────────────────────────────────────────────────────┤
│  6. Conformance      — fixture suite, levels, certification │
├───────────────────────────────────────────────────────────┤
│  5. SDKs             — Rust / TypeScript / Python reference │
├───────────────────────────────────────────────────────────┤
│  4. Projectors       — Rulespec ↔ {JSON Schema, JSON-LD,        │
│                        OpenAPI, GraphQL, FHIR, NIEM, ...}  │
│                        Bidirectional + Derive operation    │
├───────────────────────────────────────────────────────────┤
│  3. Registries       — SourceAuthority, Concept, Bridge     │
│                        Federable                             │
├───────────────────────────────────────────────────────────┤
│  2. Constraints      — DSL → SHACL / JSON Schema / Rust /   │
│                        TypeScript / CUE / Rego targets      │
├───────────────────────────────────────────────────────────┤
│  1. Vocabulary       — Assertion, Artifact, SourceFragment, │
│                        EvidenceBinding, Warrant (with       │
│                        Authority as legal specialization),  │
│                        UsageEligibility, ApplicabilityScope,│
│                        AccessScope, Lifecycle, Supersession,│
│                        Concept, Adoption, Justification,    │
│                        Attestation, ConfidenceRecord,       │
│                        Bridge, anchoring contract (§4.6)    │
└───────────────────────────────────────────────────────────┘
```

Layers are organized **bottom-up by dependency**. A conformant implementation MAY declare conformance to a subset of layers provided the subset is contiguous from Layer 1.

### 4.2 Layer separation invariants [Normative]

The following separations are load-bearing across all Rulespec releases:

- **Vocabulary MUST NOT depend on a specific constraint language.** Vocabulary terms are defined by their domain semantics; constraint expressions live in Layer 2.
- **Constraints MUST compile to multiple targets.** No single target (SHACL, JSON Schema, Rust, etc.) is normative for the constraint source of truth; see §6 and Appendix C.
- **Registries MUST be federable.** No single registry instance is normative; the registry contract enables vendor-operated and self-hosted instances to interoperate.
- **Projectors MUST be bidirectional.** A projector that attaches a Rulespec overlay to a target format MUST also extract it back. A projector serving depth-Derive partners MUST also support generating native schemas from Rulespec Vocabulary.
- **SDKs MUST pass identical conformance suites.** Cross-language SDK fragmentation is the failure mode that killed comparable W3C tooling efforts.
- **Conformance is declared by consumers.** Authoring tools MAY publish Rulespec; only consumers MAY claim Rulespec conformance.
- **Depth is a partner choice.** The framework MUST NOT privilege any depth.
- **Anchoring is dependency-inverted.** Rulespec defines the anchoring contract; bindings depend on Rulespec, not the reverse. See §4.6.

### 4.3 The overlay pattern [Normative]

A Rulespec overlay attaches to a native artifact via:

1. A **carrier convention** for the target format. Each Projector defines its carrier convention.
2. A **declared Rulespec version** on the carrier.
3. A **declared adoption depth** on the carrier (`rkaf-depth: derive`).
4. At least one **`rkaf:RelationshipAssertion`** linking the carrier to a source-grounded claim with evidence binding per Rulespec Core §1.

The overlay is the unit that validates, the unit that crosses organizational boundaries, the unit that registries resolve against, and the unit that conformance suites exercise. Native schemas are out of scope for Rulespec validation by construction at depths Cite through Align; at depth Derive and beyond, native schemas are *generated outputs* of the framework rather than independent artifacts.

### 4.4 Substrate-permission model [Normative]

The framework distinguishes two distinct commitments:

- **Framework-level (forbidden):** Rulespec Framework implementations MUST NOT *require* an adopting partner to replace its native schema or substrate. The framework provides shared semantic ground; forcing universal substrate replacement reproduces the single-vendor failure mode the federation thesis exists to avoid.
- **Partner-level (permitted, encouraged for reference consumers):** A partner MAY internally adopt Rulespec Vocabulary as the source of truth for its own schemas, types, and runtime model. Such adoption is the depth-Derive or depth-Substrate posture in §4.5.

Reference consumers choose deep adoption to prove the substrate is real; mainstream partners may choose lighter adoption to reduce integration cost. Both are first-class.

### 4.5 Adoption depth gradient [Normative]

Six adoption depths are defined. Partners declare their depth in conformance disclosures and on emitted artifacts. Full taxonomy in Appendix D.

| Depth | Name | Partner commitment | Framework layers exercised |
|---|---|---|---|
| **D0** | Cite | Partner mentions Rulespec in documentation | None |
| **D1** | Overlay | Partner emits Rulespec overlays on its native artifacts | 1, 2, 4 (one projector) |
| **D2** | Align | D1 + native types/enums name-for-name match Rulespec Vocabulary | 1, 2, 4 |
| **D3** | Derive | D2 + native schemas are generated from Rulespec Vocabulary via the projector pattern | 1-5 |
| **D4** | Substrate | D3 + runtime model operates on Rulespec graphs; native schemas are authoring projections only | 1-7 (full) |
| **D5** | Sole | D4 + non-Rulespec authoring surfaces deprecated entirely | 1-7 (full) |

Depth-D0 is informational and not framework-conformant. Depth-D1 is the minimum conformant depth. Reference consumers SHOULD adopt at depth D3 or higher to demonstrate that deep adoption is practical. A partner stable at D1 forever is a successful federation participant; the gradient is not a ladder.

### 4.6 Anchoring and identity are dependency-inverted [Normative]

Two dependency-inverted contracts live here: cryptographic anchoring (this section's original scope) and identity. Both follow the same posture — Rulespec defines an abstract contract and references the artifact by IRI; bindings depend on Rulespec, not the reverse.

**Identity dependency inversion (Plan 7d clarification).** Rulespec references identities by IRI via `rkaf:attestor`, `rkaf:emittedBy`, `rkaf:consumer`, `rkaf:verifiedBy`, `rkaf:authorizedBy`, and similar predicates. **Rulespec does not define the shape of an identity.** The identity object — its claims, public keys, attestation levels, revocation state, role grants — belongs to binding implementations: W3C Verifiable Credentials, OIDC subjects, X.509 certificates, Trellis subject ledgers, organization-specific HR/IAM systems. The dependency direction is: bindings know about Rulespec (they emit identities Rulespec can reference); Rulespec does not name any specific identity binding. Partner-level `AuthorityGrant`-style records (user-role grants distinct from content-grounding warrants, see §3) likewise belong to bindings.

**Cryptographic anchoring.** Rulespec assertions and overlays MAY be cryptographically anchored. The framework defines the **abstract anchoring contract** (what an anchor is, what it commits to, how it's referenced from a Rulespec graph). Concrete bindings (Trellis, COSE_Sign1, JWS, W3C Verifiable Credentials, Sigstore, IPFS+IPNS, content-addressed storage) implement the contract.

**The dependency direction is**: bindings know about Rulespec; Rulespec does not know about any specific binding. Trellis's spec describes how Trellis anchors Rulespec; the Rulespec spec does not name Trellis. This is dependency inversion and is the normative posture of the framework.

The abstract anchoring contract requires that any binding implementation:

1. **Defines its anchor type.** A URI identifying the binding (`urn:rkaf:anchor:trellis/1`, `urn:rkaf:anchor:cose-sign1`, etc.).
2. **Defines what the anchor commits to.** A canonical serialization function over the Rulespec subgraph being anchored, such that reanchoring the same subgraph produces a verifiable equality test.
3. **Defines verification.** A function that, given an anchor and the Rulespec subgraph, returns commit/no-commit.
4. **Publishes its specification.** As a separate document outside this framework. Bindings are not part of the Rulespec spec surface.

Rulespec assertions reference anchors via a single property:

```turtle
?assertion rkaf:anchoredBy ?anchorIRI .
?anchorIRI rkaf:anchorType ?anchorTypeURI .
# Remaining anchor structure is binding-defined.
```

Partners MAY use any binding, multiple bindings simultaneously, or no binding. The framework's conformance suite includes one reference binding (selected by the editor team) for fixture purposes, but no binding is privileged at the framework level.

### 4.7 Why this works for AI authoring [Informative]

The architecture's separations specifically support AI substrate-accelerator workflows:

- **Closed Vocabulary taxonomies** mean LLMs producing structured output have unambiguous targets.
- **Constraints compiling to JSON Schema** means LLM tool-use APIs (which consume JSON Schema) get the framework's invariants for free.
- **Projectors with the Derive operation** mean partners can generate prompts from Rulespec profiles for AI extraction.
- **Reference Corpora** (Layer 7) provide LLM training and evaluation data.
- **`rkaf:AILineage`** in Vocabulary captures what the AI did, when, with what model, on whose approval.

These are design choices made deliberately to ensure AI workflows are not second-class, while preserving the §1.5 commitment that AI is accelerator, not authority.

## 5. Layer 1 — Vocabulary

### 5.1 Status

The Vocabulary layer is **partially complete** in Rulespec v0.1.x. Its content lives in `spec/pkaf-core-v0.1.md`, `spec/pkaf-concept-registry-v0.1.2.md`, and `context/pkaf-context-v0.2.jsonld`.

The next Vocabulary release advances Layer 1 by promoting source-fragment, warrant, confidence, and access-scope primitives to first-class status (§5.5–§5.8 below) and by accommodating reference-consumer profiles without becoming any single profile's superset (§5.4).

### 5.2 Editorial discipline [Normative]

The Vocabulary layer maintains the editorial discipline established in Rulespec v0.1.1: **new vocabulary terms enter only when (a) a fixture would fail validation without them, OR (b) generalization of a primitive across multiple reference profiles requires them, OR (c) they are required to support AI-tractable structured output**. Every new term MUST ship with at least one fixture exercising it and at least one fixture that would have passed in its absence and now fails.

A reference consumer's authoring surface MAY produce **candidate promotions** for Vocabulary, but a candidate is promoted only when it generalizes beyond that consumer or is explicitly scoped as a profile-specific refinement. No reference consumer's internal schema is itself a completeness target for the universal Vocabulary.

### 5.3 Closed taxonomies [Normative]

Vocabulary enumerations (`assertionOrigin`, `warrantKind`, `safetyLabel`, `usageEligibility`, etc.) are **closed** within a release. Extension requires a new release with declared URIs. Closed-taxonomy discipline is required for both human-author clarity and LLM-tractable structured output.

### 5.4 Reference-consumer profile parity [Normative]

The next Vocabulary release MUST support all concepts exercised by accepted reference profiles and conformance fixtures. A reference consumer MAY publish a profile whose native schema is derived from Rulespec Vocabulary (depth D3), but **no reference consumer's internal schema is by itself a completeness target for the universal Vocabulary**.

For the WOS Studio (Authoring) reference consumer specifically, profile parity is measured by:

1. **Round-trip parity.** Every conceptual primitive in the Studio profile MUST round-trip losslessly through Rulespec Vocabulary + the JSON Schema projector.
2. **Lint-rule equivalence.** Every Studio lint rule whose semantics generalize beyond Studio MUST be expressible as a Layer 2 constraint over the Rulespec representation. Studio-internal rules remain in the Studio profile.
3. **Compiler-output equivalence.** Studio's compiler emitting from Rulespec-derived schemas MUST produce byte-identical WOS workflow outputs and Formspec form outputs as the v0.1.x compiler emitting from its native schemas, on the SNAP redetermination vertical slice.
4. **LLM-tractability.** Every term MUST be expressible as a closed JSON Schema enum or structured object usable directly by LLM tool-use APIs.

The promotion list in Appendix A enumerates Studio-derived candidates; each candidate is evaluated under §5.2 (does it generalize? or is it Studio-profile-scoped?). Generalizing primitives land in universal Vocabulary; profile-scoped primitives land in the Studio profile under the Rulespec namespace but do not become universal.

### 5.5 Source fragments and evidence binding [Normative]

The Vocabulary layer MUST include `Artifact`, `SourceFragment`, and `EvidenceBinding` as first-class primitives.

- **Artifact** MUST be content-addressable. Implementations MUST use a hash, IPFS CID, persistent URI, ELI URI for legal artifacts, DOI for scholarly works, or other immutable identifier. Citing an Artifact by mutable URL alone is non-conformant. **Rulespec does not reinvent artifact identification — it composes**: ELI for EU legal resources, USLM identifiers for US legal resources, Akoma Ntoso `eId` references for legal-document substructure, DOI for scholarly works, ISBN/ISSN for publications, hash/CID for content-addressed content. The Artifact primitive is the abstract; these are concrete identifier schemes a partner MAY use.
- **SourceFragment** MUST reference an Artifact identifier plus a selector. Selector kinds MUST include the W3C Web Annotation (`oa:`) selector vocabulary as the foundational set: `oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`. Domain-specific selectors compose: Akoma Ntoso `eId` paths for legislation, USLM section identifiers for US legal sources, FRBR-aligned ELI fragment identifiers for EU legal sources, JSONPath for structured data, DOI fragment identifiers for scholarly works. Partner-defined selector kinds are permitted via the §13.4 RFC process.
- **EvidenceBinding** MUST link an Assertion to one or more SourceFragments OR carry an explicit `noEvidenceReason` permitted by the Assertion's safety level. EvidenceBinding carries its own warrant kind (§5.6) and access scope (§5.8).

A Rulespec assertion is **not operationally valid** unless its evidence can be traced to addressable source material or carries an explicit no-evidence category permitted by its safety level. This invariant prevents provenance laundering and is enforced by Layer 2 constraints.

Selector stability across Artifact revisions is a partner obligation. Supersession edges between Artifact versions resolve fragment continuity; consumers traversing a superseded chain MUST surface the chain as part of any operational use of the assertion. For ELI artifacts, ELI-I (legislative impacts and amendments) is the canonical model for fragment-continuity resolution under amendment; Rulespec implementations targeting EU legal sources SHOULD compose ELI-I edges into their supersession traversal.

### 5.6 Warrant as universal grounding primitive [Normative]

The Vocabulary layer MUST include `Warrant` as the universal grounding primitive, with `hasWarrant` as the universal predicate and `warrantKind` as the closed taxonomy of warrant categories.

`Authority` (and `hasAuthority`, `authorityKind`) is preserved as a **specialization of Warrant** for the legal, regulatory, statutory, delegated, organizational, contractual, and publication families. Existing Rulespec Core v0.1 authority-chain content remains valid as the legal-warrant specialization.

The universal `warrantKind` taxonomy includes:

- **Legal family** (inherited from v0.1 `authorityKind`): `legal`, `statutory`, `regulatory`, `delegated`, `organizational`, `contractual`, `localOperational`, `publication`
- **Scientific family** (added): `methodological`, `empirical`, `replication`, `peerReview`
- **Editorial family** (added): `editorial`, `factCheck`, `correction`
- **Cryptographic family** (added): `cryptographic`, `commitment`
- **Social family** (added): `consensus`, `expertOpinion`, `communityEndorsement`
- **Source-class family** (added): `sourceReliability`, `provenanceClass`

A warrant chain is hop-local (each hop carries its own warrantKind) and may transition between families (e.g., `editorial → methodological → empirical` in a scientific chain; `regulatory → delegated → statutory` in a legal chain). Cross-family transitions are permitted; consumers traversing them MUST surface the family transition for human review.

This generalization is the unlock for the universal-domain framing. A scientific claim is *warranted by* its method section, not derived from its authority. A journalism citation is *warranted by* its sources and editorial process. An audit finding is *warranted by* its sampling methodology and evidence inspection. The framework MUST express all of these without forcing them into the legal-authority idiom.

**Alignment with existing ontologies.** The Warrant model composes deliberately with three mature public ontologies, importing rather than duplicating:

- **Legal warrants align with LegalRuleML.** OASIS LegalRuleML is the canonical formal-rule ontology for legal norms with defeasibility, deontic operators, exceptions, temporality, jurisdiction, and authorial tracking. Rulespec's legal-family warrants (`statutory`/`regulatory`/`delegated`/etc.) compose with LegalRuleML's deontic primitives. The `defeasible: boolean` field is preserved for LegalRuleML interop. Rulespec does not require LegalRuleML for ingestion (formal rule encoding is a downstream activity); when partners produce formal legal rules, they emit LegalRuleML and link via `hasWarrant`.
- **Reporting-requirement warrants align with RRMV.** The EU Reporting Requirement Metadata Vocabulary models reporting requirements within legal provisions — who reports what, due dates, change tracking, requirement-to-artifact association. This maps directly onto the warrant chain for assertions of the form "this artifact is required by this reporting provision under this legal authority." Rulespec implementations targeting reporting-requirement domains SHOULD use RRMV's vocabulary for the requirement-to-source link, with `hasWarrant` connecting the requirement to its statutory or regulatory grounding.
- **Scientific warrants align with ECO and SEPIO.** The Evidence & Conclusion Ontology and the Scientific Evidence and Provenance Information Ontology are mature published ontologies for scientific evidence types and assertion methods. Rulespec's `methodological`, `empirical`, `replication`, and `peerReview` warrant kinds align with ECO's evidence type vocabulary; partners producing scientific assertions SHOULD reference ECO terms as the warrant-kind specialization within the scientific family.

§5.9 enumerates these alignment relationships normatively.

### 5.7 ConfidenceRecord [Normative]

The Vocabulary layer MUST include `ConfidenceRecord` as a first-class primitive (promoted from prior Studio-derived appendix status).

A ConfidenceRecord MUST distinguish:

- **method** — how the confidence was computed (model inference, human estimation, review consensus, source-class inheritance, etc.)
- **score** — the numeric or categorical confidence value
- **calibrationStatus** — `uncalibrated` / `calibratedAgainst` (with reference) / `humanEstimated` / `consensus`
- **basis** — what evidence the confidence is grounded in
- **evaluatedAgainst** — the corpus or fixture set against which calibration was measured (if any)
- **generatedBy** — the actor that produced the record (model + version + prompt template ref, or human identity, or community process)

The framework explicitly forbids "score theater" — confidence values without method, basis, and calibration status. Implementations MUST distinguish uncalibrated model score, calibrated model score, human confidence, review consensus, and source reliability as separate confidence kinds even when they coexist on the same assertion.

### 5.8 AccessScope [Normative]

The Vocabulary layer MUST include `AccessScope` as a first-class primitive attachable to Assertions, Attestations, EvidenceBindings, and SourceFragments.

AccessScope encodes that an artifact's existence, content, or warrant chain is visible only to a declared audience. Use cases include:

- **Public assertion, private evidence.** A medical claim is publishable; the patient record grounding it is not.
- **Public-safe redaction.** An assertion's text is publishable; specific named entities or quantities are redacted.
- **Organization-visible attestation.** An attestation is internal to an organization; the underlying assertion is public.
- **Restricted source fragment.** A source fragment exists in a classified or confidential document; the fact of citation is disclosable but the fragment content is not.
- **Privileged local adoption.** A local adoption decision is privileged (legal/medical/strategic); the adoption status is not externally visible.

AccessScope kinds: `public`, `partnerVisible`, `organizationVisible`, `roleRestricted`, `personalRestricted`, `regulatoryRestricted` (HIPAA/PHI/PII/classified/legally-privileged), `embargoUntil` (time-bounded).

Consumers MUST preserve AccessScope through retrieval, projection, summarization, federation, and AI-assisted consumption. A consumer that exposes content beyond its declared AccessScope is non-conformant. Layer 2 constraints enforce AccessScope honoring at validation time; the AI-accelerator commitment in §1.5.6 enforces it at consumption time.

AccessScope's vocabulary is informed by **W3C ODRL** (permission/prohibition/duty modeling) and **W3C DPV** (privacy semantics for `regulatoryRestricted` HIPAA/PHI/PII cases). Rulespec does not import ODRL or DPV directly; it aligns predicate names where possible and supports an ODRL or DPV overlay attached to the same artifact via the projector pattern (§8). Partners with strong rights-expression or privacy-classification needs SHOULD attach an ODRL or DPV overlay alongside the Rulespec overlay rather than encoding rights/privacy semantics inline in Rulespec.

### 5.9 Public ontology imports and alignments [Normative]

Rulespec composes deliberately with the existing public-ontology ecosystem. Three relationship modes are defined: **import** (the ontology is a code-level dependency in the JSON-LD context and SHACL shapes), **align** (Rulespec predicate names mirror the ontology's where they overlap, and an overlay-pattern integration is supported), and **project** (the ontology is a partner-side carrier format reached via the §8 projector layer).

#### Imports — direct dependencies

| Ontology | Prefix | Role |
|---|---|---|
| **W3C PROV-O** | `prov:` | Provenance vocabulary. `prov:wasDerivedFrom` chains compose with cryptographic anchoring (§4.6) and AI lineage records (§5.7). |
| **W3C Web Annotation Ontology (OA)** | `oa:` | Selector vocabulary for `SourceFragment` (§5.5). Foundational selector kinds (`oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`) MUST be supported by every Rulespec implementation handling source fragments. |
| **W3C SKOS** | `skos:` | Concept relations (`closeMatch`, `exactMatch`, `broader`, `narrower`, `related`) for the Concept Registry (§7.1.2). |
| **JSON-LD 1.1** | (carrier) | Primary serialization. Layer 4 projector target. |
| **SHACL** | `sh:` | One Layer 2 compilation target (demoted from authoritative; see Appendix C). |
| **RDF / RDFS / XSD** | `rdf:` / `rdfs:` / `xsd:` | Base graph model and typed literals. Implicit in any RDF-shaped substrate. |

#### Alignments — predicate-name and pattern compatibility

| Ontology | Domain | Alignment posture |
|---|---|---|
| **ELI** (European Legislation Identifier) | EU legal-resource identifiers + metadata | Use ELI URIs as the canonical Artifact identifier scheme for EU legal sources (§5.5). Do not duplicate ELI's URI structure or metadata model; compose. |
| **ELI-DL** | Draft legislation | Compose ELI-DL identifiers + metadata for assertions over draft/pending legislation. Lifecycle packets carry ELI-DL state transitions natively. |
| **ELI-I** (Legal Impacts) | Legislative impacts and amendments | Canonical model for fragment-continuity resolution under amendment in EU legal sources. Rulespec implementations targeting EU legal sources SHOULD compose ELI-I edges into supersession traversal (§5.5). |
| **RRMV** (Reporting Requirement Metadata Vocabulary) | Reporting requirements in legal provisions | Align warrant chains for reporting-requirement assertions with RRMV's vocabulary (§5.6). RRMV's "who reports what / due dates / change tracking / requirement-to-artifact association" use cases map directly onto Rulespec assertions over reporting obligations. |
| **Akoma Ntoso / LegalDocML** | Legal-document XML structure | Use Akoma Ntoso `eId` paths as a SourceFragment selector kind for legislative source-document substructure (§5.5). |
| **USLM** (United States Legislative Markup) | US legislative XML structure | Use USLM section identifiers as a SourceFragment selector kind for US legal sources (§5.5). |
| **OASIS LegalRuleML** | Formal legal norms (defeasibility, deontic) | Align legal-family warrants (§5.6); preserve `defeasible: boolean` for interop. Partners producing formal legal rules emit LegalRuleML and link via `hasWarrant`. |
| **ECO** (Evidence & Conclusion Ontology) / **SEPIO** | Scientific evidence types | Align the scientific-warrant family (`methodological`/`empirical`/`replication`/`peerReview`) with ECO's evidence type vocabulary (§5.6). |
| **Nanopublications** | Portable assertion + provenance + publication-info graphs | Align the overlay-attachment pattern (§4.3) with nanopublication shape: assertion graph + provenance graph + publication-info graph. A Rulespec overlay is structurally a generalized nanopublication carrying domain-specific warrant chains. |
| **W3C ODRL** | Rights/permission expression | Align AccessScope (§5.8) predicate names with ODRL where they overlap; partners requiring full rights expression attach ODRL overlays via the projector. |
| **W3C DPV** | Privacy semantics | Align AccessScope `regulatoryRestricted` cases (§5.8) with DPV's privacy/personal-data/legal-basis vocabulary; partners requiring full privacy classification attach DPV overlays. |
| **DCTERMS** (Dublin Core) | Generic metadata + supersession (`dcterms:replaces`) | Align supersession predicates with `dcterms:replaces` / `dcterms:isReplacedBy` for generic-metadata interop. |
| **CiTO** (Citation Typing Ontology) | Scholarly citation typing (`supports` / `disagreesWith` / `extends`) | Align scholarly-warrant relations within the editorial/scientific warrant families. |
| **Schema.org / Schema.org/Legislation** | Public web markup | Align an export projection for SEO-grade public publication of assertions and source artifacts. Public-discovery layer only; not the operating model. |
| **DCAT / VoID** | Dataset catalog / linked-data discovery | Align the Reference Corpora layer (§11) for dataset publication. Rulespec corpora SHOULD ship with DCAT-compatible metadata. |

#### Projections — partner-side carrier formats reached via Layer 4

| Ontology / Format | Partner audience | Projector status |
|---|---|---|
| **JSON Schema** | Programmer-facing tooling, IDE, AI tool-use APIs | MVP (§8.2) |
| **JSON-LD** | Linked-data partners | MVP (§8.2) |
| **OpenAPI 3.1** | API-surface partners | MVP (§8.2) |
| **HL7 FHIR** | Healthcare-domain partners | Available when partner needs (§8.3) |
| **NIEM IEPDs** | US government data exchange | Available when partner needs (§8.3) |
| **Schema.org/Legislation** | Public discovery / SEO | Available when partner needs |
| GraphQL SDL, Protobuf, Avro, Iceberg, Cedar/Rego | Various | Available when partner needs |

#### Reference / influence — studied but not imported, aligned, or projected

| Source | Why studied |
|---|---|
| **Lynx Legal Knowledge Graph (H2020)** | Closest "legal knowledge graph" prior art for compliance-document modeling. |
| **LKIF** (Legal Knowledge Interchange Format) | Earlier legal knowledge ontology family; useful prior art. |
| **EuroVoc / ESCO** | Examples of large public SKOS concept registries; usable as ConceptRegistry seed data for EU policy / workforce domains. |
| **Toulmin Argumentation Schema / AIF** | Conceptual ancestor for the Warrant model; not deployed widely enough to import. |
| **Wikidata / Wikibase statements with qualifiers + references** | Conceptual ancestor for "claims with scoped qualifiers and references"; pattern influences Assertion + Attestation modeling. |
| **EU Common Data Model / CDM** | EU-institution-specific document/procedure metadata; too institution-specific to import. |
| **EU eProcurement Ontology (ePO)** | Domain-specific procurement ontology; potential projector target if procurement becomes a reference domain. |
| **OCDS** | Open contracting transparency; potential projector target. |

#### Discipline

The composition discipline is: **do not reinvent**. If a public ontology owns the local problem (ELI for EU legal-resource identity, USLM for US legal source structure, RRMV for reporting requirements, ECO for scientific evidence, OA for selectors), Rulespec uses it. Rulespec's Vocabulary expresses what is genuinely missing — the universal warrant model, the federation contract, the consumer-overlay pattern, the depth gradient, the cross-domain conformance suite. Everything else composes.

## 6. Layer 2 — Constraints

### 6.1 Source of truth [Normative]

Constraints on Rulespec data graphs MUST have a single source of truth. The source MUST be a tooling-neutral language compilable to multiple targets. SHACL, JSON Schema, Rust, and any other validator format are **compilation targets**, not the source of truth.

Selection criteria for the constraint source language:

1. **Decidable evaluation.** No silent-pass failure modes of the class observed in pySHACL conditional shapes (Appendix C).
2. **Cross-property and cross-document expression.** Constraints frequently span multiple assertions and documents.
3. **Compilable to SHACL, JSON Schema, Rust, TypeScript, CUE, Rego.** No single target may be missing.
4. **Auditable test coverage.** Every constraint MUST have a positive fixture, at least one negative fixture, and a parity assertion across all compilation targets.

### 6.2 Candidate languages [Informative]

Candidates under evaluation: Rulespec Constraint DSL (greenfield), CUE, SPARQL ASK queries, Datalog, Cedar. Selection is open and documented in a future ADR. This document does not pre-commit.

### 6.3 Compilation target obligations [Normative]

For every constraint released at the source level, the framework MUST publish compilations for at least:

1. **JSON Schema (Draft 2020-12)** — load-bearing for depth-D3 reference consumers and for LLM tool-use APIs
2. **Rust validator code** — for performance-critical embeddings
3. **TypeScript validator code** — for browser/edge embeddings

Additional targets (SHACL, CUE, Rego, OPA, Cedar) MAY be published. SHACL specifically is **demoted** from authoritative status (Appendix C).

### 6.4 Test corpus [Normative]

The constraint test corpus MUST include parity fixtures, adversarial fixtures (designed to surface evaluator-class failures), and cross-target divergence fixtures (designed to expose target-language semantic gaps).

## 7. Layer 3 — Registries

### 7.1 Registry kinds [Normative]

Three registries are normative:

1. **Source Authority Registry** — classifies SourceDocuments by authority class, jurisdiction, issuing body, effective range, supersession edges, freshness signal.
2. **Concept Registry** — canonical concepts, mappings, applicability contexts, lifecycle packets, conflict resolution.
3. **Bridge Contract Registry** — declared Rulespec versions implemented by named partners, with declared adoption depth.

### 7.2 Identity resolution [Normative]

Registries provide identity resolution against IRI-typed and workspace-prefixed identifiers:

- **Globally addressable IRIs** (`https://rulespec.org/ns/v1#`, `https://rulespec.example.org/...`)
- **Workspace-prefixed identifiers** (`urn:rkaf:workspace:<workspaceId>/<localId>`)

Workspace-prefixed identifiers are resolvable within their declaring workspace and federable across workspaces declaring mutual trust.

### 7.3 Federation [Normative]

The federation thesis (§1.3) is structurally dependent on registry federation. The framework's federation contract:

1. **Pull-based resolution.** Partner A may resolve an identifier issued by Partner B by querying B's registry endpoint directly.
2. **Push-based subscription.** Partner A may subscribe to lifecycle events on a class of identifiers in Partner B's registry.
3. **Mirror operation.** Partner A may operate a read-only mirror of Partner B's registry for performance or availability.
4. **Trust declaration.** Each partner publishes a list of partner registries it trusts for resolution, with trust scope.
5. **Disagreement resolution.** When two trusted partners' registries disagree, the protocol specifies precedence and disclosure obligation.

Detailed protocol document published as a Phase-3 deliverable per §16.

### 7.4 Reference instances [Normative]

The framework will host public reference instances of all three registries. Reference instances are operated as **public goods**, peer to other partner-operated instances rather than central authorities. Self-hosting MUST be supported and documented.

## 8. Layer 4 — Projectors

### 8.1 Projector contract [Normative]

A Projector is a bidirectional adapter between Rulespec Vocabulary and a target schema format. A conformant Projector implementation MUST provide:

1. **Attach.** Embed a Rulespec overlay into a native artifact per the target's carrier convention.
2. **Extract.** Recover the original native artifact and the embedded Rulespec overlay separately, lossless within the framework contract.
3. **Validate.** Validate that the overlay is well-formed per Layer 2 constraints and grounded per Layer 1 vocabulary.
4. **Round-trip parity.** Attach-then-extract MUST be the identity transform.
5. **Derive (depth-D3 obligation).** Given a Rulespec Vocabulary subset (a partner profile) and a target format selection, generate a native schema in the target format that expresses the profile's content.

The Derive operation makes depth-D3 partner adoption practical without requiring partners to write derivation pipelines themselves.

### 8.2 Initial projector set [Normative]

The MVP projector set:

1. **JSON Schema (Draft 2020-12)** — load-bearing for the WOS Studio reference consumer (depth D3) and for LLM tool-use APIs.
2. **JSON-LD** — overlay carried natively in the JSON-LD graph.
3. **OpenAPI 3.1** — overlay carried in `x-rkaf` extensions on operations and components.

These three cover ~80% of the working policy-data interop surface.

### 8.3 Subsequent projector set [Informative]

Targets planned for future releases: GraphQL SDL, Protocol Buffers, FHIR profiles (R4 and R5), NIEM IEPDs, CUE, Rego / Cedar policy attachments, Apache Avro / Iceberg metadata. Each requires a published carrier convention, a working bidirectional implementation including Derive, round-trip parity fixtures, and at least one declared adopting partner.

### 8.4 Carrier convention discipline [Normative]

Carrier conventions per target MUST minimize collision with the target's existing extension mechanisms. Where a target defines an extension namespace, Projectors MUST use that mechanism. Where a target does not, Projectors MUST publish their carrier convention as a versioned subordinate document.

### 8.5 Schema-as-projection pattern [Normative]

A partner adopting at depth D3 commits to operating its native schemas as **projections** of Rulespec Vocabulary rather than as independent artifacts:

1. The partner publishes a **profile** — a subset of Rulespec Vocabulary plus partner-specific refinements — through the §13.4 RFC process.
2. The partner runs the §8.1.5 Derive operation on its profile against a target format.
3. The generated native schema is published alongside the profile as a derived artifact, with the profile as source of truth.
4. The partner's authoring tools, codegen, IDE integration, and AI-extraction services consume the derived schema with no awareness that it came from Rulespec Vocabulary.
5. The partner's compiler emits Rulespec overlays directly from the profile.

This pattern lets a partner retain the full ergonomics of native-schema tooling while binding its conceptual surface to Rulespec.

## 9. Layer 5 — SDKs

### 9.1 Reference SDK languages [Normative]

The reference SDKs:

1. **Rust** — substrate SDK; load-bearing for performance and embedding.
2. **TypeScript** — browser/edge/Node SDK.
3. **Python** — research/data-science SDK; inheritor of the existing v0.1.1 tooling line.

Each SDK MUST implement Vocabulary, Constraints, Registries (client + federation participation), and Projectors. Each SDK MUST pass the §10 conformance fixture suite at L2 or higher.

### 9.2 SDK API parity [Normative]

The three reference SDKs MUST expose APIs of equivalent shape: same operations, same conceptual surface, same fixture conformance. Language-idiomatic adaptation is permitted; semantic divergence is not.

### 9.3 SDK release gates [Normative]

An SDK release MUST NOT publish if any fixture fails, cross-SDK parity assertions fail, constraint compilation targets diverge from canonical targets at the bundled framework version, or federation-protocol participation tests fail against at least one peer SDK.

### 9.4 Embedding SDKs [Informative]

Partners integrate Rulespec via SDK embedding. WOS Studio embeds the Rust SDK in its compiler and lint engine; case-portal embeds the TypeScript SDK; AI extraction services embed the Python SDK.

## 10. Layer 6 — Conformance

### 10.1 Conformance suite [Normative]

The framework publishes a public conformance fixture suite. The suite MUST include:

- Every Vocabulary class exercised by at least three fixtures (positive, negative, edge)
- Every constraint exercised by at least one positive and one negative fixture
- Every Projector exercised through round-trip parity AND Derive operation on every applicable Vocabulary class
- Every registry-resolution path exercised by at least one fixture
- Federation protocol exercised by at least three fixtures (pull, push, disagreement-resolution)
- At least five **adversarial fixtures** designed to surface evaluator-class failures
- At least three **AI-extraction adversarial fixtures** surfacing LLM systematic-misinterpretation patterns

### 10.2 Conformance levels [Normative]

Four conformance levels. **Conformance level is orthogonal to adoption depth (§4.5).** A partner declares both: a depth (what it commits to) and a level (what its read-side guarantees deliver).

| Level | Name | Scope |
|---|---|---|
| **L1** | Validate | Implementation reads Rulespec overlays and validates them per Layer 2 constraints. |
| **L2** | Project | L1 + implementation projects Rulespec overlays to/from at least one declared target format (Attach + Extract). |
| **L3** | Cascade | L2 + implementation correctly computes lifecycle cascade closure (CascadeClosureV1; Rulespec Core §5) and `usageEligibility` reducer output. |
| **L4** | Federation | L3 + implementation participates in registry federation. |

### 10.3 Self-certification [Normative]

A partner declaring conformance MUST publish:

1. The Rulespec version
2. The declared **adoption depth** (D1-D5)
3. The declared **conformance level** (L1-L4)
4. The fixture-suite version exercised
5. A public test report demonstrating fixture pass

The Bridge Contract Registry indexes declared-conformant partners by depth, level, and version.

### 10.4 Why consumer-declared and not tool-declared [Informative]

Authoring-tool conformance is a weak signal; consumer conformance is the actual interop test. The federation flywheel relies on consumer claims being verifiable and citable.

## 11. Layer 7 — Reference Corpora

### 11.1 Purpose [Normative]

Reference Corpora are public Rulespec-typed datasets shipped with the framework. They serve four functions:

1. **Worked examples.** Demonstrate Rulespec in use across multiple domains.
2. **Adoption infrastructure.** New partners can build against real Rulespec-typed data immediately, without needing to produce their own first.
3. **AI training and evaluation.** LLMs targeting structured Rulespec output need labeled training data; reference corpora provide it.
4. **Conformance-suite extension.** Real-world data exercises edge cases synthetic fixtures miss.

### 11.2 Initial corpus [Normative]

The initial Reference Corpus is the **SNAP redetermination vertical slice** from `policy-studio/examples/snap-redetermination-from-sources/`. The slice is a width-one path through every framework layer for one real-world policy domain (federal benefits redetermination).

### 11.3 Subsequent corpora [Informative]

Planned corpora across diverse domains, each composing existing public ontologies (per §5.9) for source identity and structure:

- **EU regulatory text** — selected EU regulations and directives with **ELI URIs** as Artifact identifiers, **Akoma Ntoso** `eId` paths as SourceFragment selectors, **ELI-I** edges for amendment supersession, **RRMV** for any embedded reporting requirements, Rulespec warrant chains over the legal-family.
- **US federal regulatory text** — selected CFR titles with **USLM** identifiers as Artifact identifiers, USLM section identifiers as SourceFragment selectors, Rulespec warrant chains over the legal-family.
- **State benefits policy manuals** — selected state manuals (anchoring on the existing SNAP slice methodology) with content-addressed Artifacts, structured-section selectors, Rulespec warrant chains.
- **Scientific reproducibility** — selected reproducible-research papers with **DOI** Artifact identifiers, **ECO/SEPIO** evidence-typed warrants, Rulespec scientific-warrant family chains over `methodological`/`empirical`/`replication`/`peerReview`.
- **Journalism citation** — selected investigative journalism pieces with claim → cited-source warrant chains over the editorial/expertOpinion/sourceReliability families.
- **Contracting transparency** — selected procurement records (potentially aligning with **OCDS** or **EU eProcurement Ontology**) with authority chains and supersession.
- **Audit trails** — selected compliance audit traces with lifecycle and adoption events.
- **AI training-data provenance** — selected dataset-lineage records with content-addressed Artifacts, AI lineage records (§5.7), and warrant chains over data sources.

Each corpus composes existing public ontologies for source identity and structure — Rulespec adds the warrant chain, eligibility, lifecycle, and consumer-overlay layer on top. Partner contributions are incorporated through the §13.4 RFC process.

### 11.4 Corpus discipline [Normative]

A Reference Corpus MUST:

1. Validate cleanly against the conformance fixture suite at the declared Rulespec version.
2. Carry a license permitting redistribution and use for AI training.
3. Document its source provenance — what real-world artifacts were tagged, by whom, with what authority.
4. Be reproducible — the tagging methodology MUST be documented so others can replicate the corpus on adjacent source materials.
5. Use existing public-ontology identifier schemes (ELI / USLM / DOI / Akoma Ntoso / etc.) for source identity and structure where they exist; do not mint Rulespec-internal identifiers for sources that already have public canonical identifiers.
6. Ship with **DCAT-compatible metadata** so the corpus is discoverable in standard linked-data catalogs.

## 12. Versioning

### 12.1 Pre-release posture [Normative]

Rulespec is **pre-release**. Breaking changes are expected and signaled via CHANGELOG. The framework does not yet make semver-style stability commitments.

The framework operates with a single version axis (`rkaf/0.x`) until structural stability supports splitting into independent payload-semantics and framework-structure versions. The split is reserved for a post-1.0 evolution; this document does not pre-commit to it.

Artifacts MUST pin the Rulespec version they target. Partners MUST publish a migration note when they adopt a new version. CHANGELOG-driven breakage signaling is the only ceremony pre-1.0.

### 12.2 Post-1.0 [Informative]

Once adoption signal supports stability commitments (multiple external partners depending on a stable contract), the framework transitions to semver with a published deprecation policy. The mechanics are deferred until that signal exists; pre-defining ceremony for a stability we don't yet have is wasted motion.

## 13. Governance

### 13.1 The single-vendor problem [Normative]

A public federation substrate with a single-vendor editor will not achieve broad adoption. The framework's federation thesis depends on perceived neutrality.

### 13.2 Pre-launch posture [Normative]

The framework currently operates under formspec-stack maintainership with the single-vendor problem acknowledged. The pre-launch posture:

- All editorial decisions are made publicly with rationale published.
- All Vocabulary additions, constraint additions, projector additions, and conformance-fixture additions go through a public RFC process with a minimum 30-day comment period.
- External contributor PRs are reviewed and merged on technical merit, not institutional affiliation.
- A `CODEOWNERS` file in the public repo identifies the current editorial team transparently.

### 13.3 Governance shell [Informative]

A move to a neutral governance shell (W3C Community Group, OASIS Technical Committee, or independent foundation) becomes appropriate once **adoption signal supports the move** — typically after multiple external partners are depending on the framework. Pre-launch shell selection is wasted motion: foundations take months to spin up, the framework needs partners now, and partners care more about working code than about governance optics.

When adoption signal arrives, the framework migrates. The mechanics of that migration are not defined here; the commitment is that migration happens.

### 13.4 RFC process [Normative]

Vocabulary additions, constraint additions, projector additions, and conformance-fixture additions MUST proceed through a public RFC process with:

1. Public draft publication
2. A minimum 30-day public comment period
3. A published disposition of comments
4. Editor consensus on inclusion

Implementation experience reports from at least two independent partners are REQUIRED before a Vocabulary or Constraint addition advances to ratified status.

### 13.5 Partner participation [Normative]

Partners declaring conformance gain:

1. **Voice.** Public comment on RFCs; partner objections recorded in the disposition document.
2. **Implementation experience reporting.** A partner's experience counts toward the §13.4 two-implementation requirement.
3. **Profile publication.** Partners may publish profiles under the framework's namespace.
4. **Federation participation.** Partners participate in registry federation per §7.

Partners do not gain editorial authority unless they hold an editor seat. Partner influence operates through voice, experience reporting, and profile publication.

## 14. Reference consumer pattern

### 14.1 First reference consumer [Normative]

WOS Studio (Authoring) — `policy-studio/` in the formspec-stack — is the first reference consumer. Studio's commitment is **depth D3 (Derive)** with planned migration to D4 (Substrate) over subsequent releases.

Studio's specific commitments:

1. **Vocabulary alignment (D2 floor).** Studio's Rust types align name-for-name with Rulespec Vocabulary classes. Studio's enum values match Rulespec closed taxonomies exactly. Studio's `authorityClass` collapses into Rulespec's `authorityKind` (the legal/regulatory specialization of universal `warrantKind` per §5.6). Studio's one-to-one `supersededBy` widens to many-to-many `rkaf:supersedesAssertion`. Studio's `automationEligibility` three-state enum maps onto Rulespec's `usageEligibility` lattice. Studio's source-document references migrate to `rkaf:Artifact` + `rkaf:SourceFragment` per §5.5; Studio's confidence shapes consume the Layer 1 `rkaf:ConfidenceRecord` per §5.7; Studio's visibility metadata adopts `rkaf:AccessScope` per §5.8.
2. **Schema derivation (D3 commitment).** Studio's 19 native JSON Schemas become outputs of the Layer 4 JSON Schema projector applied to the Studio profile. The profile is the source of truth; the schemas are derived artifacts. IDE tooling, codegen, AI-extraction `x-lm` annotations (renamed `rkaf:llmHint`), and authoring ergonomics are preserved.
3. **Overlay emission.** Studio's compiler emits Rulespec overlays on every artifact at every emission boundary. The overlay carries the full Rulespec surface: source fragments + artifacts, warrant chain (legal-family or otherwise), eligibility lattice, applicability scope, access scope, lifecycle packet, AI lineage, confidence records, supersession edges, attestations.
4. **Lint integration.** Studio's lint engine adds a tier of "overlay grounded" rules sourced from Rulespec Layer 2 constraints.
5. **Conformance L3 minimum** with target L4.
6. **Public worked example.** The SNAP redetermination vertical slice is published as the Reference Corpus (§11.2) and as the depth-D3 worked example.

### 14.2 Reference consumer obligations [Normative]

A reference consumer MUST declare its conformance level and adoption depth publicly, pass the §10 fixture suite at the declared level, publish implementation experience reports for each Rulespec release cycle, provide source code for the integration as a worked example, and participate in registry federation at L4 once L4 conformance is demonstrated.

### 14.3 Substrate independence [Normative]

The framework MUST NOT require any future reference consumer to adopt at depth D3 or above; future reference consumers may anchor at any conformant depth. Studio's depth-D3 commitment is a *Studio* commitment, not a framework requirement.

### 14.4 Studio depth-D3 work program [Informative]

Studio's depth-D3 commitment requires:

- The §5.4 Vocabulary completeness target is met.
- The JSON Schema projector's Derive operation produces ergonomic schemas equivalent to Studio's hand-written schemas.
- The Studio profile is published as a subordinate document under the Rulespec namespace.
- Studio's compiler is rewired to consume the derived schemas instead of the hand-written schemas; byte-identical SNAP-slice output gates the cutover.
- The studio-derived primitives in Appendix A land in Rulespec Vocabulary.

The cutover preserves all existing Studio capabilities. Nothing in Studio's existing surface goes away; the conceptual ground beneath it shifts from independent-Studio-vocabulary to derived-from-Rulespec-vocabulary.

## 15. Federation flywheel

### 15.1 The flywheel [Informative]

Four reinforcing loops:

1. **Marginal integration cost.** Each new partner reduces the marginal cost of the next: more registry content reduces bootstrapping work, more projector targets cover the new partner's existing format, more reference consumers demonstrate adoption patterns adjacent to the new partner's domain.
2. **Registry value.** Each partner contributing source-authority classifications, concept mappings, and bridge-contract declarations increases registry value to all other partners.
3. **Governance neutrality.** Each external partner participating in the §13.4 RFC process strengthens perceived neutrality, lowering the adoption barrier for the next partner.
4. **Conformance leverage.** Each L3+ consumer creates downstream pressure on its upstream authoring tools to emit conformant Rulespec.

### 15.2 Partner roles [Normative]

| Role | Description | Typical depth |
|---|---|---|
| **Authoring partner** | Tools that emit Rulespec overlays on artifacts they produce | D1-D3 |
| **Consumer partner** | Systems that read Rulespec overlays and act on them | D1-D5 |
| **Registry operator** | Hosts a federable registry instance | N/A — orthogonal |
| **Projector partner** | Implements a projector for a target format | D2-D3 |
| **Binding partner** | Implements an anchoring binding (Trellis, COSE, VC, etc.) per §4.6 | N/A — orthogonal |
| **Corpus contributor** | Publishes a Reference Corpus per §11 | N/A — orthogonal |

### 15.3 Partner onboarding [Normative]

A new partner joins by:

1. Declaring conformance per §10.3.
2. Registering its conformance declaration with the Bridge Contract Registry.
3. Declaring its registry trust list per §7.3.
4. Optionally publishing a profile per §8.5 if adopting at depth D3 or above.
5. Optionally accepting partner-participation rights per §13.5.

There is no application process and no editor approval required for partner entry. The framework's posture is **open enrollment with disclosure**. Editor approval is required only for promotion to reference-consumer status (§14) or editor-team membership.

See Appendix E for the partner onboarding template.

### 15.4 Anti-fragmentation discipline [Normative]

The framework explicitly works to prevent partner fragmentation:

- **Profile registration.** Partner profiles MUST be published in the framework namespace; private profiles do not benefit from federation.
- **Profile compatibility.** A partner's profile MUST be a *subset and refinement* of Rulespec Vocabulary, never an extension that bypasses Vocabulary terms. Extensions land through the §13.4 RFC process.
- **Registry trust transparency.** A partner declaring trust in another partner's registry MUST disclose the trust relationship publicly.
- **Conformance honest reporting.** False conformance declarations are grounds for removal from the Bridge Contract Registry.

## 16. Sequencing

### 16.1 Sequence [Informative]

Ship-then-recruit-then-govern. Phases gate on the prior phase's deliverable acceptance, not on calendar dates.

**Phase 1 — Vocabulary completeness + constraint source selection.**
- Studio-derived primitive promotions land in Vocabulary (Appendix A)
- §5.4 completeness target met against the SNAP slice
- Constraint source language selected; reference compilation pipeline producing the three required Layer 2 targets
- Constraint test corpus reaching parity across targets
- AI-tractability discipline applied to all new Vocabulary terms

**Phase 2 — MVP projector triangle with Derive operation.**
- Rulespec ↔ JSON Schema, Rulespec ↔ JSON-LD, Rulespec ↔ OpenAPI projectors at L2 conformance
- All three projectors implement the §8.1.5 Derive operation
- Round-trip parity fixtures published
- Carrier convention documents published per target

**Phase 3 — Reference SDKs + federation protocol + anchoring contract.**
- Rust, TypeScript, Python SDKs at L2 conformance with cross-SDK parity verified
- Federation protocol document published
- Federation participation tests pass across SDKs
- Abstract anchoring contract (§4.6) finalized
- At least one binding implementation published as a worked example (the binding lives in its own repo)

**Phase 4 — Reference registries + initial Reference Corpus.**
- Hosted reference instances of Source Authority, Concept, Bridge Contract registries
- Self-hosting documentation
- Federation between reference instances and at least one self-hosted instance demonstrated
- SNAP slice published as the initial Reference Corpus per §11.2

**Phase 5 — Reference consumer (WOS Studio) cutover.**
- Studio profile published as subordinate document
- Studio compiler rewired to consume derived schemas
- SNAP slice byte-identical output verified across cutover
- Studio declared conformance L3 + depth D3
- Studio's overlay-emission integration published as worked example

**Phase 6 — Public release + repo extraction.**
- Rulespec extracted to its own public repo under the formspec organization
- Submoduled back into formspec-stack
- Release manifest publishing all seven layers
- Public CHANGELOG initialized
- SDKs published to language registries (crates.io, npm, PyPI)

**Phase 7 — Partner recruitment (post-launch).**
- Outreach to potential partners across adjacent domains (healthcare, civic-tech, contracting transparency, scientific reproducibility, AI provenance)
- Partner onboarding via §15.3 open enrollment
- Implementation experience reports inform the next Vocabulary release

**Phase 8 — Governance shell migration (post-adoption-signal).**
- Once adoption signal supports it (multiple external partners actively depending on Rulespec), select a neutral governance shell per §13.3
- Migrate editorial responsibility
- Recruit external editors per the shell's process

### 16.2 Phase ordering rationale [Informative]

Ship working tools before demanding partner commitments. Ship public release before recruiting partners. Recruit partners before migrating governance. This is the inverse of the conventional standards-body sequencing and is the right order for federations whose adoption depends on tooling, not credentials. Kubernetes, OpenAPI, terraform, Sigstore — all shipped first, recruited later, governed last.

### 16.3 Risks [Informative]

- **Vocabulary completeness slippage.** Mitigation: byte-identical SNAP-slice output is a hard gate; no Phase 5 cutover until it passes.
- **Projector quality.** The Derive operation must produce ergonomic schemas; ugly derived schemas kill depth-D3 adoption. Mitigation: Studio team participates in projector design; ergonomic-equivalence is a release gate.
- **Federation protocol underspecification.** Mitigation: protocol exercised against multiple SDKs in Phase 3 before publication.
- **Carrier-convention collisions.** Mitigation: carrier-convention documents explicitly enumerate collision risk per target.
- **W3C-tooling adjacency drag.** Rulespec inherits IRI / JSON-LD / PROV vocabulary. Mitigation: §6 demotes SHACL to one of many compilation targets; the framework's tooling commitments do not require any particular semantic-web evaluator.
- **AI vocabulary drift.** LLMs may systematically misinterpret some Vocabulary terms. Mitigation: AI-extraction adversarial fixtures in §10.1; iterative term refinement based on misinterpretation patterns.

---

## Appendix A — Studio-derived primitive promotions

[Normative — completion is a §5.4 prerequisite for the next Vocabulary release.]

Primitives currently defined in WOS Studio (Authoring) schemas slated for promotion into Rulespec Vocabulary. Once promoted, they become first-class Vocabulary classes available to all partners.

| Studio primitive | Rulespec promotion | Source |
|---|---|---|
| Four-state mapping taxonomy (`mapsToWos` / `authoringOnly` / `requiresSpecExtension` / `unmappedButApproved`) | `rkaf:MappingState` — closed enum, four values | `policy-studio/schemas/wos-studio-mapping.schema.json` |
| `RetentionPolicy` typed shape | `rkaf:RetentionPolicy` — first-class Vocabulary class | `policy-studio/crates/wos-studio-model/src/policy.rs` |
| `aiLineage` (`modelId` / `modelVersion` / `promptTemplateRef` / `temperature` / `seed` / `inputContextHash` / `humanApprover` / `humanRationale`) | `rkaf:AILineage` shape — fills the AI-governance gap Rulespec currently has | `policy-studio/schemas/wos-studio-provenance.schema.json` |
| `x-lm` annotations (`critical: true`, `intent: "..."`) | `rkaf:llmHint` annotation property | `policy-studio/schemas/*.schema.json` (pervasive) |
| Three-gate compiler contract (`schema-pass` / `lint-pass` / `conformance-pass`) | Conformance §10: normative emit-pipeline pattern for any Rulespec-producing tool at L3 | `policy-studio/specs/compiler-contract.md` |
| Workspace scoping | `rkaf:Workspace` scope kind alongside existing scopes | `policy-studio/schemas/wos-studio-workspace.schema.json` |
| Deterministic-emit invariant | Conformance §10: required for L3 Rulespec Compiler Conformance | `policy-studio/CLAUDE.md` |
| `wosTarget` projection pattern | Generalized as `rkaf:projectsTo` — overlay declares its target schema fragment | `policy-studio/specs/policy-object-model.md` |
| Polymorphic `PolicyObject` kinds (Notice, Appeal, Deadline, ActorMapping, EvidenceRequirement, Outcome, DecisionRule, etc.) | **Studio-profile-scoped** — refinements over Rulespec base classes; live in the Studio profile under the Rulespec namespace, not in universal Vocabulary (per §5.2) | `policy-studio/schemas/wos-studio-policy-object.schema.json` |
| `ApplicabilityScope`, `EffectivePeriod`, `WosVersionPin` `$defs` | Already isomorphic to Rulespec `rkaf:hasApplicability` / `rkaf:effectivePeriod*`; alignment work is field-renaming + schema regeneration | `policy-studio/schemas/wos-studio-policy-object.schema.json` |
| `Supersession` PolicyObject kind | Subsumed by `rkaf:supersedesAssertion` (already many-to-many in Rulespec) | `policy-studio/schemas/wos-studio-policy-object.schema.json` |
| `Conflict` PolicyObject kind | Subsumed by `rkaf:RegistryConflict` / `rkaf:ConceptResolutionResult` | `policy-studio/schemas/wos-studio-policy-object.schema.json` |
| Source-authority classification (`authorityClass`, `automationEligibility`, `freshnessSignal`, `supersededBy`) | Promoted into Source Authority Registry schema; `authorityClass` collapses into `rkaf:authorityKind` (the **legal/regulatory specialization** of `rkaf:warrantKind` per §5.6); `automationEligibility` maps to `rkaf:usageEligibility` lattice | `policy-studio/schemas/wos-studio-source-authority.schema.json` |
| `AuthoringProvenanceRecord` with hashChain | Composes existing PROV-O integration; hashChain becomes `prov:wasDerivedFrom` chain. Cryptographic anchoring is dependency-inverted (§4.6) — Rulespec defines the abstract anchor reference, bindings implement | `policy-studio/schemas/wos-studio-provenance.schema.json` |

**Note on ConfidenceRecord.** ConfidenceRecord was previously listed here as a Studio-derived promotion. It is **promoted to Layer 1 first-class** in §5.7 because confidence is a universal AI-accelerator-substrate primitive, not a Studio-specific concern. Studio's existing `ConfidenceRecord` shape contributes to but does not constitute the universal definition.

Each promotion follows the §13.4 RFC process. Each candidate is evaluated under §5.2 (does it generalize? or is it Studio-profile-scoped?). Generalizing primitives land in universal Vocabulary; profile-scoped primitives land in the Studio profile under the Rulespec namespace but do not become universal.

## Appendix B — Relationship to existing standards

[Informative — full ontology composition table is in §5.9 (normative).]

Rulespec Framework explicitly does not compete with existing public ontologies. The framework's posture is **federate, not replace** — and within federation, **compose, not duplicate**. Where a public ontology owns a local problem, Rulespec uses it.

The composition discipline:

- **Foundational ontologies are imported as code-level dependencies.** PROV-O (provenance), Web Annotation (selectors), SKOS (concepts), JSON-LD (serialization), SHACL (one validation target), RDF/RDFS/XSD (base graph). See §5.9.
- **Domain-specific ontologies are aligned where their scope owns the problem.** ELI / ELI-DL / ELI-I (EU legal resources, draft legislation, legislative impacts), RRMV (reporting requirements in legal provisions), Akoma Ntoso / USLM (legal source-document structure), LegalRuleML (formal legal rules), ECO / SEPIO (scientific evidence), DPV (privacy), ODRL (rights), DCTERMS (supersession), CiTO (scholarly citation typing), Schema.org / Schema.org/Legislation (public discovery), Nanopublications (publication pattern), DCAT / VoID (dataset cataloging). See §5.9.
- **Carrier formats are reached via the projector layer.** JSON Schema, JSON-LD, OpenAPI (MVP); HL7 FHIR, NIEM IEPDs, GraphQL SDL, Protobuf, Avro, Iceberg, Cedar/Rego (when partners need them). See §8.
- **Cryptographic anchoring substrates depend on Rulespec, not the reverse.** Trellis, COSE, JWS, W3C Verifiable Credentials, Sigstore, IPFS, content-addressed storage — these are bindings that depend on the §4.6 abstract anchoring contract. Rulespec does not name any specific binding as authoritative.
- **Reference / influence — studied but not imported, aligned, or projected.** Lynx Legal Knowledge Graph (H2020), LKIF, EuroVoc / ESCO (large public SKOS registries usable as ConceptRegistry seed data), Toulmin Argumentation Schema / AIF (conceptual ancestor of the Warrant model), Wikidata / Wikibase statements (conceptual ancestor of qualified assertions), EU Common Data Model, OCDS, EU eProcurement Ontology (potential domain-specific projector targets).

Where Rulespec's Vocabulary expresses something genuinely missing from the existing landscape — the universal warrant model spanning legal/scientific/editorial/cryptographic/social/source-class families, the federation contract with depth-graded adoption, the consumer-overlay pattern, the cross-domain conformance suite, the AI-substrate-accelerator posture — it is because no existing ontology occupied that role. Where an existing ontology does occupy a role, Rulespec composes.

The earlier research synthesis (PKAF v0.1.x prior art) reached the same conclusion: ELI handles identifiers and legislation metadata; Akoma Ntoso and USLM handle legal-document markup; LegalRuleML handles formal normative rules; PROV-O and Web Annotation handle provenance and evidence; SKOS, SHACL, and JSON-LD support concepts, validation, and interchange; Schema.org helps with public discovery; ODRL/XACML support permissions and access control. **None of those alone is the operating model for a mixed corpus of laws, regulations, SOPs, forms, notes, transcripts, and generated work products.** Rulespec is exactly that operating model — the layer above the existing ontologies that lets them interoperate around evidence-grounded structured claims.

## Appendix C — Why SHACL is not the constraint source of truth

[Informative]

Rulespec v0.1.1 Batch 4 validation revealed that pySHACL 0.31.0 does not reliably evaluate the `sh:if` / `sh:then` conditional shape pattern. Eight conditional shapes across Batches 1.1, 2, 3, and 4 were parsing correctly and reporting PASS, but were not actually evaluating their constraints against fixture data. All eight have been rewritten using Pattern C (`sh:or` with `sh:not`); the rewrites surfaced six latent fixture defects hidden for the entire v0.1-rc1 era.

This is a **framework-class failure**, not a one-off bug:

1. The failure mode was *silent* — validation reported PASS while not evaluating the constraint at all.
2. The failure persisted across multiple validation cycles undetected.
3. The failure's discovery required deliberate synthetic defect injection.
4. The failure depended on the choice of evaluator; pySHACL 0.31.0 specifically.

For a public federation substrate underwriting cross-organizational interop, this class of failure is disqualifying for any single-evaluator authoritative posture. The framework's response (§6):

1. The constraint source of truth is a tooling-neutral language compiled to multiple targets.
2. SHACL is one compilation target, not the authority.
3. Compilation parity across targets is a release gate.
4. Adversarial fixtures designed to surface evaluator-class failures are normative in the conformance suite.

The discovery itself is a credit to the v0.1.1 editorial process. The framework-level response makes that adversarial discipline normative for all downstream evaluator implementations.

## Appendix D — Adoption depth gradient

[Normative — formal taxonomy of §4.5]

### D.1 Depth D0 — Cite

- **Commitment:** Partner mentions Rulespec in documentation. Produces nothing Rulespec-typed.
- **Framework layers exercised:** None.
- **Conformance:** None. D0 is informational; not framework-conformant.
- **Exit criteria for D1:** Implement at least one Rulespec overlay attachment on at least one emitted artifact.

### D.2 Depth D1 — Overlay

- **Commitment:** Partner emits Rulespec overlays on its native artifacts. Native schemas remain independent.
- **Framework layers exercised:** Vocabulary, Constraints (one target), Projectors (one target).
- **Conformance:** L1 minimum; L2 typical.
- **When appropriate:** Established systems with substantial native-schema investment that benefit from cross-org transport.
- **Exit criteria for D2:** Refactor native types/enums to align name-for-name with Rulespec Vocabulary.

### D.3 Depth D2 — Align

- **Commitment:** D1 + partner's native types and enums name-for-name match Rulespec Vocabulary classes and closed taxonomies.
- **Framework layers exercised:** Vocabulary, Constraints, Projectors.
- **Conformance:** L2 minimum; L3 typical.
- **When appropriate:** Systems committing to long-term Rulespec interop without yet ready to make Vocabulary the source of truth.
- **Exit criteria for D3:** Replace hand-written native schemas with derived outputs of the §8.1.5 Derive operation.

### D.4 Depth D3 — Derive

- **Commitment:** D2 + partner's native schemas are generated from Rulespec Vocabulary via the projector pattern. The partner publishes a profile.
- **Framework layers exercised:** Vocabulary, Constraints, Registries, Projectors (with Derive), SDKs.
- **Conformance:** L3 minimum; L4 target.
- **When appropriate:** Systems with sufficient confidence in Rulespec Vocabulary completeness to make it the conceptual source of truth.
- **Reference consumer anchor.** Studio anchors here.
- **Exit criteria for D4:** Migrate runtime model to operate on Rulespec graphs; demote native schemas to authoring projections.

### D.5 Depth D4 — Substrate

- **Commitment:** D3 + partner's runtime model operates on Rulespec graphs. Native schemas exist solely as authoring projections.
- **Framework layers exercised:** All seven.
- **Conformance:** L3 minimum; L4 typical.
- **When appropriate:** New systems built fresh against Rulespec; mature systems migrating after extended D3 operation.
- **Exit criteria for D5:** Deprecate non-Rulespec authoring surfaces.

### D.6 Depth D5 — Sole

- **Commitment:** D4 + partner deprecates non-Rulespec authoring surfaces entirely. Rulespec is the only substrate.
- **Framework layers exercised:** All seven.
- **Conformance:** L3 minimum; L4 typical.
- **When appropriate:** Domain-specialized tools whose value proposition is precisely Rulespec-native authoring.
- **Exit criteria:** None — D5 is terminal.

### D.7 Depth selection guidance [Informative]

A partner's depth selection balances integration cost (lower depths cost less), cross-org transport value (delivered from D1), drift prevention (higher depths prevent more), tooling reuse (higher depths reuse more Rulespec infrastructure), and vocabulary commitment (higher depths commit more to Rulespec's editorial process).

The framework provides no opinion on the "right" depth. Healthy federations include partners at every depth.

## Appendix E — Partner onboarding

[Informative — open enrollment, no application process. Partners declare and register; no editor approval required.]

```yaml
# Rulespec Federation Conformance Declaration

partner:
  name: <organization name>
  contact: <public contact>
  website: <organization website>
  registry_endpoint: <optional — partner's registry instance URL>

declaration:
  rkaf_version: <e.g., 0.2.0>
  adoption_depth: <D1 | D2 | D3 | D4 | D5>
  conformance_level: <L1 | L2 | L3 | L4>
  fixture_suite_version: <version of §10 suite exercised>
  test_report_url: <public URL to test report>

projectors_implemented:
  - target: <e.g., json-schema | json-ld | openapi | fhir | ...>
    operations: [attach, extract, validate, derive]
    carrier_convention_version: <version>

profile:  # required if depth ≥ D3
  name: <partner profile name>
  url: <profile document URL>
  base_vocabulary_version: rkaf-core/<version>

anchoring_bindings:  # optional; per §4.6
  - binding_uri: <e.g., urn:rkaf:anchor:trellis/1>
    binding_spec_url: <URL to binding's own spec>

registry_trust:
  - registry: <reference instance URL or peer partner registry>
    scope: [source-authority, concept, bridge-contract]
    trust_basis: <reciprocal | one-way | conditional>

partner_participation:  # opt-in per §13.5
  voice: <yes | no>
  experience_reporting: <yes | no>
  profile_publication: <yes | no>
  federation_participation: <yes | no>
```

The completed declaration is registered with the Bridge Contract Registry. Open a PR against the registry's public repo with the YAML; merge follows technical review (does the test report show fixture pass?) without affiliation gating.

---

## References

### Normative

- **[RFC2119]** Bradner, S. "Key words for use in RFCs to Indicate Requirement Levels." BCP 14, RFC 2119, March 1997.
- **[RFC8174]** Leiba, B. "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words." BCP 14, RFC 8174, May 2017.
- **Rulespec Core v0.1** — `spec/pkaf-core-v0.1.md`
- **Rulespec ConceptRegistry v0.1.2** — `spec/pkaf-concept-registry-v0.1.2.md`
- **Rulespec v0.1.1 Release Manifest** — `reports/v0.1.1-release-manifest.md`

### Informative

- **JSON-LD 1.1** — W3C Recommendation, July 2020.
- **SHACL** — W3C Recommendation, July 2017.
- **PROV-O** — W3C Recommendation, April 2013.
- **Verifiable Credentials Data Model v2.0** — W3C Recommendation, May 2025. (One possible anchoring binding per §4.6.)
- **HL7 FHIR R5** — HL7 International, 2023.
- **W3C DPV** — Data Privacy Vocabulary Community Group Report.
- **WOS Studio (Authoring) Reference Architecture** — `policy-studio/specs/reference-architecture.md`
- **WOS Studio Compiler Contract** — `policy-studio/specs/compiler-contract.md`
- **WOS Studio Concept Model** — `policy-studio/CONCEPT-MODEL.md`
- **WOS Studio VISION** — `policy-studio/VISION.md`

---

*End of strategic specification. Editor's drafts of each framework layer derive from this document.*
