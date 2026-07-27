# Rulespec Conformance — L0–L4 levels

Status: Editor's Draft, normative.
Companion to: `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-behavior.md`.

## 0. Purpose

This document specifies what "Rulespec-conformant" means at increasing depths of integration. Conformance is **consumer-declared and self-certified** — there is no central certification authority pre-1.0. An implementation declares the level it satisfies; the relevant audit or conformance suite is the falsifiability gate.

Five levels are defined:

| Level | What an L`n`-conformant implementation guarantees |
|---|---|
| **L0 — Vocabulary** | A non-JSON-LD carrier maps its fields to registered Rulespec terms, identifier schemes, and closed-enum values. |
| **L1 — Parse** | Documents claiming to be Rulespec parseable as JSON-LD without error. |
| **L2 — Shape** | Every Rulespec node validates against its compiled JSON Schema. |
| **L3 — Constraint** | Every Rulespec node also passes SHACL constraints, including Pattern-C cross-property invariants. |
| **L4 — Behavior** | Implementation honors the runtime contracts in `spec/rkaf-behavior.md` (reducer, CascadeClosureV1, 10 bridge rules, point-in-time exceptions, stale transition). |

L1 ⊂ L2 ⊂ L3 ⊂ L4 — each JSON-LD level subsumes the prior. L0 is the vocabulary-only path for tabular or other non-JSON-LD carriers; it is not a prerequisite for L1. An L3-conformant implementation MUST also be L2- and L1-conformant.

## 0.1 L0 — Vocabulary [Normative]

### Requirement

An L0 implementation MUST:

1. Publish a carrier-mapping document pinned to the SHA-256 digest of the
   Rulespec contract: the kernel CUE, every domain profile's CUE, the shared
   context, and every L0 range registry.
2. Declare each mapped field's carrier location, subject type, predicate,
   direction, value kind, collection behavior, and class-valued range.
3. Give an executable transform and sample for every IRI-valued field that is
   not a closed enum; a closed-enum IRI-valued field declares an `enum_map`
   instead. Identifier transforms also declare the registered identifier
   scheme.
4. Preserve closed-enum discipline through an explicit `enum_map` or
   executable transform.
5. File a self-certification with `declared_levels: [L0]`,
   `rulespec_version`, `carrier_mapping`, `terms_used`, and
   `test_corpus_version`. `terms_used` MUST be the unique set of full term IRIs
   present in the mapping blocks.
6. NOT claim L1, L2, L3, L4, or an Appendix-D adoption depth. L0 does not
   exercise a JSON-LD carrier, and Appendix D does not define depth semantics
   for vocabulary-only carriers.

### Carrier-mapping format

The carrier-mapping document MUST contain one or more fenced code blocks whose
info string is exactly `yaml rkaf-l0-mapping`. Each block is a mapping with
exactly `rulespec_version` and `mappings`. `rulespec_version` MUST equal the
current `sha256:<64 lowercase hex>` contract digest. Every block in one
document MUST use the same digest.

```yaml rkaf-l0-mapping
rulespec_version: "sha256:5f287a1e266feb4bec73317c3dca2d10654a61b1502f13ace176d1e9f4e23446"
mappings:
  - table: proceedings
    column: current_stage
    subject_type: https://rulespec.org/ns/v1#Proceeding
    term: https://rulespec.org/ns/v1#proceedingStage
    direction: forward
    value_kind: vocab
    enum_map:
      proposed: https://rulespec.org/ns/v1#proceedingProposed
      final: https://rulespec.org/ns/v1#proceedingFinal
  - table: proceedings
    column: fr_document_numbers_json
    subject_type: https://rulespec.org/ns/v1#Proceeding
    term: https://rulespec.org/ns/v1#publishedInProceeding
    direction: inverse
    object_type: https://rulespec.org/ns/v1#Artifact
    value_kind: iri
    collection: json-list
    transform:
      template: "https://www.federalregister.gov/d/{value}"
    samples:
      - input:
          fr_document_numbers_json: '["2024-00366"]'
        output:
          - https://www.federalregister.gov/d/2024-00366
```

