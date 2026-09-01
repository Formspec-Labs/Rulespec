# Conformance assessment and certification

## Purpose

The `conformance_assessment_and_certification` module provides Rulespec’s evidence and reporting path:

- **L0:** Audits declared mappings from non-JSON-LD carriers, such as SQL tables, CSV, and Parquet, against the current vocabulary.
- **L1–L4:** Assesses JSON-LD fixtures through JSON decoding, JSON Schema validation, Shapes Constraint Language (SHACL) validation, semantic integrity checks, and Rust behavior tests.
- **Certification output:** Produces mapping verdicts, human and JSON reports, process exit statuses, and reference self-certification YAML.

The module consumes authoritative constraints and compiled artifacts. It does not compile CUE, inspect production carrier data, validate release artifacts, or issue central certification.

## Architecture

```mermaid
flowchart LR
    subgraph Sources["Inputs"]
        CUE["CUE constraints"]
        Context["JSON-LD context"]
        Ranges["L0 range registries"]
        Schemas["Compiled JSON Schema"]
        Shapes["Compiled and authored SHACL"]
        Mappings["Mapping documents and<br/>L0 partner declarations"]
        Fixtures["JSON-LD fixtures"]
        Runtime["Rust behavior runtime"]
    end

    subgraph Assessment["Conformance assessment and certification"]
        L0["l0_mapping_audit"]
        Binding["compiled_schema_binding"]
        Reporter["conformance_fixture_reporting"]

        L0 -.->|"contract_version digest"| Reporter
        Binding -->|"SchemaBinding map"| Reporter
    end

    CUE --> L0
    Context --> L0
    Ranges --> L0
    Mappings --> L0

    Schemas --> Binding
    Fixtures --> Reporter
    Shapes --> Reporter
    Runtime --> Reporter

    L0 --> L0Result["L0 mapping and partner verdicts"]
    Reporter --> Reports["Human or JSON report"]
    Reporter --> Certification["Reference self-certification YAML"]
    Reporter --> Status["Process exit status"]
```

The two assessment paths remain separate. L0 checks declarations about non-JSON-LD mappings; it is not a prerequisite or reduced form of L1. The L1–L4 reporter uses only the L0 vocabulary registry’s digest when generating reference self-certification.

```mermaid
flowchart TD
    Input{"Evidence type"}

    Input -->|"Non-JSON-LD mapping"| Registry["Build VocabularyRegistry"]
    Registry --> Mapping["Check mapping terms, types,<br/>ranges, transforms, and samples"]
    Mapping --> Partner["Reconcile optional<br/>L0 partner declaration"]
    Partner --> L0Verdict["MappingAudit and L0 verdict"]

    Input -->|"JSON-LD fixture"| Classify["Discover and classify fixture"]
    Classify --> L1["L1: decode JSON"]
    L1 --> L2["L2: select SchemaBinding and<br/>validate JSON Schema extensions"]
    L2 --> L3["L3: validate SHACL and<br/>release-digest semantics"]
    L3 --> Category["Apply positive, negative,<br/>edge, or behavior rules"]
    Category -->|"Behavior fixtures only"| L4["L4: run Rust behavior validator"]
    Category --> Result["FixtureResult"]
    L4 --> Result
    Result --> Output["Report, divergence status,<br/>or self-certification"]
```

The documented verification entry points are `make test-audits` for L0 and related coverage checks, and `make test-conformance` for the L1–L4 fixture report.

## Core component documentation

- [Compiled schema binding](compiled_schema_binding.md) — discovers compiled schemas, resolves profile precedence, and provides immutable `SchemaBinding` records for L2 dispatch.
- [Conformance fixture reporting](conformance_fixture_reporting.md) — runs the L1–L4 fixture flow, records `FixtureResult` verdicts, detects divergences, and renders reports or reference self-certification.
- [L0 mapping audit](l0_mapping_audit.md) — builds `VocabularyRegistry`, audits mapping declarations and executable samples, and reconciles L0 partner claims into `MappingAudit` results.