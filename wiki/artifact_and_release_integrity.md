# Artifact and release integrity

## Purpose

The `artifact_and_release_integrity` module provides Rulespec’s integrity gates for immutable artifacts and release records. Its components recompute content identities, verify declared files and digests, resolve exact upstream pins, check release-specific evidence, and return deterministic validation results.

The components cover separate formats and do not replace one another. Passing validation proves integrity within the selected component’s scope; approval, publication, deployment, and activation remain product-owned decisions.

## Architecture

```mermaid
flowchart LR
    subgraph Inputs
        Artifact["Platform artifact<br/>directory or prefix"]
        V1["Core or v1 Extrapolation<br/>release JSON"]
        V2["Partitioned v2 bundle<br/>DocumentRelease v3<br/>atlas proof"]
    end

    subgraph Integrity["artifact_and_release_integrity"]
        Runtime["platform_artifact_runtime<br/>common structure and bytes"]
        ReleaseV1["release_record_validation<br/>v1 identities and semantics"]
        ReleaseV2["extrapolation_release_v2_verification<br/>v2 bundle and evidence graph"]
    end

    Artifact --> Runtime
    V1 --> ReleaseV1
    V2 --> ReleaseV2
    ReleaseV1 -. "shared v1 identity and<br/>evidence helpers" .-> ReleaseV2

    Runtime --> ArtifactResult["VerifiedArtifact<br/>or structural refusal"]
    ReleaseV1 --> V1Result["ValidationIssue list"]
    ReleaseV2 --> V2Result["VerificationResult"]

    ArtifactResult --> Gate["Product-owned release gate"]
    V1Result --> Gate
    V2Result --> Gate
    Gate --> Decision["Separate approval, publication,<br/>deployment, or activation"]
```

The module keeps storage and product knowledge behind small caller-supplied interfaces:

```mermaid
sequenceDiagram
    actor Caller
    participant Shape as Schema or format gate
    participant Verifier as Selected integrity component
    participant Proof as MemberSource, BlobSource,<br/>SemanticVerifier, or AtlasMembershipReader
    participant Gate as Product release gate

    Caller->>Shape: Supply artifact or release
    Shape-->>Caller: Shape accepted or refused
    Caller->>Verifier: Request integrity verification
    Verifier->>Verifier: Recompute canonical identity
    Verifier->>Proof: Resolve bytes, pins, membership, and product facts
    Proof-->>Verifier: Immutable evidence or refusal
    Verifier->>Verifier: Reconcile digests, links, and counts
    Verifier-->>Gate: Verified result or deterministic issues
    Gate-->>Caller: Product-owned admission decision
```

## Core components

| Component | Responsibility | Documentation |
| --- | --- | --- |
| `platform_artifact_runtime` | Builds and admits product-neutral platform artifacts. It verifies canonical bytes, identities, manifests, exact membership, payload digests, counts, and optional product semantics. It also provides race-resistant local readers and no-replace directory publication. | [Platform artifact runtime](platform_artifact_runtime.md) |
| `release_record_validation` | Validates canonical `RulespecCoreRelease` and single-JSON version 1 `ExtrapolationRelease` records. It checks release identities, exact input pins, evidence and receipt links, selection decisions, and coverage. Closed JSON Schema validation remains a separate required gate. | [Release record validation](release_record_validation.md) |
| `extrapolation_release_v2_verification` | Verifies copied, partitioned `ExtrapolationRelease` version 2 bundles offline. It closes directory membership, verifies manifests and Parquet schemas, resolves document and atlas pins, replays evidence coordinates, and reconciles dispositions, coverage, receipts, and root totals. | [Extrapolation release v2 verification](extrapolation_release_v2_verification.md) |