The example above maps a US rulemaking carrier, so both of its predicates —
`rkaf:proceedingStage` and `rkaf:publishedInProceeding` — are US rulemaking
PROFILE terms defined by `spec/rkaf-rulemaking.md` and codified under
`constraints/profiles/us-rulemaking/`, not universal kernel terms. L0 places no
adoption obligation on any profile: an implementation maps whichever registered
terms its carrier actually holds, kernel or profile, and the digest in
`rulespec_version` covers the kernel shapes, every profile's shapes, the shared
context, and every L0 range registry.

Each entry has these rules:

- `table`, `subject_type`, `term`, `direction`, and `value_kind` are required.
  `subject_type` and `term` MUST be full registered HTTP(S) IRIs.
- Exactly one of `column` or `columns` is required. `columns` is a non-empty,
  duplicate-free list for transforms that compose several fields.
- One carrier column MAY project multiple distinct predicates or directions.
  Only an exact repeat of table, column set, term, and direction is a duplicate.
- `direction` is `forward` or `inverse`. Forward emits
  `subject --term--> transformed value`. Inverse emits the transformed related
  node as the RDF subject pointing to the carrier subject. `object_type`
  declares that related node's class and is required for inverse mappings and
  class-valued ranges.
- `value_kind` is `iri`, `vocab`, `literal`, `number`, or `date` and MUST match
  the registered context/CUE coercion. `collection` defaults to `scalar`;
  `json-list` parses a single JSON-array column and applies the transform to
  every item as `{value}`.
- `enum_map` is valid only for a closed-enum property, and its `value_kind`
  MUST be `vocab` or `iri`. Both coercions put the value on the wire as an IRI;
  the difference is only whether the context resolves a bare term (`@vocab`) or
  carries the already-expanded IRI (`@id`). Every target MUST be a registered
  value allowed for that property. A closed-enum property registered as `iri`
  — `rkaf:decision`, `rkaf:assertionOrigin` — therefore declares its discipline
  through `enum_map` rather than through a transform, whose output the audit
  checks for IRI shape and never for membership.
- `transform` contains either `template`, or `pattern` plus `replacement`.
  Identifier predicates also require `identifier_scheme`.
- `source_membership`, when present, contains exactly `table` and `column`.
  It is valid only on a one-column mapping. A scalar value, or each item of a
  `json-list`, participates in that mapping only when the exact non-null value
  occurs in the named carrier column. Nonmembers remain preserved in the source
  carrier but MUST NOT be projected through that entry. A corpus-level receipt
  MUST report the projected and excluded counts and MUST fail if a projected
  value lacks the declared membership evidence. This is an evidence filter, not
  permission to discard a value merely because it fails a lexical grammar.
- A transform requires a non-empty `samples` list. Each sample has exactly an
  `input` mapping and expected `output`; the audit executes it and checks the
  declared value kind.

Unknown block, entry, transform, and sample keys are errors. The audit checks
predicate domains and class ranges from the current CUE contract, so an
inverse relationship cannot silently become a forward relationship.
A document MAY contain prose and other code blocks around the mapping blocks.

### Worked pattern — attestation as a table [Normative]

`spec/rkaf-core.md` §3.1 and §4.7.3 place approval, rejection, and revocation
in an `rkaf:Attestation` **targeting** the record — never in a field on the
record itself. That rule is about the SHAPE OF THE GRAPH, not about the
serialization, and a tabular carrier satisfies it the same way a JSON-LD one
does: with a separate node set whose rows point at the approved records. This
subsection states the pattern normatively so a Parquet, SQL, or CSV producer
does not have to infer it.

An L0 implementation that records approval MUST carry it in a **separate
attestations table**. One row is one `rkaf:Attestation` node. The row's own
identifier is the Attestation's identity; the approved record's identity
appears only in the target column, which maps to `rkaf:targets`. Six columns
carry the required Attestation terms:

