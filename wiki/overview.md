# Rulespec repository overview

## Purpose

Rulespec is a portable semantic and verification layer for software that uses legal, regulatory, and policy rules. It records a rule’s origin, authority, lifecycle, permitted uses, concepts, evidence, reference releases, and downstream effects.

The repository:

- Compiles authoritative CUE constraints into JSON Schema, Rust, TypeScript, Shapes Constraint Language (SHACL), and Rego.
- Exposes approved vocabulary terms to Python authors.
- Assesses non-JSON-LD mappings at L0 and JSON-LD data at L1–L4.
- Verifies immutable platform artifacts and release records before a product decides to publish, deploy, or activate them.

Rulespec does not acquire source documents, run product workflows, serve search, or make product release decisions.

## End-to-end architecture

```mermaid
flowchart LR
    subgraph Sources["Semantic and evidence sources"]
        CUE["CUE constraints"]
        Semantic["JSON-LD context,<br/>vocabulary, and specifications"]
        Mappings["Carrier mappings and<br/>partner declarations"]
        Data["Rulespec JSON-LD data<br/>and fixtures"]
        RustRuntime["Rust behavior runtime"]
        Releases["Artifact directories<br/>and release bundles"]
    end

    subgraph Build["Compile and bind"]
        Compiler["constraint_compiler_ast"]
        Registry["contract_term_registry"]
        Targets["JSON Schema, Rust,<br/>TypeScript, SHACL, Rego"]
        Terms["Python terms and enums"]
    end

    CUE --> Compiler --> Targets
    CUE --> Registry
    Semantic --> Registry --> Terms
    Terms --> Data

    subgraph Assessment["Assess conformance"]
        L0["l0_mapping_audit"]
        Binding["compiled_schema_binding"]
        Reporter["conformance_fixture_reporting"]
    end

    CUE --> L0
    Semantic --> L0
    Mappings --> L0
    Targets --> Binding --> Reporter
    Targets --> Reporter
    Data --> Reporter
    RustRuntime --> Reporter

    L0 --> L0Results["L0 mapping verdicts"]
    Reporter --> Reports["L1-L4 reports,<br/>exit status, and self-certification"]

    subgraph Integrity["Verify artifact and release integrity"]
        ArtifactRuntime["platform_artifact_runtime"]
        ReleaseV1["release_record_validation"]
        ReleaseV2["extrapolation_release_v2_verification"]
    end

    Releases --> ArtifactRuntime
    Releases --> ReleaseV1
    Releases --> ReleaseV2

    ArtifactRuntime --> IntegrityResults["Verified results or<br/>deterministic refusals"]
    ReleaseV1 --> IntegrityResults
    ReleaseV2 --> IntegrityResults

    L0Results -. "release evidence" .-> Gate["Product-owned release gate"]
    Reports -. "release evidence" .-> Gate
    IntegrityResults --> Gate
    Gate --> Decision["Approval, publication,<br/>deployment, or activation"]
```

The assessment paths remain distinct:

```mermaid
flowchart TD
    Input{"Input type"}

    Input -->|"SQL, CSV, Parquet,<br/>or another mapped format"| L0["L0: audit vocabulary mapping,<br/>ranges, transforms, and samples"]
    L0 --> L0Verdict["Mapping and partner verdict"]

    Input -->|"JSON-LD"| L1["L1: decode and classify JSON"]
    L1 --> L2["L2: select compiled schema<br/>and validate structure"]
    L2 --> L3["L3: validate SHACL constraints<br/>and release-digest semantics"]
    L3 --> Behavior{"Behavior fixture?"}
    Behavior -->|"Yes"| L4["L4: run Rust behavior validator"]
    Behavior -->|"No"| Result["Fixture result"]
    L4 --> Result
    Result --> Report["Human or JSON report,<br/>status, or self-certification"]

    Input -->|"Artifact or release"| Format["Check required format"]
    Format --> Verify["Recompute identities, digests,<br/>pins, membership, and counts"]
    Verify --> Evidence["Resolve immutable evidence"]
    Evidence --> Integrity["Verified result or issues"]
    Integrity --> Product["Product-owned decision"]
```

The term registry helps authors use approved names; it does not validate data. L0 audits non-JSON-LD mappings independently of the cumulative L1–L4 JSON-LD path. Integrity verification proves only the selected artifact or release format’s stated properties.

## Core module documentation

Area guides:

- [Semantic contract compilation and binding](/Users/mikewolfd/Work/rulespec/wiki/semantic_contract_compilation_and_binding.md)
- [Conformance assessment and certification](/Users/mikewolfd/Work/rulespec/wiki/conformance_assessment_and_certification.md)
- [Artifact and release integrity](/Users/mikewolfd/Work/rulespec/wiki/artifact_and_release_integrity.md)

| Core module | Implementation | Documentation |
|---|---|---|
| `constraint_compiler_ast` | [constraints_compile.py](/Users/mikewolfd/Work/rulespec/tools/constraints_compile.py) | [Constraint compiler AST](/Users/mikewolfd/Work/rulespec/wiki/constraint_compiler_ast.md) |
| `contract_term_registry` | [_term.py](/Users/mikewolfd/Work/rulespec/src/rulespec_conformance/contract/_term.py) | [Contract term registry](/Users/mikewolfd/Work/rulespec/wiki/contract_term_registry.md) |
| `compiled_schema_binding` | [conformance_lib.py](/Users/mikewolfd/Work/rulespec/src/rulespec_conformance/conformance_lib.py) | [Compiled schema binding](/Users/mikewolfd/Work/rulespec/wiki/compiled_schema_binding.md) |
| `conformance_fixture_reporting` | [conformance_report.py](/Users/mikewolfd/Work/rulespec/tools/conformance_report.py) | [Conformance fixture reporting](/Users/mikewolfd/Work/rulespec/wiki/conformance_fixture_reporting.md) |
| `l0_mapping_audit` | [l0_mapping_audit.py](/Users/mikewolfd/Work/rulespec/tools/l0_mapping_audit.py) | [L0 mapping audit](/Users/mikewolfd/Work/rulespec/wiki/l0_mapping_audit.md) |
| `platform_artifact_runtime` | [_artifact.py](/Users/mikewolfd/Work/rulespec/packages/rulespec-artifacts/src/rulespec_artifacts/_artifact.py) | [Platform artifact runtime](/Users/mikewolfd/Work/rulespec/wiki/platform_artifact_runtime.md) |
| `release_record_validation` | [rulespec_release.py](/Users/mikewolfd/Work/rulespec/tools/rulespec_release.py) | [Release record validation](/Users/mikewolfd/Work/rulespec/wiki/release_record_validation.md) |
| `extrapolation_release_v2_verification` | [extrapolation_release_v2.py](/Users/mikewolfd/Work/rulespec/tools/extrapolation_release_v2.py) | [Extrapolation release v2 verification](/Users/mikewolfd/Work/rulespec/wiki/extrapolation_release_v2_verification.md) |

The main verification entry points are `make compile`, `make test-audits`, `make test-conformance`, and the complete `make test` gate.