# Request: a lexical space for legacy Federal Register document numbers

- **Date:** 2026-09-02
- **Status:** Requested — decision is the owner's. Filed by the SpicySearch
  demand-consolidation plan (spicysearch
  `docs/search-demand-consolidation-plan-2026-09-02.md`, Phase 4 / D4); the
  source-supply plan's Phase E identifiers inherit the same dependency, so one
  request serves both.
- **Requesting products:** SpicySearch (linking/serving), RefSpec (minting —
  the executable layer is already built and waiting).

## The population

394,128 of 1,004,233 real Federal Register `document_number` values — 39.2%,
essentially every document before ~2000 — are the bare-numeric legacy shape
(`09-19806`, `94-120124`: two-digit year head, 3–6 digit tail). Measured over
the pinned FR corpus; the figure is restated in RefSpec
`registry/iri_minting.py`'s module notes and REF-052.

Today no `rkaf` space spells them. RefSpec's minting layer (landed 2026-09-01,
RefSpec `6eec18c4`) already carries the column-licensed admission path for
this family (REF-052: "the column is the license" — minting from a trusted
`document_number` column needs none of the prose-detection loosening that was
separately measured and refused). The partner hatch recovered 28,862 documents
(REF-054). Everything is in place except the grammar: **`rkaf:us-frdoc` is
deliberately modern-form only**, and 0.2.0-pre.16 (`961de3c`) fenced the
boundary on purpose — `94-120124` ships as a *family negative* fixture.

This request engages that fence rather than asking to erase it.

## Why it matters

SpicySearch's body-text lane landed and the pre-2000 bodies are acquired and
preserved. Served without identity, a third of history gets searchable text
whose citations dead-end: links, joins, and cross-references stop at 61% of
the corpus. The demand plan's D4 holds the honest line meanwhile (refuse,
never fabricate), but refusal at 39.2% is a product ceiling only this grammar
decision can lift.

## Options

**A — Widen `rkaf:us-frdoc` to admit the legacy family.**
`^urn:rkaf:us:frdoc:([0-9]{4}-[0-9]{3,5}|[0-9]{2}-[0-9]{3,6})$` (tail bounds
to be re-measured against the corpus before adoption). One space, one scheme.
*Against:* pre.16 deliberately fenced this family out and its fixture doctrine
("a flipped negative is replaced by negatives pinning the NEW boundary") would
have to re-fence a much softer boundary; a two-digit head is century-ambiguous
as an *identity* even when unambiguous as a *string*; and every existing
consumer of the modern-only guarantee silently loses it.

**B — A sibling scheme for the legacy family (recommended).**
Add `rkaf:us-frdoc-legacy` to `#USRegulatoryIdentifierScheme` with its own
space, e.g. `^urn:rkaf:us:frdoc-legacy:[0-9]{2}-[0-9]{3,6}$` (bounds
re-measured before adoption). The published identifier is preserved verbatim
(no century is invented — the publisher never issued a four-digit form);
`rkaf:us-frdoc`'s four-sided fence and its `94-120124` negative stay exactly
as pre.16 pinned them; consumers that want the modern guarantee keep it, and
consumers that want history opt in by scheme. RefSpec's minter grows one
branch under the same `column_licensed` flag. Century disambiguation, where a
consumer needs it, is a *join fact* (publication date lives in the same
column-bearing row), not part of the identifier.

**C — Stay refused, record the cost.**
Legitimate: D4 already serves bodies honestly without links. If chosen, the
39.2% ceiling should be recorded as accepted in the platform plan's
retained-value map so it stops resurfacing as a gap.

## What adoption takes (per pre.16's own mechanics)

The CUE change (single site for B: the scheme enum + one new conditional), the
four compiled targets, fixtures (positives from real legacy numbers —
`94-120124` itself becomes the sibling scheme's first positive while remaining
`us-frdoc`'s negative — plus four-sided negatives for the new space's own
boundary), and a version bump (0.2.0-pre.17). RefSpec then re-vendors the
compiled profile and its minting-layer contract test
(`test_the_minted_spaces_are_the_contract_verbatim`) picks the space up.

## Decision requested

Choose A, B, or C. B is recommended: it lifts the ceiling without touching a
deliberately-pinned boundary, preserves published identity verbatim, and its
blast radius is one enum member, one conditional, and fixtures.

## Amendment 2026-09-02 — B chosen; the collision fact; the date qualifier

**The owner chose B** (relayed via the supply plan's owner table on main,
2026-09-02). During implementation, the supply lane's live FR crawl
surfaced a fact that changes B's design: **legacy document numbers are not
unique.** `00-111` names two different January-2000 documents — the FR API's
`documents/00-111.json` is a 2000-01-18 notice, while the pinned
`federal_register.parquet`'s `00-111` is a 2000-01-14 rule (the rollup
silently kept one). A bare-number legacy IRI would therefore mint the same
identifier for distinct documents — a false join key.

**Ruling (orchestrator, within B): the legacy scheme is date-qualified.**

```
^urn:rkaf:us:frdoc-legacy:[0-9]{2}-[0-9]{1,6}:[0-9]{4}-[0-9]{2}-[0-9]{2}$
```

— the published number verbatim, then the document's publication date as the
disambiguator. Why this and not the API's own resolution: the API resolution
silently drops one of two real documents, against platform doctrine
(refuse/record, never silently lose — the supply fix likewise *counts* the
discarded observation rather than erasing it). Why the date is always
available: REF-052 keeps prose reading of bare legacy refused, so legacy
mints only from licensed catalog columns, and the column-bearing row carries
`publication_date` — the column is both the license and the disambiguator
source. A licensed row lacking a publication date refuses the mint (and is
counted).

The modern `rkaf:us-frdoc` space stays date-free on the assumption modern
numbers are unique; if the full-history crawl falsifies that too, this
amendment's mechanism extends. The collision census across the full range
lands with the completed crawl as a sidecar receipt at
`~/Work/corpora/supply-2026-09-02/receipts/fr-full-collision-census.json`
(per entry: documentNumber, observationCount, publicationDates, winner —
newest date, the API's own resolution — digestsDistinct, and an explicit
post2000 flag; beside discardedObservationCount and the release pins;
derived from the release's own evidence, sealed format unmoved). Cite that
receipt plus its release pin when restating collision facts here.
Consumer note: RefSpec's `mint_federal_register_document_iri` legacy branch
takes the date alongside `column_licensed` when it re-vendors this release.
Also corrected by measurement (2026-09-02): real legacy tails run 1–6
digits (histogram 1→112, 2→1,258, 3→13,226, 4→119,770, 5→261,125, 6→7 over
395,498 values), not the 3–6 this document originally guessed.
