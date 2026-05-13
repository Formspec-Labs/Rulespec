---
title: "Formspec Generalization — Spec-Side Implementation Proposal"
date: 2026-05-13
status: proposal
authors: ["formspec-stack editorial"]
---

# Formspec Generalization: Universal Data-Contract Framework
**Spec-Side Implementation Proposal**

**Date:** 2026-05-13
**Status:** Proposal — not normative. Pre-editor's-draft stage.
**Target:** Formspec Core v2.0 (major version bump)
**Related:** `PKAF/thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md`

---

## 1. Abstract

This proposal advances Formspec from a form specification into a **universal data-contract framework**. The form profile becomes the default profile of a general-purpose primitive set. Rulespec assertions, WOS workflow artifacts, Trellis evidence packets, and arbitrary domain data become additional profiles. The stack consolidates to two languages: FEL (expression) + Formspec (schema/contract).

**What changes:**

- A `profile` declaration is added to `FormDefinition`. The `form` profile is default; new profiles (`graph`, `workflow`, plus custom) select domain-appropriate defaults for null policy, relevance suppression, and path mode.
- Six primitive gaps are closed: IRI-aware paths, entity-level disjunction, graph-scale cross-document references, constraint null policy, relevance suppression mode, and the profile system itself.
- The spec's positioning is reframed. Formspec is a data-contract framework; the form profile is intake-specific; other profiles serve other domains.
- A major version bump (`$formspec: "2.0"`) signals the framework generalization. All existing form-profile behavior is preserved under the `form` default.

**What does not change:**

- FEL grammar, type system, and stdlib. Zero changes.
- The processing model (Rebuild → Recalculate → Revalidate → Notify). Zero changes.
- Bind MIPs (calculate, relevant, required, readonly, constraint). Semantics preserved. Form-profile defaults preserved.
- Item structure (field/group/display, dataType catalog, option sets, variables, instances). Zero changes.
- Validation Shapes (and/or/not/xone, severities, ValidationResult/ValidationReport). Zero changes.
- Theme, Component, Mapping, Screener, Assist, References, Locale, Respondent Ledger companion specs. Zero changes.
- Response, IntakeHandoff schemas. Zero changes.

**Dependency direction:** Rulespec keeps its shape. Formspec grows to accommodate it.

---

## 2. Status of This Document

This document is a **proposal**, not a normative specification. It is intended to drive editor's-draft work on Formspec Core v2.0 and the profile catalog. It does not replace any current normative text; it describes changes to be made.

Pre-1.0 stack. Greenfield. No migration shims. No deprecation ceremony. No external partners. Existing form-profile semantics are preserved with no behavioral change under the default profile.

---

## 3. Motivation

### 3.1 The structural argument

Formspec's current primitives are domain-neutral. Examine them without the "form" framing:

| Primitive | Form framing | Domain-neutral reality |
|-----------|-------------|----------------------|
| **Definition** | "a form" | a versioned data-contract document |
| **Item** | "a field or section" | a typed node in a data graph |
| **Bind** | "form field behavior" | reactive constraint attachment to a path |
| **Shape** | "cross-field validation rule" | a named composable constraint over a data region |
| **OptionSet** | "answer choices" | a closed vocabulary enumeration |
| **FEL expression** | "form logic" | a deterministic, side-effect-free constraint language |
| **`@instance()`** | "secondary data source" | a named external reference for cross-document evaluation |
| **`semanticType`** | "field domain annotation" | an IRI-linked concept identifier |
| **Response** | "submitted form data" | a versioned, pinned data artifact |
| **IntakeHandoff** | "form→workflow boundary" | a cross-domain contract boundary object |

Nothing in the primitive set is intrinsically form-specific. The form-specific behavior is localized to: (a) `formPresentation` hints (advisory, not behavioral), (b) NRB defaults (`nonRelevantBehavior: "remove"`, `constraint: null → pass`), (c) naming and positioning prose.

The four-phase processing model (Rebuild → Recalculate → Revalidate → Notify) is domain-neutral: it is the XForms reactive model, proven across form, workflow, spreadsheet, and graph evaluation contexts.

### 3.2 The Rulespec forcing function

Rulespec (RKAF) — the public federation substrate for evidence-grounded structured claims — requires expressing:

- `Assertion` — an evidence-grounded claim (a Definition in graph profile)
- `Warrant` — the grounding relation (typed field with IRI value)
- `EvidenceBinding` — structured link to source fragments (a cross-document reference)
- Closed taxonomies (`warrantKind`, `assertionOrigin`, `safetyLabel`) — OptionSets in graph profile
- Cross-document IRI graphs — `@instance()` calls against authority registries
- Entity-level disjunction (`Assertion = withEvidence | withoutEvidence`) — not expressible today

This is exactly what a universal Formspec expression of Rulespec needs. Six gaps block it. This proposal closes those gaps.

