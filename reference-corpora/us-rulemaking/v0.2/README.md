# US Rulemaking Reference Corpus

This corpus contains one curated, real EPA rulemaking graph:

> Standards of Performance for New, Reconstructed, and Modified Sources and Emissions Guidelines for Existing Sources: Oil and Natural Gas Sector Climate Review

The graph keeps the durable agenda item identified by RIN `2060-AV16`
separate from the editioned April 2024 Unified Agenda observation and from
the independently identified proceeding. It includes docket
`EPA-HQ-OAR-2021-0317`, four Federal Register documents, the cross-posted
regulations.gov copy of the proposed rule, the pre-amendment and resulting
CFR editions, the statutory authority chain down to its enacting public law,
the Executive order the proposal responds to, two comment periods, and three
stage-transition events.

## Contents

| Resource | Count | Identity |
|---|---:|---|
| `rkaf:RegulatoryAgendaItem` | 1 | RIN `2060-AV16` |
| `rkaf:RegulatoryAgendaObservation` | 1 | Permanent April 2024 Reginfo URL |
| `rkaf:AgendaProceedingRelationship` | 1 | Provenance-bearing RIN assignment from an action-specific Federal Register source |
| `rkaf:Proceeding` | 1 | Stable reference-corpus partner identifier |
| `rkaf:Docket` | 1 | `EPA-HQ-OAR-2021-0317` |
| Federal Register `rkaf:Artifact` | 4 | `2021-24202`, `2021-27312`, `2022-24675`, `2024-00366` |
| regulations.gov document `rkaf:Artifact` | 1 | `EPA-HQ-OAR-2021-0317-0001` (cross-posted proposed rule) |
| Target, result, and authority `rkaf:Artifact` | 4 | 40 CFR part 60 (2021 target and 2024 result); 42 U.S.C. 7411; Public Law 91-604 |
| Executive-order `rkaf:Artifact` | 1 | EO 13990, referenced by the proposed rule |
| `rkaf:Authority` | 1 | Regulatory authority grounded in 42 U.S.C. 7411 and Public Law 91-604 |
| `rkaf:CommentPeriod` | 2 | Initial proposal, including its extension; supplemental proposal |
| `rkaf:LifecycleEvent` | 3 | Proposed, supplemental, final |

The December 2021 extension changes the end of one continuous comment period
from January 14 to January 31, 2022. It is not modeled as a reopening. The
supplemental proposal begins a second period. Each CommentPeriod names the
Proceeding and Docket it anchors, the Federal Register Artifact that opened
the interval, and the Artifacts from which the interval was derived.

The correction document `2024-13206` shares the docket but reports RIN
`2060-AW18`. It is deliberately excluded because neither shared docket
membership nor a different RIN is enough to adjudicate its Proceeding
membership. A producer must preserve the source and make a separate
evidence-backed identity decision.

The proposed rule demonstrates the cross-posting pattern of
`spec/rkaf-rulemaking.md` §4.1: its Federal Register posting and its
regulations.gov posting are two Artifacts, each with its own permanent-URL
identity and its own regulatory identifier (`rkaf:us-frdoc` and
`rkaf:us-regsgov`), linked with `dcterms:hasFormat` / `dcterms:isFormatOf`.
The authority chain runs Proceeding → Authority → 42 U.S.C. 7411 and Public
Law 91-604 (`rkaf:us-usc`, `rkaf:us-pl`); Executive Order 13990
(`rkaf:us-eo`) is referenced by the proposed rule, which responds to its
directive, rather than placed in the authority chain.

The Proceeding carries both a citation-level target
(`urn:rkaf:us:cfr:40:60.5375a`) and an edition-pinned pre-amendment target.
`rkaf:proceedingProduces` points separately to the resulting 2024 CFR
edition. The RIN belongs to the separate RegulatoryAgendaItem. An
`rkaf:AgendaProceedingRelationship`, derived from an action-specific Federal
Register Artifact, records that the source assigned the RIN to this
Proceeding without turning that assignment into Proceeding identity.

## Sources

Sources were accessed on 2026-07-23:

- [Federal Register API: 2021-24202](https://www.federalregister.gov/api/v1/documents/2021-24202.json)
- [Federal Register API: 2021-27312](https://www.federalregister.gov/api/v1/documents/2021-27312.json)
- [Federal Register API: 2022-24675](https://www.federalregister.gov/api/v1/documents/2022-24675.json)
- [Federal Register API: 2024-00366](https://www.federalregister.gov/api/v1/documents/2024-00366.json)
- [Federal Register API: excluded correction 2024-13206](https://www.federalregister.gov/api/v1/documents/2024-13206.json)
- [Regulations.gov docket EPA-HQ-OAR-2021-0317](https://www.regulations.gov/docket/EPA-HQ-OAR-2021-0317)
- [Regulations.gov document EPA-HQ-OAR-2021-0317-0001](https://www.regulations.gov/document/EPA-HQ-OAR-2021-0317-0001) (cross-posted proposed rule; document identity confirmed against the regulations.gov v4 API `frDocNum` field)
- [Reginfo.gov Unified Agenda entry 2060-AV16](https://www.reginfo.gov/public/do/eAgendaViewRule?RIN=2060-AV16&pubId=202404)
- [Federal Register API: 2021-01765 (Executive Order 13990)](https://www.federalregister.gov/api/v1/documents/2021-01765.json)
- [GovInfo: Public Law 91-604, 84 Stat. 1676](https://www.govinfo.gov/app/details/STATUTE-84/STATUTE-84-Pg1676)

The source records disagree about whether the docket itself has an assigned
RIN: Regulations.gov reports “Not Assigned,” while every included Federal
Register document and the Unified Agenda entry report `2060-AV16`. The corpus
therefore preserves the mutable docket, Proceeding, editioned observation, and
RIN-identified agenda item as four distinct resources. Only action-specific
evidence creates an agenda-item-to-Proceeding relationship.

## Validation

From the repository root:

```bash
make test-reference-corpora
```

The gate runs the corpus as fixture input through both the reference JSON
Schema validator and SHACL suite. The corpus does not claim a consumer
conformance level or adoption depth. Its manifest records the exact
content-addressed Rulespec contract used by the validation run.
