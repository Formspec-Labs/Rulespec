<!-- markdownlint-disable MD013 MD060 -->

# Rulespec Batch E vocabulary closure report

Status: **Executable gate complete for the local `0.2.0-pre.9` candidate**

Date: 2026-07-29

## Executive summary

Rulespec now enforces the vocabulary-carriage and concept-evolution rules
defined in the companion plan. The complete local `make test` gate exits
successfully. It covers the Rust implementation, source and graph validation,
behavior rules, generated-target parity, vocabulary coverage, version
consistency, code-generation drift, and the 497-fixture conformance corpus.

The tested source tree is captured by commit
`0eb94257b70783688b55220e7a84dcc61bbd7507`. This report does not claim that
the candidate is tagged, pushed, published, or released. The self-certification
records that exact tested source revision; the follow-up certification commit
changes evidence metadata only.

## Scope

Batch E closes executable coverage for:

- SKOS language maps, typed notation, notes, and multiple hierarchy parents;
- concept lifecycle operations and exact release membership;
- the RefSpec `rkaf:openLabel` profile;
- `RegisteredConcept.registeredAt`;
- resolution method, cache status, usage ceiling, and conditional mapping
  assertions on `ConceptResolutionResult`;
- generated JSON Schema, SHACL, Rust, TypeScript, Rego, and CUE targets; and
- runtime resolution behavior for direct, cached, and mapped concepts.

Registry and actor IRIs remain externally described. This batch does not
restore the retired `ConceptRegistry` or `ConceptMintingAuthority` object
models.

## Initial failures and classifications

| Failure | Count | Classification | Meaning |
|---|---:|---|---|
| Resolution-ceiling negatives passed generated SHACL but failed JSON Schema | 3 | Compiler defect | Inline literal unions inside conditionals did not become closed SHACL value sets. |
| Behavior fixtures failed L2 before their L4 rule ran | 17 | Fixture defect | Fourteen concept-resolution cases and three Bridge Rule 5 cases supplied incomplete typed inputs. |
| RefSpec overlay predicates appeared to violate kernel ownership | 4 predicates | Audit classification defect | The audit lacked explicit profile-overlay exemptions for shared assertion predicates. |
| Retired promotion and demotion values appeared allowed | 2 values | Audit classification defect | The audit interpreted values inside `sh:not` as an allowlist. |
| Nested fixtures escaped vocabulary and L0-L3 discovery | 1 discovery rule in each of 2 audits | Audit coverage defect | Both audits searched only the fixture root. |
| The malformed-language negative could not enter the L1 parse gate | 1 fixture | Fixture layering defect | `en_US` caused the JSON-LD parser to reject the document before Rulespec could test the BCP 47 rule. |
| RefSpec profile shapes used the wrong Rulespec namespace | 1 namespace | Shape defect | The shapes used `https://rulespec.org/rkaf#` instead of `https://rulespec.org/ns/v1#`. |
| One release could identify both sides of a concept change | 1 lifecycle rule | Semantic and constraint omission | A replacement, split, merge, promotion, or demotion could use one complete release as both the predecessor and successor state. Membership checks alone did not prove a change between two release states. |

The three release-blocking parity cases were:

1. `concept-resolution-result-broad-over-ceiling-negative.jsonld`;
2. `concept-resolution-result-close-awaiting-over-ceiling-negative.jsonld`;
3. `concept-resolution-result-close-local-over-ceiling-negative.jsonld`.

In each case, JSON Schema rejected the invalid usage ceiling, but generated
SHACL accepted it.

The 17 L2 behavior failures did not expose L4 logic defects. Their inputs
omitted required concept, mapping, release, attestation, adoption, or consumer
registration fields. Several Bridge Rule 5 references also used relative
identifiers where the schema required absolute IRIs.

## Corrections

The implementation made these corrections:

1. The compiler now projects conditional inline literal unions into closed
   SHACL sets and TypeScript literal unions. A focused regression test protects
   this path.
2. `ConceptResolutionUsageCeilingShape` enforces the resolution ceiling in
   graph validation.
3. Behavior fixtures now contain complete L2 records before L4 evaluation.
   Mapping identifiers and Bridge Rule 5 assertion references are absolute
   IRIs.