### 3.3 The consolidation thesis

The stack currently has two structural languages that overlap:

- **FEL** — expressions over data
- **Formspec** — schemas/contracts for structured data

Adding Rulespec as a third structural language (CUE, custom vocabulary) reproduces the language-proliferation problem the stack exists to avoid. The correct move: Formspec is the universal schema/contract layer; Rulespec types its vocabulary using Formspec Definitions under a graph profile; FEL remains the universal expression layer. Two languages total.

---

## 4. The Profile Pattern

### 4.1 What profiles are

A **profile** is a named configuration that selects:

1. **Default null policies** for constraint, relevant, and other Bind contexts.
2. **Relevance suppression mode** — whether non-relevance suppresses validation.
3. **Path mode** — whether IRI-style paths are valid in Bind and Shape targets.
4. **Cross-document reference semantics** — lazy vs. eager instance resolution.
5. **Positioning prose** — what the profile is for (informative).

Profiles do NOT introduce new primitives. They select among behaviors already present in Formspec's primitive set, with new switches exposed by this proposal.

### 4.2 Profile declaration

A `profile` property is added to the top-level `FormDefinition`:

```json
{
  "$formspec": "2.0",
  "profile": "graph",
  "url": "https://rulespec.org/definitions/assertion",
  "version": "0.2.0",
  ...
}
```

`profile` MUST be one of the known profile identifiers or a custom profile URI. When absent, `profile` defaults to `"form"`. The `form` profile is the default; all pre-v2.0 Definitions without a `profile` are treated as `form` profile without modification.

### 4.3 What is in core vs. in a profile

**Core** (shared across all profiles):

- Item tree (field, group, display, dataType catalog)
- Bind MIPs (calculate, relevant, required, readonly, constraint, default)
- FEL grammar, type system, stdlib
- Processing model (Rebuild → Recalculate → Revalidate → Notify)
- Validation Shapes (and/or/not/xone, severities)
- ValidationResult / ValidationReport schemas
- OptionSets and variables
- Identity and versioning (url, version, lifecycle)
- Response and IntakeHandoff schemas
- Extension points (x- prefix)
- Modular composition ($ref, keyPrefix)

**Per-profile defaults** (each profile specifies its own):

- `constraintNullPolicy`: `pass` (form default) | `fail` (graph default)
- `relevanceMode`: `form` (suppresses validation when non-relevant) | `graph` (never suppresses)
- `pathMode`: `standard` (dot-path only) | `iri` (enables `@id`, `@type`, IRI paths)
- `instanceResolution`: `eager` (form default) | `lazy` (graph default, registry-backed)
- `disjunctionSupport`: `false` (form default) | `true` (graph default, enables entity disjunction)

### 4.4 Profile inheritance

Profiles extend core defaults. Custom profiles declare `extends: "<base-profile>"` and override specific settings. Custom profiles MUST use a URI identifier.

---

## 5. Core Primitive Changes

This section describes each gap item, the normative change, and where in `formspec/specs/core/spec.md` the change lands.

### 5.1 Gap 1: IRI-aware paths

**Current state.** Bind `path` and Shape `target` use dot-notation key paths (`$field.subfield`, `group.child[*]`). Keys are machine identifiers — `key` values declared on Items. There is no mechanism to reference IRI-typed concepts (`@id`, `@type`, `rkaf:warrant`) as path segments.

**What the spec says.** Core §4.3.3 (Bind path syntax): "Dot paths, `[*]`, `[@index=N]`; 1-based FEL vs 0-based resolved paths in results." No IRI path mode defined.

**Required change.** Add `pathMode` as a top-level Definition property (also selectable per profile). When `pathMode: "iri"`:

- Item keys MAY use the pattern `<prefix>:<localName>` (compact IRI) or a full IRI enclosed in angle brackets `<https://...>`.
- Bind `path` and Shape `target` MUST resolve compact IRIs against the Definition's declared prefix map (a new `@context`-analogous property, `prefixes`).
- FEL field references (`$rkaf:warrant`) MUST be valid when `pathMode: "iri"`.
- The `$` path sigil continues to work; compact IRI keys are valid `key` identifiers in IRI path mode.

**New Definition-level properties:**

```json
{
  "pathMode": "iri",
  "prefixes": {
    "rkaf": "https://rulespec.org/vocab/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "schema": "https://schema.org/"
  }
}
```

**Spec landing zone:** §4.1 (top-level structure, new `pathMode` and `prefixes` properties), §4.3.3 (Bind path syntax, add IRI path mode), §4.2.1 (Item key pattern, relax to allow compact IRI keys when `pathMode: "iri"`).

**Schema change:** `definition.schema.json` → add `pathMode` enum (`standard` | `iri`), add `prefixes` object (keys: NCName-colon patterns, values: URI strings).

### 5.2 Gap 2: Entity-level disjunction