| Column role | Term | Value kind | Rule |
| --- | --- | --- | --- |
| Attestor | `rkaf:attestor` | `iri` | The IRI of the party that decided. |
| Attestor kind | `rkaf:attestorKind` | `vocab` | Closed `rkaf:AttestorKind`; declare it with `enum_map`. |
| Targets | `rkaf:targets` | `iri` | At least one target. A repeated column is a `json-list`; a one-target-per-row table is `scalar`. |
| Decision | `rkaf:decision` | `iri` | Closed `rkaf:AttestationDecision`; declare it with `enum_map`. |
| Scope | `rkaf:attestationScope` | `literal` | What the decision covers. |
| Decided at | `rkaf:attestedAt` | `literal` | `xsd:dateTime`. |

Four rules make the tabular form carry the same meaning as the JSON-LD one:

1. **The attestation is not a column on the approved record.** An
   `approved_by` or `approval_status` column on the assignments, assertions, or
   findings table is NOT an Attestation, whatever it is renamed to. It carries
   no attestor kind, no scope, no decision time, and no revocation, and it
   cannot express two attestors disagreeing about one record. A carrier that
   holds only such a column MUST NOT map it to `rkaf:decision`,
   `rkaf:attestor`, or any other Attestation term.
2. **Rejection is a row.** `rkaf:rejected`, `rkaf:abstained`, and
   `rkaf:flaggedForReview` are values of the same closed decision set as
   `rkaf:approved`. A record with no attestation row is UNREVIEWED; it is not
   rejected. A carrier that represents rejection by deleting the row, or by the
   absence of an approval row, has made rejection unrepresentable and MUST NOT
   claim `rkaf:decision`.
3. **Revocation is a value, not a delete.** A withdrawn attestation keeps its
   row and gains `rkaf:revokedAt`. Deleting the row destroys the record that
   the decision was once made.
4. **`rkaf:targets` is the join, and it is many.** The Attestation names the
   records; the records do not name the Attestation. A target column with a
   single-value constraint is a narrowing of the pattern, not the pattern, and
   an implementation that needs one attestor decision over several records MUST
   either repeat the target column as a `json-list` or emit one row per target
   with a shared attestation identifier.

The mapping below is the worked example. It is audited by
`tools/test_l0_mapping_audit.py`, so it is executable rather than illustrative:

```yaml rkaf-l0-mapping
rulespec_version: "sha256:5f287a1e266feb4bec73317c3dca2d10654a61b1502f13ace176d1e9f4e23446"
mappings:
  - table: attestations
    column: attestor_id
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#attestor
    direction: forward
    value_kind: iri
    transform:
      template: "urn:example:actor:{attestor_id}"
    samples:
      - input:
          attestor_id: reviewer-14
        output: urn:example:actor:reviewer-14
  - table: attestations
    column: attestor_kind
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#attestorKind
    direction: forward
    value_kind: vocab
    enum_map:
      human: https://rulespec.org/ns/v1#humanUser
      model: https://rulespec.org/ns/v1#aiModel
  - table: attestations
    column: target_ids_json
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#targets
    direction: forward
    value_kind: iri
    collection: json-list
    transform:
      template: "urn:example:assignment:{value}"
    samples:
      - input:
          target_ids_json: '["ca-0007", "ca-0008"]'
        output:
          - urn:example:assignment:ca-0007
          - urn:example:assignment:ca-0008
  - table: attestations
    column: decision
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#decision
    direction: forward
    value_kind: iri
    enum_map:
      approved: https://rulespec.org/ns/v1#approved
      approved_with_conditions: https://rulespec.org/ns/v1#approvedWithConditions
      rejected: https://rulespec.org/ns/v1#rejected
      abstained: https://rulespec.org/ns/v1#abstained
      flagged: https://rulespec.org/ns/v1#flaggedForReview
  - table: attestations
    column: attestation_scope
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#attestationScope
    direction: forward
    value_kind: literal
  - table: attestations
    column: attested_at
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#attestedAt
    direction: forward
    value_kind: literal
  - table: attestations
    column: revoked_at
    subject_type: https://rulespec.org/ns/v1#Attestation
    term: https://rulespec.org/ns/v1#revokedAt
    direction: forward
    value_kind: literal
```

