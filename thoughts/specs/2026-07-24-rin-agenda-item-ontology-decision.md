# RIN Ontology Decision: Durable Subjects, Editioned Records, and Qualified Relations

- **Date:** 2026-07-24
- **Status:** Accepted for the Experimental US rulemaking module
- **Consumers:** Rulespec and Spicy Regs
- **Supersedes:** The claim that `rkaf:us-rin` can, by itself, identify one
  `rkaf:Proceeding`

## Decision

A Regulation Identifier Number identifies one durable
`rkaf:RegulatoryAgendaItem`. It does not identify a publication, a Unified
Agenda edition record, or an unconditional single `rkaf:Proceeding`.

Rulespec will use two public-ontology seams that are broader than US
rulemaking:

1. An immutable `rkaf:Artifact` can use `foaf:primaryTopic` to identify the
   durable thing that the artifact principally describes.
2. A cataloged resource can use the DCAT 3 qualified-relation pattern
   (`dcat:qualifiedRelation`, `dcat:Relationship`, `dcterms:relation`, and
   `dcat:hadRole`) when a relationship needs its own role and provenance.

The US rulemaking module will add the domain terms that those general seams do
not supply:

- `rkaf:RegulatoryAgendaItem`;
- a RIN-based agenda-item identity contract;
- agenda scope, stage, priority, CFR-context, and authority-citation terms;
- `rkaf:agendaTracksProceeding`, the role used by an evidence-qualified
  agenda-item-to-proceeding relationship.

A Unified Agenda edition row remains an immutable `rkaf:Artifact`. Its
`foaf:primaryTopic` is the durable agenda item. The Artifact carries that
edition's agenda state and context. It is not a temporal version of the
Proceeding.

## The general identity pattern

The RIN problem is one instance of a pattern that applies across document
types:

| Layer | Meaning | Rulemaking example | Other examples |
|---|---|---|---|
| Durable domain subject | The thing that persists while records change | Regulatory agenda item | Court case, bill, contract, project, dataset |
| Editioned descriptive record | A dated or versioned record principally about the subject | One Unified Agenda edition entry | Catalog record, case-status snapshot, bill-status page |
| Immutable artifact | One fixed publication or captured representation | Edition-specific Reginfo page or source snapshot | PDF, filing, judgment, signed contract |
| Activity or proceeding | A real process or action associated with the subject | One rulemaking proceeding | Hearing, legislative action, procurement action |
| Qualified relationship | An evidence-bearing assertion between durable entities | Agenda item tracks proceeding | Project cites dataset, case reviews decision |

Rulespec should not invent one universal `Work` class and force every row into
it. A legal case, regulatory program, dataset, and authored work have different
identity conditions. The reusable core is the separation between a durable
subject, a document about that subject, and a qualified relationship. Domain
profiles supply the subject classes and relationship roles.

## Public-ontology audit

### BIBFRAME and IFLA LRM