4. The RefSpec shapes use the canonical Rulespec namespace.
5. The semantic-carrier audit recognizes the four shared assertion predicates
   as deliberate RefSpec overlay terms.
6. Retired promotion and demotion forms use a SPARQL rejection rule, which
   keeps forbidden values out of allowlist analysis.
7. Vocabulary and L0-L3 audits discover fixtures recursively.
8. The malformed-language fixture now uses `en-abcdefghi`. JSON-LD can parse
   the document, and the Rulespec BCP 47 constraint rejects its nine-character
   subtag.
9. A concept lifecycle event with successors must name distinct predecessor
   and successor release IRIs. Each release digest proves its own release
   manifest; a digest does not let one release IRI represent two states. The
   compiler carries this rule into CUE, JSON Schema metadata, SHACL,
   TypeScript, and Rego. The Python and Rust Rulespec validators enforce the
   JSON Schema extension.

## Final results

| Gate | Result |
|---|---|
| Complete `make test` | **PASS**, exit 0 |
| Python audit tests | **208 passed** |
| Core target parity | **244 checks, 0 release blockers** |
| Documented adversarial parity findings | **2** |
| Conformance corpus | **497 fixtures, 0 divergences** |
| Conformance classes | **110 positive, 275 negative, 56 edge, 56 behavior** |
| L0 vocabulary coverage | **101/101 required fixtures** |
| CUE primitive vocabulary coverage | **49/49** |
| L1 JSON-LD parse coverage | **497/497** |
| L2 positive and negative type coverage | **53/53 and 53/53** |
| L2 required-field negative coverage | **209/209** |
| L3 edge type coverage | **53/53** |
| L4 behavior coverage | **56 fixtures** |
| L4 closed dimensions | **5/5 statuses, 7/7 methods, 3/3 cache states, 4/4 severities** |
| Rust runtime tests | **34 unit, 46 integration, 4 profile-isolation passed** |
| Projector parity | **13/13 passed** |
| Version consistency | **PASS: `0.2.0-pre.9` at every checked call site** |
| Generated Rust drift | **PASS: no drift** |

The two remaining adversarial findings are documented differences on the
adversarial corpus. They are not core release blockers:

- `conditional-silent-pass-positive`;
- `nested-noevidencereason-positive`.

## Same-release lifecycle behavior by target

The positive edge fixture names two distinct complete releases. The negative
fixture names the same complete release on both sides while satisfying all
participant membership checks.

| Target | Same-release result | Enforcement |
|---|---|---|
| Authoritative and compiled CUE | **Reject** | Direct cross-field inequality constraint. |
| JSON Schema artifact | **Reject through Rulespec Validate** | The schema declares `x-rkaf-not-equal`. Rulespec's shared Python gates and `rkaf-validate` enforce it. A generic Draft 2020-12 validator alone ignores extension keywords and is not sufficient for this rule. |
| Generated SHACL | **Reject** | A presence-aware `sh:not` branch uses `sh:equals` to reject equal release IRIs. |
| Generated TypeScript validator | **Reject** | The generated validator compares the two values directly. |
| Generated Rego validator | **Reject** | The generated `deny` rule compares the two values directly; metadata also records the inequality. |
| Generated Rust record | Data only | The generated record preserves both fields. The reference `rkaf-validate` runtime reads and enforces `x-rkaf-not-equal`, so validation rejects the fixture. |

OpenAPI and the JSON Schema projector preserve the Rulespec extension. A
consumer must use Rulespec Validate, or implement the extension with equivalent
behavior, to claim this lifecycle rule.

## Release evidence

The authoritative constraint digest is:

`sha256:8feadf8f4037a60a18667c6f7ee920ff1285ccb05a72fe5352b6cd82b38a252c`

The conformance corpus digest is:

`sha256:a16ddbf58996dc1e136a99ebf37abbeed0a3adfef724b203347c301cdd5972b2`

The following SHA-256 values identify the principal generated vocabulary
artifacts:

| Artifact | SHA-256 |
|---|---|
| `compiled/json-schema/core/concept.schema.json` | `372bfd1738f58f58391f1ba183e0a1b7502ce890adc357515023879d70a0368d` |
| `compiled/json-schema/core/vocabulary-text.schema.json` | `5e5e19b16eaf6520eb54317db0f947ea3ffe14956de42d5982060cc9a535d600` |
| `compiled/json-schema/core/lifecycle-event.schema.json` | `1d1b796f7c242129fd84a8c7e5b361994641d31b78b38900c41c5346bd3d1c95` |
| `compiled/json-schema/core/concept-resolution-result.schema.json` | `d2485e1f524149b1b2635ccb064272b18af55222ab0a96ac88d75b9c1be3e7d3` |
| `compiled/json-schema/profiles/refspec/open-label.schema.json` | `914344d660c55ae45026d33916b75df828dd73d6fe85c7544cab770a4ed184bd` |
| `compiled/shacl/core/concept.ttl` | `22ef58ce5ec28fb68782074a536fec33049386bce59f51ac6ba1d18b35ed59ae` |
| `compiled/shacl/core/vocabulary-text.ttl` | `556f22d9bdb7b201f53549a909c6ea64d26238d1989ca232d23a71a8fd1c61f6` |
| `compiled/shacl/core/lifecycle-event.ttl` | `a556f7640d2d6bc3b8e7e8dfb25d8386c64293f9decc809fbfde9e8dd21cc02e` |
| `compiled/shacl/core/concept-resolution-result.ttl` | `0f1dda3314a6151cd6bccf306640464a0fa565dd38f29203075c6a3d37991c3e` |
| `compiled/shacl/profiles/refspec/open-label.ttl` | `f9c98d09110a274dad7609d9ea6498bc2a1b2cdcae4490b99f396c9ee35a50ab` |
| `compiled/typescript/core/concept.ts` | `6c5322a7b75ee471a98393883e88c377ff4e1378fe20dca1323b803905bb3f32` |
| `compiled/typescript/core/vocabulary-text.ts` | `31c417c161e1081fa4049ed9fbb1ac78540446715939e0fdec4f251f8a16ebe6` |
| `compiled/typescript/core/lifecycle-event.ts` | `5c2bd35132910ab3bbf4491da334833bf6d5633aabf1d988c51563aef347a4e0` |
| `compiled/typescript/core/concept-resolution-result.ts` | `e3f2575ae8dc4de1fab0fea046373561d1ee9354ec0bf6dd815844b2f6e83f20` |
| `compiled/typescript/profiles/refspec/open-label.ts` | `52deee0f9aae32906693033c20405eecb18be8fa0f55d40c81cf5d95d5bbc191` |
| `crates/rkaf-core/src/generated/concept.rs` | `fa21a54f88ad3296d10a7c9ad34f7655be901e7ce2ee9a9f7bc4602af8d6a3e4` |
| `crates/rkaf-core/src/generated/vocabulary_text.rs` | `87d923608683e631b42b7fd737690da144cbc3a7fe538c8e4c719a083e667069` |
| `crates/rkaf-core/src/generated/lifecycle_event.rs` | `9d72564354bfd13f717d63e05e0b46fbe389c51d037c562162af140f9368d355` |
| `crates/rkaf-core/src/generated/concept_resolution_result.rs` | `d19546e32fc59d553ecb55bae372b5cf12cac5a631ed9657aca45d6a66a3ec32` |
| `crates/rkaf-core/src/generated/profiles/refspec/open_label.rs` | `28133ee461308402eea7e86ec07ab6e1a06b3112b03e90f006a58b5bf430fac7` |
| `context/rkaf-context.jsonld` | `be984a9a4c2e47ae6a37327afc72ca57e1bf4771c017b8abf90680aa8f6b55ff` |
| `compiled/rego/core/lifecycle-event.rego` | `b8e7be096e750fb243c9d24bce79d8d3533520c3057cbdb22e9834b49c05b6ea` |

## Delivery boundary

The local candidate is internally consistent, fully tested, and captured by an
exact source commit. Publishing that commit, tagging `0.2.0-pre.9`, or declaring
a release remains a separate delivery decision.

No work in this batch stages, commits, pushes, tags, publishes packages, or
updates RefSpec's Rulespec gitlink.

## Reproduction

From the Rulespec repository root:

```sh
make test
uv run --python 3.12 --with-requirements requirements.txt \
  python tools/conformance_report.py --self-certify
```

The self-certification is
`conformance/partners/rulespec-reference.yaml`. It records the candidate
version, corpus digest, constraint digest, and the absence of an immutable
source revision.
