# US Rulemaking Reference Corpus

This corpus contains one complete, real EPA proceeding expressed as a Rulespec JSON-LD graph:

> Standards of Performance for New, Reconstructed, and Modified Sources and Emissions Guidelines for Existing Sources: Oil and Natural Gas Sector Climate Review

The proceeding is bounded by RIN `2060-AV16`. It includes docket `EPA-HQ-OAR-2021-0317`, four Federal Register documents, the April 2024 Unified Agenda entry, the affected CFR part, statutory authority, two comment periods, and three stage-transition events.

## Contents

| Resource | Count | Identity |
|---|---:|---|
| `rkaf:Proceeding` | 1 | RIN |
| `rkaf:Docket` | 1 | `EPA-HQ-OAR-2021-0317` |
| Federal Register `rkaf:Artifact` | 4 | `2021-24202`, `2021-27312`, `2022-24675`, `2024-00366` |
| Unified Agenda `rkaf:Artifact` | 1 | April 2024 entry for RIN `2060-AV16` |
| Target and authority `rkaf:Artifact` | 2 | 40 CFR part 60; 42 U.S.C. 7411 |
| `rkaf:Authority` | 1 | Regulatory authority grounded in 42 U.S.C. 7411 |
| `rkaf:CommentPeriod` | 2 | Initial proposal, including its extension; supplemental proposal |
| `rkaf:LifecycleEvent` | 3 | Proposed, supplemental, final |

The December 2021 extension changes the end of one continuous comment period
from January 14 to January 31, 2022. It is not modeled as a reopening. The
supplemental proposal begins a second period. Each CommentPeriod names the
Federal Register Artifacts from which its interval was derived.

The correction document `2024-13206` shares the docket but reports RIN `2060-AW18`, so it is outside this RIN-bounded proceeding and is deliberately excluded. This boundary demonstrates why docket membership alone cannot establish Proceeding identity.

## Sources

Sources were accessed on 2026-07-23:

- [Federal Register API: 2021-24202](https://www.federalregister.gov/api/v1/documents/2021-24202.json)
- [Federal Register API: 2021-27312](https://www.federalregister.gov/api/v1/documents/2021-27312.json)
- [Federal Register API: 2022-24675](https://www.federalregister.gov/api/v1/documents/2022-24675.json)
- [Federal Register API: 2024-00366](https://www.federalregister.gov/api/v1/documents/2024-00366.json)
- [Federal Register API: excluded correction 2024-13206](https://www.federalregister.gov/api/v1/documents/2024-13206.json)
- [Regulations.gov docket EPA-HQ-OAR-2021-0317](https://www.regulations.gov/docket/EPA-HQ-OAR-2021-0317)
- [Reginfo.gov Unified Agenda entry 2060-AV16](https://www.reginfo.gov/public/do/eAgendaViewRule?RIN=2060-AV16&pubId=202404)

The source records disagree about whether the docket itself has an assigned RIN: Regulations.gov reports “Not Assigned,” while every included Federal Register document and the Unified Agenda entry report `2060-AV16`. The corpus therefore preserves the mutable docket as a separate `rkaf:Docket` and assigns the RIN only to the `rkaf:Proceeding`.

## Validation

From the repository root:

```bash
make test-reference-corpora
```

The gate runs the corpus as fixture input through both the reference JSON
Schema validator and SHACL suite. The corpus does not claim a consumer
conformance level or adoption depth. Its manifest records the exact
content-addressed Rulespec contract used by the validation run.