**Current state.** Formspec supports field-level option sets and Shape-level `xone` composition. There is no mechanism to declare that a Definition *type* is itself a disjunction — `Assertion = withEvidence | withoutEvidence` as a structural constraint on which items are required depending on a type discriminator.

**What the spec says.** §5.2.2 (Shape composition): `xone` is a shape operator — it validates that exactly one branch passes. But this is a validation rule, not a structural type declaration. There is no `disjunction` property on a Definition.

**Required change.** Add `disjunction` as an OPTIONAL top-level property on FormDefinition (only valid when `disjunctionSupport: true` under the active profile):

```json
{
  "disjunction": {
    "discriminator": "rkaf:evidenceStatus",
    "variants": [
      {
        "id": "withEvidence",
        "when": "$rkaf:evidenceStatus = 'grounded'",
        "requiredItems": ["rkaf:evidenceBinding", "rkaf:sourceFragment"]
      },
      {
        "id": "withoutEvidence",
        "when": "$rkaf:evidenceStatus = 'ungrounded'",
        "requiredItems": ["rkaf:noEvidenceReason"]
      }
    ]
  }
}
```

The `disjunction` block declares that the Definition's valid shape depends on a discriminator field's value. Each variant specifies:

- `id`: variant identifier (string)
- `when`: FEL boolean — when true, this variant applies
- `requiredItems`: array of item keys that are required in this variant (equivalent to injecting `required: "true"` Binds for those items, but scoped to the variant)

**Processing model change:** During Revalidate, if a `disjunction` is declared and `disjunctionSupport` is active, the processor MUST evaluate each variant's `when` condition. The active variant's `requiredItems` MUST be enforced as required. Non-active variants' `requiredItems` MUST be treated as non-required regardless of any Bind `required` expressions.

**Spec landing zone:** §4.1 (new top-level `disjunction` property), §2.4 Phase 3 (Revalidate — add disjunction variant resolution step), §5.2 (Shapes — note that disjunction variants are resolved before shape evaluation).

**Schema change:** `definition.schema.json` → add `disjunction` object with `discriminator` (string path), `variants` array.

### 5.3 Gap 3: Graph-scale cross-document references

**Current state.** `@instance('name')` resolves against named instances declared in the `instances` object. Each instance has a `source` URI (optional), `data` fallback, and `static` flag. The design scales to roughly 5-10 pre-declared sources. It does not support lazy resolution against thousands of cross-references, authority chains, supersession edges, or registry-backed IRI lookups.

**What the spec says.** §4.4 (Instance Schema): "Instances are declared as properties of the top-level `instances` object. The property name serves as the instance's identifier." §4.4.2: "`@instance()` MUST be a string literal matching an instance name declared in the `instances` object. References to undeclared instances MUST produce a Definition error."

The hard constraint — undeclared instance = definition error — blocks graph profile use. Rulespec graphs have O(thousands) cross-references resolved against SourceAuthority registries, Concept registries, and Bridge Contract registries. These cannot be pre-declared by name.

**Required change.** Add `instanceResolution` as a Definition-level property (also selectable per profile). Two modes:

- `"eager"` (default, backward-compatible): current behavior. All instances MUST be pre-declared. Undeclared instance = definition error.
- `"lazy"`: enables registry-backed dynamic resolution. `@instance()` MAY take a full IRI string or a compact IRI. Undeclared instances are resolved against a registry defined in `instanceRegistry`. Resolution failure returns `null` (not a definition error).

New top-level property `instanceRegistry`:

```json
{
  "instanceResolution": "lazy",
  "instanceRegistry": {
    "source": "https://registries.rulespec.org/v1/resolve",
    "authScheme": "bearer",
    "cacheTtl": 3600
  }
}
```

`@instance('rkaf:SourceAuthority:IRS')` in lazy mode resolves to the IRS authority record from the registry. `@instance('https://rulespec.org/registries/source-authority/irs')` resolves by full IRI.

**Backward compatibility:** When `instanceResolution` is absent or `"eager"`, all existing behavior is preserved exactly. The lazy mode is strictly additive.

**Spec landing zone:** §4.4 (Instance Schema — add `instanceResolution` and `instanceRegistry` to top-level), §4.4.2 (Referencing Instances in Expressions — add lazy resolution mode), §3.10.1 (Definition Errors — scope the undeclared instance error to `instanceResolution: "eager"`).

**Schema change:** `definition.schema.json` → add `instanceResolution` enum (`eager` | `lazy`) and `instanceRegistry` object.

### 5.4 Gap 4: Constraint null policy mode

**Current state.** Core §3.8.1 defines: `constraint: null → true (passes)`. The rationale: "A constraint that cannot be evaluated due to null inputs is not considered violated. The `required` Bind, not the `constraint` Bind, is responsible for ensuring the field has a value." This is a form-UX default. In graph validation contexts, null constraint is not a valid passthrough — it is a data integrity failure.