`fixtures/attestation-tabular-projection-positive.jsonld` is what two rows of
that table project to: one approval and one rejection over the same
`rkaf:ConceptAssignment`, both carrying their own attestor, scope, and decision
time, and neither appearing as a field on the assignment. The fixture is
validated at L1, L2, and L3 by the repository gates, so the pattern's output is
checked and not merely asserted.

An implementation MAY inline the attestation columns into the record's own
table ONLY when that table carries the full column set above, its rows still
project to separate Attestation nodes with their own identity, and the mapping
still declares `subject_type: rkaf:Attestation` for every attestation column.
Inlining is a storage choice about where the columns sit; it is never
permission to model approval as a property of the approved record, and it
caps the carrier at one attestation per record — a second attestor, a later
revocation, or a rejection following an approval all require the separate
table.

### Gate

`tools/l0_mapping_audit.py` parses the fenced blocks and verifies their contract
digest, structure, vocabulary terms, domain/range, direction, value kind,
transforms, samples, and enum targets against the CUE vocabulary, semantic
range registry, and canonical JSON-LD context. Given a partner YAML, it also
resolves `carrier_mapping`, verifies `terms_used`, and rejects mixed L0/L1+
claims or an L0 adoption-depth claim.

```bash
python3 tools/l0_mapping_audit.py --print-contract-version
python3 tools/l0_mapping_audit.py docs/ontology.md
python3 tools/l0_mapping_audit.py conformance/partners/rulespec-reference.yaml
```

The repository gate invokes the tool without arguments. That mode discovers every L0 declaration under `conformance/partners/`.

### Self-certification

Declaring L0 requires the mapping audit to pass against the published carrier mapping. L1–L4 fixture verdicts are `not-claimed`; they do not determine the L0 result.

## 1. L1 — Parse [Normative]

### 1.1 Requirement

An L1 implementation MUST:

1. Accept any document carrying `@type` values prefixed with `rkaf:` and parse them as JSON-LD 1.1 nodes.
2. Recognize the canonical Rulespec JSON-LD context URL (`https://rulespec.org/context/rkaf-context.jsonld`) and resolve term-to-IRI mappings against it.
3. Round-trip a Rulespec document through JSON-LD expand → compact without loss of `rkaf:*` typed properties.
4. NOT panic, crash, or silently drop nodes on unrecognized `rkaf:*` properties — forward-compatibility requires extension property tolerance.

### 1.2 Gate

`tools/conformance_report.py --level L1 --fixture <path>` exits 0 if the document parses as JSON-LD without error.

### 1.3 Self-certification

Declaring L1 requires that **every fixture under `fixtures/` parses without error** through the implementation's JSON-LD loader.

## 2. L2 — Shape [Normative]

### 2.1 Requirement

An L2 implementation MUST:

1. Satisfy L1.
2. Validate every Rulespec node against the JSON Schema for its `@type` IRI. The canonical schema set is `compiled/json-schema/core/`; the canonical Rust validator is the `rkaf-validate` crate.
3. Refuse to interpret an `@type` outside the v0.2 vocabulary as Rulespec-typed (pass-through is OK; mis-validation is not).
4. Surface validation errors with at least the offending JSON pointer and the violated constraint (`required`, `enum`, `type`, `pattern`).

### 2.2 Gate

`rkaf-validate <file>` exits 0 on L2-conformant input, 1 on any L2 violation. `tools/conformance_report.py --level L2 --fixture <path>` is the Python-side equivalent.

### 2.3 Self-certification

Declaring L2 requires that **every positive fixture validates cleanly** and every embedded JSON Schema type has positive-fixture coverage. Negative fixtures MUST surface at least one L2 or L3 violation across the reference gates.