[BIBFRAME 2.0](https://www.loc.gov/bibframe/docs/bibframe2-model.html)
separates a conceptual Work, a published Instance, and an individual Item.
[IFLA LRM](https://www.ifla.org/files/assets/cataloguing/frbr-lrm/ifla-lrm-august-2017_rev201712.pdf)
similarly separates Work, Expression, Manifestation, and Item.

That distinction is useful for authored content and publication forms. It does
not fit a RIN directly: a recurring safety-zone agenda item is neither the
conceptual content of all resulting rules nor a manifestation of them.
Rulespec therefore cites the identity-layer pattern without importing a
bibliographic Work class.

### ELI and ELI-DL

[ELI](https://op.europa.eu/en/web/eu-vocabularies/eli) applies a
work/expression/format distinction to legislation.
[ELI-DL](https://op.europa.eu/en/web/eu-vocabularies/dataset/-/resource?uri=http://publications.europa.eu/resource/dataset/eli-dl&version=V3.0)
adds legislative projects, activities, and draft-law resources.

These are strong models for legislation and legislative processes. A US
Unified Agenda item can cover executive-branch actions that are not draft
legislation, so importing ELI-DL's legislative-project semantics would narrow
the domain incorrectly.

### PROV-O

[PROV-O](https://www.w3.org/TR/prov-o/) defines
`prov:specializationOf` between a more specific Entity and a more general
Entity, such as today's state of a web page and the page across time.

Use it only when both nodes are temporal aspects of the same entity. A Unified
Agenda edition record is a document about an agenda item, not a specialization
of the real regulatory program or of every proceeding associated with it.
`prov:specializationOf` is therefore not the record-to-subject relation here.

PROV-O remains the provenance vocabulary for evidence and generation.

### DCAT 3

[DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) makes three distinctions that
fit this problem:

- `dcat:Resource` is an extension point for things described in a catalog;
- `dcat:CatalogRecord` is the record describing a resource's registration;
- `dcat:Relationship` qualifies a relation to another resource with a role.

DCAT also distinguishes a series member from a version of the same resource.
That is valuable prior art for recurring RINs. `dcat:DatasetSeries` itself is
not imported for rulemakings because its domain is datasets.

The prior Rulespec composition audit dropped the `dcat:` prefix because no
concrete layer used it. The RIN carrier and its full-corpus tests now provide a
named consumer, an exact binding, and executable fixtures. The four qualified
relation terms therefore move from deferred pattern citation to a scoped
mode-1 import.

### FOAF and Dublin Core

[FOAF `primaryTopic`](https://xmlns.com/foaf/spec/#term_primaryTopic) is a
stable, functional relation from a Document to the one main Thing the document
describes. DCAT uses it for `dcat:CatalogRecord` to cataloged-resource links.
It supplies the general document-to-durable-subject seam without requiring a
Rulespec-wide `Work` class.

[`dcterms:subject`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/subject/)
is appropriate for zero or more topical classifications. It is too weak to
distinguish the one registry object an edition record principally describes.
Rulespec may still use it for secondary topics in a later, separately tested
composition.

## Alternatives considered

### A. One agenda item for every RIN

Every valid RIN identifies a `RegulatoryAgendaItem`. Editioned records and
proceedings remain distinct and connect through explicit relations.

**Result:** selected. It gives RIN one meaning, handles zero, one, or many
proceedings, preserves edition history, and keeps agenda context off children.

### B. A series node only for proven recurring RINs

Ordinary RINs continue to identify Proceedings; proven umbrella RINs identify
`RulemakingSeries` nodes.

**Rejected:** the same identifier would change referent after a classification
decision. An apparently ordinary RIN could later acquire a second action,
forcing an identity migration from Proceeding to Series. It also leaves
repeated but unresolved RINs without a truthful referent.

### C. A qualified identifier-assignment assertion

A RIN assignment node can point to agenda items, series, or proceedings.

**Rejected as the primary model:** qualified assignments are useful when an
identifier's issuer, validity period, or confidence is disputed. They do not
remove the need to say what the normal RIN referent is, and they make ordinary
queries needlessly indirect. A future profile may qualify conflicting or
historical identifier assignments without changing this decision.

## Normative shape

### Durable item

`rkaf:RegulatoryAgendaItem` is a rulemaking-profile specialization of
`dcat:Resource`.

Required:

- `rkaf:hasAgendaItemIdentifier` (1);
- `rkaf:agendaItemIdentifierScheme` (1), initially `rkaf:us-rin`.

Optional:

- `rkaf:agendaScopeStatus` (0..1), one of:
  - `rkaf:agendaScopeRecurring`: an official source expressly supports a
    recurring family;
  - `rkaf:agendaScopeSingleObserved`: current evidence links exactly one
    Proceeding; this is not a closed-world promise that no later action exists;
  - `rkaf:agendaScopeUnresolved`: available evidence does not establish one
    action or an intentional recurring family;
- `dcat:qualifiedRelation` (0..*) to provenance-bearing
  `dcat:Relationship` nodes.

Multiplicity alone MUST NOT produce `agendaScopeRecurring`. One current
relationship alone MUST NOT be described as proof of permanent one-action
scope.

### Editioned observation

One Unified Agenda edition entry is one `rkaf:Artifact`. It uses:

- `foaf:primaryTopic` (1 in this profile) to the
  `rkaf:RegulatoryAgendaItem`;
- `rkaf:agendaStage` (0..1);
- `rkaf:agendaPriority` (0..1);
- `rkaf:agendaAffectsCitation` (0..*);
- `rkaf:agendaAuthorityCitation` (0..*).

These facts belong to the editioned observation. They MUST NOT become
Proceeding stage, CFR, or authority assertions without separate
action-specific evidence.

An implementation MAY additionally type the record as `dcat:CatalogRecord`.
Rulespec does not require that extra RDF type in its flat carrier projections.

### Agenda-item-to-proceeding relationship

The item links to a `dcat:Relationship` with `dcat:qualifiedRelation`. The
relationship node requires:

- `dcterms:relation` (1) to one `rkaf:Proceeding`;
- `dcat:hadRole` (1), equal to `rkaf:agendaTracksProceeding`;
- `prov:wasDerivedFrom` (1..*) with the action-specific source evidence;
- `prov:wasGeneratedBy` (1);
- `prov:wasAttributedTo` (1);
- `prov:generatedAtTime` (1).

The role means that source evidence assigned the agenda item's RIN to the
Proceeding or to an action-specific docket or publication used to construct
that Proceeding. It does not mean the RIN establishes Proceeding identity, and
it does not by itself classify the item as a recurring series.

## Query and product consequences

- Looking up a RIN starts at `RegulatoryAgendaItem`.
- Edition history joins through `foaf:primaryTopic`.
- Associated Proceedings join through qualified relationships.
- Agenda stage, priority, timetable, CFR, and authority context stay on the
  edition record.
- Proceeding stage, authority, targets, dockets, publications, and comment
  periods require action-specific evidence.
- OIRA review and meeting products may join to the agenda item through the RIN
  without merging the linked Proceedings.

## Migration

For a legacy Proceeding whose primary identifier uses `rkaf:us-rin`:

1. Mint or retain a stable partner or official-registry Proceeding identifier.
2. Mint the `RegulatoryAgendaItem` identified by that RIN.
3. Create a qualified agenda-to-Proceeding relationship only when
   action-specific source evidence supports it.
4. Move Unified Agenda stage, title, priority, timetable, CFR, and authority
   context to the edition Artifact.

For legacy `rkaf:hasProceedingEvidenceIdentifier` values:

1. Treat each RIN value as an agenda-item identifier.
2. Preserve the original evidence on the qualified relationship.
3. Do not mechanically create a relationship from a RIN-only equality join.

The old terms remain decodable during the Experimental pre-release migration,
but they no longer satisfy the current Proceeding shape.

## Rejected inferences

The following inferences are non-conforming:

- same RIN implies same Proceeding;
- repeated RIN implies recurring series;
- one observed Proceeding implies permanent single-action scope;
- agenda “Final Rule Stage” implies every linked Proceeding is final;
- agenda CFR or authority text applies to every linked Proceeding;
- an edition record is a version or specialization of a Proceeding;
- several documents about the same durable subject are the same Artifact.