**What the spec says.** The null-as-pass rule is normative and unconditional in §3.8.1. There is no override mechanism.

**Required change.** Add `constraintNullPolicy` as a Definition-level property (also selectable per profile):

- `"pass"` (default, backward-compatible): current behavior — `constraint: null → true`.
- `"fail"`: `constraint: null → false` — constraint evaluation failure produces a ValidationResult with `severity: "error"` and `constraintKind: "CONSTRAINT_NULL"`.

```json
{
  "constraintNullPolicy": "fail"
}
```

The `CONSTRAINT_NULL` ValidationResult code is added to the ValidationResult `constraintKind` enum.

**Spec landing zone:** §3.8.1 (null propagation table — add `constraintNullPolicy` override note for constraint row), §4.1 (top-level properties — add `constraintNullPolicy`), §5.3.1 (ValidationResult properties — add `CONSTRAINT_NULL` to `constraintKind` enum).

**Schema change:** `definition.schema.json` → add `constraintNullPolicy` enum (`pass` | `fail`). `validation-result.schema.json` → add `CONSTRAINT_NULL` to `constraintKind` enum.

### 5.5 Gap 5: Relevance suppression mode

**Current state.** Core §5.6 (Non-Relevant Field Handling): "Validation rules targeting the non-relevant node MUST NOT execute." This is the form UX contract — non-relevant = not shown = not validated. The rule is unconditional.

**What the spec says.** §1.4.3 (Conformance Prohibitions): "A conformant Formspec processor MUST NOT: validate non-relevant fields." This is a conformance prohibition, not just a default. It blocks graph profile use where relevance conveys domain scope (an assertion is irrelevant to a jurisdiction but still must pass graph-level constraints if present).

**Required change.** Add `relevanceMode` as a Definition-level property (also selectable per profile):

- `"form"` (default, backward-compatible): current NRB behavior. Non-relevant fields skip all validation. The conformance prohibition (VP-01 on non-relevant) applies only within `form` mode.
- `"graph"`: relevance is advisory only. Non-relevant nodes are still excluded from the submitted Response per `nonRelevantBehavior`, but validation MUST NOT be suppressed on non-relevant nodes. All Bind constraints, Shape constraints, and required checks run regardless of relevance state.

```json
{
  "relevanceMode": "graph"
}
```

**Impact on conformance prohibition.** §1.4.3 must be scoped: the prohibition "validate non-relevant fields" applies only when `relevanceMode: "form"`. Graph mode explicitly permits and requires it.

**Spec landing zone:** §4.1 (top-level properties — add `relevanceMode`), §5.6 (Non-Relevant Field Handling — scope all suppression rules to `relevanceMode: "form"`), §1.4.3 (Conformance Prohibitions — scope the non-relevant prohibition to form mode).

**Schema change:** `definition.schema.json` → add `relevanceMode` enum (`form` | `graph`).

### 5.6 Gap 6: Profile system

**Current state.** Formspec has no profile concept. It is implicitly a single-mode specification tuned for form-UX defaults. Gaps 1-5 each introduce a per-Definition toggle, but without a profile system those toggles are disconnected knobs with no coherent semantics.

**Required change.** Add `profile` as a top-level Definition property. The profile system is the composition mechanism for the gap-1 through gap-5 toggles.

**Profile definitions (v2.0 initial set):**

| Property | `form` (default) | `graph` | `workflow` |
|----------|-----------------|---------|------------|
| `constraintNullPolicy` | `pass` | `fail` | `pass` |
| `relevanceMode` | `form` | `graph` | `form` |
| `pathMode` | `standard` | `iri` | `standard` |
| `instanceResolution` | `eager` | `lazy` | `eager` |
| `disjunctionSupport` | `false` | `true` | `false` |

Each profile is a named bundle of defaults. When `profile` is declared, the corresponding defaults apply unless overridden by explicit per-Definition property settings. Explicit per-Definition settings always win over profile defaults.

**Spec landing zone:** §4.1 (top-level properties — add `profile`), new §4.1.2 (Profile Semantics — defines the profile system and the initial profile catalog).

**Schema change:** `definition.schema.json` → add `profile` as string (enum of known profiles + URI pattern for custom).

### 5.7 Gap 7: Branding / positioning

The spec's Abstract currently reads: "Formspec is a format-agnostic, JSON-native standard for declarative form definition and validation." §1.1 (Motivation) frames the problem entirely as "XForms for JSON" — a form standard.

**Required change.**