## 3. L3 — Constraint [Normative]

### 3.1 Requirement

An L3 implementation MUST:

1. Satisfy L2.
2. Validate every Rulespec node against CUE-generated SHACL under
   `compiled/shacl/core/` and the legacy Pattern-C-only suite under `shapes/`.
   A hand-authored shape MUST NOT redefine a CUE-expressible structural,
   lexical, date, or ordered-field constraint.
3. Enforce Pattern-C cross-property invariants — e.g., an Assertion with `assertionOrigin` in the AI-touched subset MUST carry `hasAILineage`.
4. Surface SHACL violations with focus node, result path, source constraint component, and result message.

### 3.2 Gate

`tools/ci_validate.py` is the Python SHACL gate. An L3-conformant implementation produces an equivalent verdict on every fixture.

### 3.3 Self-certification

Declaring L3 requires that **every positive fixture passes the full SHACL shape suite** and **every negative fixture surfaces at least one L2 or L3 violation** through the reference gates.

## 4. L4 — Behavior [Normative]

### 4.1 Requirement

An L4 implementation MUST:

1. Satisfy L3.
2. Implement the `usageEligibility` reducer per `spec/rkaf-behavior.md` §1, honoring narrow-only / LocalAdoption-broadens-within-scope invariants.
3. Implement `CascadeClosureV1` per `spec/rkaf-behavior.md` §2 — the algorithm name in `LifecycleEvent.cascadeAlgorithm` is the conformance identifier.
4. Honor all 10 bridge contract rules per `spec/rkaf-behavior.md` §3.
5. Honor point-in-time exceptions per §4 — refuse unsupported `evaluationAnchor` values.
6. Implement stale transition per §5.
7. Emit a `rkaf:BridgeValidationResult` for every packet ingest, with conformant `result` / `effectiveUsageEligibility` / `authorityChainStatus`.

### 4.2 Gate

L4 conformance is gated by `crates/rkaf-runtime-cli/src/main.rs` (the `rkaf-behavior-validate` binary). `tools/conformance_report.py` shells out to this binary for every fixture under `fixtures/behavior/`, parses the per-fixture JSON verdict, and populates the L4 column with `pass` / `fail` / `error` / `skip`. Exit 0 from the binary across all behavior fixtures (45 today: 3 cascade — base fanout + all declared cascade predicates + as_of; 9 reducer — baseline workspace, applicability gate, capability cap, local broadens, stale narrows, stale-with-honored-PIT, freshness fresh/stale/malformed; 2 PIT — supported anchor + unsupported anchor; 6 concept-resolution — unresolved, resolved, and all 4 conflict severities (informational, operationalConflict, publicationBlocking, authorityCritical); 25 bridge-rule — positive + negative per all 10 contract rules plus Rule 5 safeAutomaticMigration exemption and targeted-finding/attestation boundary cases) is the L4 verdict gate.

`tools/l4_coverage_audit.py` is the branch-coverage gate. It verifies that the behavior corpus covers all five contracts, all 10 bridge rules with accepted/rejected outcomes, the reducer's normative branches, supported/unsupported PIT handling, concept resolution outcomes plus the severity ladder, every cascade predicate, cascade `as_of`, and Rule 5 safeAutomaticMigration.

When the binary is missing (e.g., the workspace has not been built), the reporter marks affected behavior fixtures `L4: skip` with a clear note and treats the run as divergent. A conformance run that did not execute L4 behavior fixtures is not green.

### 4.3 Self-certification

Declaring L4 requires the implementation to file a `conformance/partners/<implementation>.yaml` document enumerating which behavior-spec sections are implemented and the implementation's plan for the ones not yet enforced.

## 5. Test corpus [Normative]

The conformance test corpus lives under `fixtures/`. The §10.1 coverage target per source spec:

| Coverage | Target | Current |
|---|---|---|
| Per-class positive fixtures | every embedded compiled schema type | 74 positive fixtures; `rkaf-validate` asserts coverage for all 38 embedded `@type` schemas |
| Per-class negative fixtures | every codified class with required fields | 143 negative fixtures; `tools/validate_negatives.py` discovers and gates all of them |
| Per-class edge fixtures | every codified class | 39 edge fixtures; `tools/l0_l3_coverage_audit.py` asserts coverage for all 38 compiled schema classes |
| Behavior fixtures | every L4 contract family and normative branch | 45 behavior fixtures |
| Adversarial fixtures | ≥5 | 6 (in `fixtures/adversarial/`) |
| AI-extraction adversarial fixtures | ≥3 | 3 (in `fixtures/ai-extraction/`) |
| Projector round-trip fixtures | every projector × Attach/Extract | 7 (in `fixtures/projectors/`) |
| Cross-target parity fixtures | every CORE Vocabulary class × {JSON Schema, SHACL} | covered via `tools/constraints_parity.py` |

A class's negative + edge fixtures are housed in `fixtures/negatives/<class>-*.jsonld` and `fixtures/edges/<class>-*.jsonld` respectively to keep the positive set discoverable.

## 6. Self-certification document [Normative]

Implementations declaring a conformance level publish a YAML at `conformance/partners/<implementation>.yaml`. The template at `conformance/self-certification.template.yaml` enumerates the required fields. The common fields are:

```yaml
partner: "<organization or maintainer name>"
implementation: "<package@version>"
rulespec_version: "<commit hash or pre-release tag; L0 uses contract sha256>"
declared_levels: [L1, L2, L3, L4]   # cumulative JSON-LD subset, or [L0] alone
test_corpus_run_at: "<date>"
test_corpus_version: "<immutable fixture/corpus version>"
results:
  L0: not-claimed
  L1: pass
  L2: pass
  L3: pass
  L4: pass
notes: |
  Free-form. Document what the implementation does and does not enforce.
```

The conformance reporter (`tools/conformance_report.py --self-certify > conformance/partners/<implementation>.yaml`) produces this document from a test run.

An L0 document also includes:

```yaml
declared_levels: [L0]
rulespec_version: "sha256:<current L0 contract digest>"
carrier_mapping: "path/to/the/published-mapping.md"
terms_used:
  - "https://rulespec.org/ns/v1#hasAgendaItemIdentifier"
test_corpus_version: "<immutable carrier corpus version>"
results:
  L0: pass
  L1: not-claimed
  L2: not-claimed
  L3: not-claimed
  L4: not-claimed
```

## 7. Why consumer-declared and not authority-certified [Informative]

Pre-1.0 Rulespec is a public substrate, not a credentialed-membership organization. The federation thesis (`spec/rkaf-core.md` §1.3) is structural: partners agree on the substrate, not on a body that certifies their conformance. Self-certification with falsifiability through the conformance suite is the appropriate posture for a federation substrate at this stage.

Post-1.0, a governance shell (per `spec/rkaf-core.md` §13.3) MAY introduce third-party conformance audits, but the suite itself remains the falsifiability gate.

## 8. Adoption depth gradient interaction [Informative]

Conformance level is distinct from adoption depth (D0–D5 per source spec
Appendix D). Appendix D describes integration with the structured Rulespec
substrate and does not define a depth for the L0 vocabulary-only carrier path.
An L0 declaration therefore omits `adoption_depth`. A JSON-LD implementation
may be:

- **L2 at D1** — a partner accepting Rulespec overlays in JSON Schema documents (low integration, basic validation).
- **L3 at D3** — a reference consumer (like Studio) whose schemas are CUE-derived from a Rulespec profile, with full SHACL gate enforcement.
- **L4 at D5** — a substrate-level implementation owning the runtime contracts (workflow engine, governance platform).

For L1–L4, the matrix is multiplicative: an implementation declares a
(level, depth) tuple. JSON-LD consumers often operate at (L2, D1) or (L3, D2);
reference consumers operate at (L3, D3); substrate hosts operate at (L4, D4)
or (L4, D5).
