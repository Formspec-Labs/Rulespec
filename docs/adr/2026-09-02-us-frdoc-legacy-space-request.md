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