- **Abstract**: reframe as "Formspec is a format-agnostic, JSON-native data-contract framework. The form profile — intake and data collection — is one application of a domain-neutral primitive set that also serves graph validation, workflow contracts, and structured evidence packaging."
- **§1.1 Motivation**: add a paragraph after the current form-fragmentation narrative explaining the generalization: the same primitives that solve form fragmentation also solve contract fragmentation for graph data, workflow definitions, and structured claims.
- **§1.3 Scope**: add to the "defines" list: "Profile declarations selecting domain-appropriate defaults." Add to the "does not define" list: "Domain-specific schema vocabularies (those are profiles)."
- **§1.2 Design Principles**: AD-06 ("Extensible without forking") should reference the profile system as the primary extension mechanism for new domains.

---

## 6. What Stays Unchanged

The following are explicitly NOT changed by this proposal:

**FEL (formspec/specs/fel/fel-grammar.md, Core §3):** Grammar, type system, operator precedence, stdlib functions, null propagation rules (except the context-specific override enabled by `constraintNullPolicy`), error handling, dependency tracking. Zero changes.

**Processing model (Core §2.4):** The four phases (Rebuild → Recalculate → Revalidate → Notify) and their semantics. The profile system selects which validations run in Revalidate; it does not change phase order, deferred processing, or DAG construction.

**Bind MIPs under form profile (Core §4.3):** calculate, relevant, required, readonly, constraint, default — all semantics preserved. Inheritance rules (relevant AND, readonly OR, required non-inherited) preserved. Under `form` profile there is zero behavioral change from v1.0.

**Item structure (Core §4.2):** field/group/display taxonomy, dataType catalog (string, number, decimal, boolean, date, money, choice, multiChoice, file, signature), key uniqueness, repeat groups, minRepeat/maxRepeat. Zero changes.

**Validation Shapes (Core §5.1-5.5):** named shapes, and/or/not/xone operators, severity levels (error/warning/info), ValidationResult schema, ValidationReport schema. Zero changes.

**OptionSets, Variables, Instances (Core §4.4-4.6):** in `eager` instance resolution mode, all behavior is identical to v1.0.

**Response schema (schemas/response.schema.json, Core §2.1.6):** No changes to pinning rules (VP-01, VP-02), status lifecycle, authoredSignatures, or `data` structure.

**IntakeHandoff schema (schemas/intake-handoff.schema.json, Core §2.1.6.1):** No changes.

**Companion specifications:** Theme, Component, Mapping, Screener, Assist, References, Locale, Respondent Ledger, Token Registry, Extension Registry, Changelog — none require changes to support the profile system. Companions interact with Core at fixed seams (presentation, processing model, extension points) that this proposal does not alter.

**Extension points (Core §8):** The x- prefix contract, unknown-extension ignore semantics, and round-trip preservation rules are unchanged.

---

## 7. Profile Catalog v0.next

### `form` (default)

The intake and data-collection profile. The complete Formspec v1.0 behavior surface. Default for all Definitions without a `profile` declaration. All pre-v2.0 Definitions are treated as form profile.

**Domain:** web forms, PDF forms, mobile intake, survey instruments, government intake workflows.
**Deviations from core:** none — this IS the v1.0 behavior set.
**Key defaults:** `constraintNullPolicy: "pass"`, `relevanceMode: "form"`, `pathMode: "standard"`, `instanceResolution: "eager"`, `disjunctionSupport: false`.

### `graph`

The structured-data validation and knowledge-graph profile. Designed for Rulespec assertions, evidence-grounded claims, authority graphs, and any domain where every node must pass its constraints regardless of relevance state.

**Domain:** Rulespec Vocabulary, knowledge graphs, regulatory claim databases, audit evidence packages, structured citations.
**Key deviations from form:** `constraintNullPolicy: "fail"` (null constraint = validation error), `relevanceMode: "graph"` (relevance never suppresses validation), `pathMode: "iri"` (IRI keys and paths enabled), `instanceResolution: "lazy"` (registry-backed resolution enabled), `disjunctionSupport: true` (entity-level disjunction enabled).
**Use when:** a Definition describes a node type in a graph, not a form to be rendered by a human.

### `workflow`

The workflow-contract profile. Designed for WOS workflow definitions, process step contracts, state-machine schemas, and handoff boundary objects.

**Domain:** WOS workflow schemas, case management contracts, event-driven state machines.
**Key deviations from form:** `constraintNullPolicy: "pass"`, `relevanceMode: "form"`, `pathMode: "standard"`, `instanceResolution: "eager"`, `disjunctionSupport: false`.
**Note:** The workflow profile's defaults are identical to `form` in v0.next. It is declared as a distinct profile to support future divergence (e.g., workflow-specific null policy, cross-step instance references) without requiring all workflow Definitions to opt into graph semantics.

---

## 8. Rulespec as the First Non-Form Consumer

This section sketches two Rulespec Vocabulary types expressed as Formspec Definitions under the graph profile. The purpose is to demonstrate the framing is load-bearing — not to define Rulespec's normative vocabulary.

### 8.1 `Assertion` expressed as a Formspec Definition

```json
{
  "$formspec": "2.0",
  "profile": "graph",
  "url": "https://rulespec.org/definitions/assertion",
  "version": "0.2.0",
  "status": "active",
  "title": "Rulespec Assertion",
  "prefixes": {
    "rkaf": "https://rulespec.org/vocab/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "items": [
    { "key": "rkaf:id",            "type": "field", "dataType": "string",
      "label": "Assertion IRI" },
    { "key": "rkaf:assertionText", "type": "field", "dataType": "string",
      "label": "Assertion text" },
    { "key": "rkaf:evidenceStatus","type": "field", "dataType": "choice",
      "label": "Evidence status", "optionSet": "evidenceStatusOptions" },
    { "key": "rkaf:evidenceBinding","type": "group", "label": "Evidence Binding",
      "children": [
        { "key": "rkaf:sourceFragment", "type": "field", "dataType": "string" },
        { "key": "rkaf:warrantKind",    "type": "field", "dataType": "choice",
          "optionSet": "warrantKindOptions" }
      ]
    },
    { "key": "rkaf:noEvidenceReason", "type": "field", "dataType": "string",
      "label": "No-evidence reason" }
  ],
  "optionSets": {
    "evidenceStatusOptions": {
      "options": [
        { "value": "grounded",   "label": "Grounded" },
        { "value": "ungrounded", "label": "Ungrounded — reason required" }
      ]
    },
    "warrantKindOptions": {
      "options": [
        { "value": "statutory" },    { "value": "regulatory" },
        { "value": "methodological" }, { "value": "empirical" },
        { "value": "editorial" }
      ]
    }
  },
  "disjunction": {
    "discriminator": "rkaf:evidenceStatus",
    "variants": [
      {
        "id": "withEvidence",
        "when": "$rkaf:evidenceStatus = 'grounded'",
        "requiredItems": ["rkaf:evidenceBinding.rkaf:sourceFragment",
                          "rkaf:evidenceBinding.rkaf:warrantKind"]
      },
      {
        "id": "withoutEvidence",
        "when": "$rkaf:evidenceStatus = 'ungrounded'",
        "requiredItems": ["rkaf:noEvidenceReason"]
      }
    ]
  },
  "binds": [
    { "path": "rkaf:id",            "required": "true" },
    { "path": "rkaf:assertionText", "required": "true" },
    { "path": "rkaf:evidenceStatus","required": "true" }
  ],
  "shapes": [
    {
      "id": "warrantKindClosed",
      "target": "rkaf:evidenceBinding.rkaf:warrantKind",
      "severity": "error",
      "constraint": "selected(['statutory','regulatory','methodological','empirical','editorial'], $rkaf:evidenceBinding.rkaf:warrantKind)",
      "message": "warrantKind must be a closed taxonomy value.",
      "code": "RKAF_WARRANT_KIND_CLOSED"
    }
  ]
}
```

**What this demonstrates:**

- IRI keys (`rkaf:id`, `rkaf:evidenceStatus`) work as Item keys under `pathMode: "iri"`.
- `disjunction` expresses the withEvidence/withoutEvidence type-level split cleanly.
- `constraintNullPolicy: "fail"` (inherited from `graph` profile) means null `rkaf:warrantKind` fails the shape, not passes silently.
- `relevanceMode: "graph"` means the evidence group is validated regardless of whether a renderer has made it "visible."
- No form-specific properties appear (`formPresentation` absent, no `widgetHint`).

### 8.2 `EvidenceBinding` expressed as a Formspec Definition

```json
{
  "$formspec": "2.0",
  "profile": "graph",
  "url": "https://rulespec.org/definitions/evidence-binding",
  "version": "0.2.0",
  "status": "active",
  "title": "Rulespec Evidence Binding",
  "prefixes": {
    "rkaf": "https://rulespec.org/vocab/",
    "oa":   "http://www.w3.org/ns/oa#"
  },
  "instanceResolution": "lazy",
  "instanceRegistry": {
    "source": "https://registries.rulespec.org/v1/resolve"
  },
  "items": [
    { "key": "rkaf:targetAssertion", "type": "field", "dataType": "string",
      "label": "Target assertion IRI" },
    { "key": "oa:hasSource",         "type": "field", "dataType": "string",
      "label": "Source artifact IRI" },
    { "key": "oa:hasSelector",       "type": "group", "label": "Selector",
      "children": [
        { "key": "oa:type",   "type": "field", "dataType": "string" },
        { "key": "oa:value",  "type": "field", "dataType": "string" }
      ]
    },
    { "key": "rkaf:warrantKind", "type": "field", "dataType": "choice",
      "optionSet": "warrantKindOptions" }
  ],
  "binds": [
    { "path": "rkaf:targetAssertion", "required": "true" },
    { "path": "oa:hasSource",         "required": "true" },
    {
      "path": "oa:hasSource",
      "constraint": "present(@instance($oa:hasSource).rkaf:contentHash)",
      "constraintMessage": "Source artifact must be content-addressable (registry lookup failed)."
    }
  ]
}
```

**What this demonstrates:**

- `@instance($oa:hasSource)` — lazy resolution of a source IRI against the registry. Under `instanceResolution: "lazy"`, this is valid even though `$oa:hasSource` is not a pre-declared instance name; it resolves at evaluation time.
- IRI path keys (`oa:hasSource`, `oa:hasSelector`, `oa:type`) are valid items under `pathMode: "iri"`.
- Constraint failure on null registry lookup is a real error (`constraintNullPolicy: "fail"`), not a silent pass.

---

## 9. Spec Sections to Author

### 9.1 `formspec/specs/core/spec.md` — amendments

| Section | Change |
|---------|--------|
| Abstract | Reframe as universal data-contract framework; form profile as one application |
| §1.1 Motivation | Add paragraph on generalization; keep existing form-fragmentation narrative |
| §1.2 Design Principles | Update AD-06 to reference profile system |
| §1.3 Scope | Add profile declarations to "defines" list |
| §1.4.3 Conformance Prohibitions | Scope non-relevant suppression prohibition to `form` profile |
| §2.1.1 Definition | Add `profile` to the Definition abstraction description |
| §4.1 Top-Level Structure | Add `profile`, `pathMode`, `prefixes`, `constraintNullPolicy`, `relevanceMode`, `instanceResolution`, `instanceRegistry`, `disjunction` properties to the generated schema-ref table |
| New §4.1.2 | **Profile Semantics** — defines profile concept, lists v0.next profiles, specifies default-selection rules, custom profile URI pattern |
| §4.2.1 Item Common Properties | Relax `key` pattern to allow compact IRI form when `pathMode: "iri"` |
| §4.3.3 Bind Path Syntax | Add IRI path mode section — compact IRI resolution against `prefixes` |
| §4.4 Instance Schema | Add `instanceResolution` and `instanceRegistry` to top-level; §4.4.2 add lazy resolution semantics |
| New §4.8 | **Disjunction** — `disjunction` property, discriminator, variants, `requiredItems`, processing model interaction |
| §3.8.1 Null Propagation | Add `constraintNullPolicy` override to constraint row |
| §5.6 Non-Relevant Field Handling | Scope all suppression rules to `relevanceMode: "form"`; add `relevanceMode: "graph"` behavior |
| §5.3.1 ValidationResult | Add `CONSTRAINT_NULL` to `constraintKind` enum |

### 9.2 `formspec/schemas/definition.schema.json` — amendments

Add to the root Definition object:

- `profile`: `{ "type": "string", "description": "..." }` (enum of `form`, `graph`, `workflow` + URI pattern)
- `pathMode`: `{ "type": "string", "enum": ["standard", "iri"] }`
- `prefixes`: `{ "type": "object", "additionalProperties": { "type": "string" } }`
- `constraintNullPolicy`: `{ "type": "string", "enum": ["pass", "fail"] }`
- `relevanceMode`: `{ "type": "string", "enum": ["form", "graph"] }`
- `instanceResolution`: `{ "type": "string", "enum": ["eager", "lazy"] }`
- `instanceRegistry`: `{ "type": "object", "properties": { "source": ..., "authScheme": ..., "cacheTtl": ... } }`
- `disjunction`: `{ "type": "object", "properties": { "discriminator": ..., "variants": ... } }`

### 9.3 `formspec/schemas/validation-result.schema.json` — amendment

Add `CONSTRAINT_NULL` to `constraintKind` enum.

### 9.4 New: `formspec/specs/core/profiles.md`

A new companion document (not a separate spec tier — companion to Core) defining:

- The profile catalog format
- The three v0.next profiles (form, graph, workflow) with their full property tables
- Custom profile declaration pattern (URI, `extends`, property override table)
- Profile resolution rules (explicit Definition properties override profile defaults)
- Profile stability guarantees (form profile is frozen; graph and workflow profiles may evolve pre-1.0)

### 9.5 New: `formspec/schemas/profile.schema.json`

JSON Schema for the profile catalog document format (the machine-readable complement to `profiles.md`).

### 9.6 `formspec/specs/ontology/ontology-spec.md` — minor amendment

Add a note in §3 (Concept Bindings) that when `pathMode: "iri"` is active on the target Definition, concept binding keys in the Ontology Document MUST use the same IRI key format. No behavioral change; clarification only.

---

## 10. Open Issues / Decision Forks

The following are not committed in this proposal. Each needs an explicit decision before editor's-draft authoring.

**10.1 FEL IRI reference syntax.** Under `pathMode: "iri"`, the FEL `$` sigil must be extended. Options: (a) `$rkaf:id` — compact IRI as a path segment (requires FEL grammar change); (b) `$['rkaf:id']` — bracket notation with string key (no grammar change, ugly); (c) retain `$fieldKey` where keys happen to be compact IRIs (the key string itself is `rkaf:id`, so `$['rkaf:id']` resolves correctly without grammar change if bracket access is already in the grammar). **Decision needed:** which FEL path syntax extension is normative. Option (c) is lowest cost if bracket notation is already in the FEL grammar.

**10.2 `prefixes` normalization.** How should the `prefixes` map interact with Ontology Document `context`? Options: (a) orthogonal — `prefixes` is for Definition-internal path resolution, `@context` in Ontology Document is for JSON-LD export; (b) unified — the Ontology Document's `context` fragment is the prefix source. Option (a) is cleaner; option (b) avoids duplication.

**10.3 Lazy instance resolution security.** `instanceResolution: "lazy"` introduces URI resolution at evaluation time. Is the `instanceRegistry` endpoint sufficient, or must Definitions declare allowlisted domains for `@instance(IRI)` calls? The Ontology spec §10 notes "concept URIs are identifiers not fetch targets" — the same concern applies here. Decision needed before normative text is written.

**10.4 `disjunction` and Shape interaction.** When a `disjunction` variant's `requiredItems` are enforced, are they enforced as Bind `required` injections (producing `constraintKind: "REQUIRED"` results) or as a new `constraintKind: "DISJUNCTION_VARIANT"` kind? The distinction affects downstream processing that consumes ValidationResults by constraintKind. Proposal leans toward `REQUIRED` with a `shapeId` pointing to the variant; open for review.

**10.5 Workflow profile divergence.** The `workflow` profile is defined with identical defaults to `form` in v0.next. If it never diverges, it should be removed from the catalog — a profile that adds nothing is conceptual debt. Decision: either commit to a specific workflow-profile deviation by the time v2.0 editor's draft is complete, or remove the workflow profile from v0.next and add it later under the custom profile mechanism.

**10.6 Version bump ceremony.** The proposal recommends `$formspec: "2.0"`. This requires all processors to handle both `"1.0"` and `"2.0"`. The alternative: use a new marker property (`$formspecProfile: "graph"`) and keep `$formspec: "1.0"` stable. The former is cleaner; the latter avoids a version-string migration for existing tooling. Decision needed.

**10.7 Conformance tier impact.** Should graph-profile support be a Core or Extended conformance requirement? Proposal leans toward: graph profile parsing = Core (any v2.0 processor must be able to read graph-profile Definitions without error); graph profile evaluation (lazy instance resolution, disjunction validation) = Extended. Open for review.

---

## 11. Out of Scope

This proposal does not address:

**Engine changes.** Implementing lazy instance resolution, IRI path resolution, disjunction variant evaluation, and `constraintNullPolicy: "fail"` in the TypeScript engine, Rust crates, or Python reference implementation. Those are the implementation-side proposal.

**Codegen.** Generating CUE, JSON Schema, or other constraint targets from Formspec graph-profile Definitions. That is Rulespec's projector layer, not Formspec's responsibility.

**Migration of existing Definitions.** Pre-v2.0 Definitions are backward-compatible as `form` profile with zero changes. No migration tooling or `fieldMap` automation is required.

**Screener, Assist, Locale, Respondent Ledger behavioral changes.** None of these companion specs require changes. Companion specs interact with Core at seams this proposal does not alter.

**Rulespec normative vocabulary.** This proposal uses Rulespec concepts to demonstrate that the Formspec generalization is load-bearing. It does not define Rulespec's vocabulary. Rulespec's normative vocabulary lives in `PKAF/thoughts/specs/` and its successor release.

**JSON-LD integration.** The Ontology spec already handles JSON-LD context generation. The `pathMode: "iri"` addition in Formspec is a path-resolution feature, not a full JSON-LD implementation. Full JSON-LD integration (open-world semantics, named graph merging, SPARQL) remains out of Formspec scope.

**Trellis anchoring.** Rulespec Definitions expressed in Formspec do not change how Trellis anchors evidence. Trellis anchors artifacts; Formspec Definitions are one artifact type.

---

## References

- `formspec/specs/core/spec.md` — Formspec Core v1.0-draft.1 (canonical)
- `formspec/specs/ontology/ontology-spec.md` — Formspec Ontology Specification v1.0-draft.1
- `formspec/specs/mapping/mapping-spec.md` — Formspec Mapping DSL v1.0-draft.1
- `formspec/schemas/definition.schema.json` — Definition schema (structural contract)
- `formspec/schemas/validation-result.schema.json` — ValidationResult schema
- `PKAF/thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` — Rulespec strategic spec
- RFC 2119 / RFC 8174 — Normative keyword interpretation
- W3C SKOS — Concept relation vocabulary (used by Ontology spec)
- W3C Web Annotation Ontology — Selector vocabulary referenced in Rulespec EvidenceBinding
