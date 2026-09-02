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
every document from 1994 through August 2009 (era corrected by measurement
2026-09-02 — see the second amendment) — are the bare-numeric legacy shape
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

SpicySearch's body-text lane landed and the pre-2010 bodies are acquired and
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

Implementation re-derived the amendment's bounds with DuckDB on 2026-09-02
against the 1,004,233-row preserved `federal_register.parquet`, using
`regexp_matches(document_number,'^[0-9]{2}-[0-9]+$')`. The histogram and
395,498-row total matched exactly; heads spanned `00`–`99`. The same pass found
zero bare-legacy rows with a null or empty `publication_date` and zero
bare-legacy `document_number` values present on more than one parquet row.

**The denominator on that last figure, stated so nobody cites it as a proof
it is not** (raised by the overseer session 2026-09-02, and correct): zero
within-parquet collisions is a *within-source* count over one rolled-up
table, and that table is the deduped side of the very question. `00-111` is
the demonstration — the parquet holds the 2000-01-14 Rule and the API holds
the 2000-01-18 Notice, so the parquet reads zero precisely *because* a
rollup dropped one. A cross-check that shares the filter measures the
filter. This figure therefore licenses exactly one thing: the date qualifier
costs no refusals in this source (0 missing dates). It does **not** establish
that `(number, publication date)` uniquely identifies a document, which is
the claim a RefSpec minting widening would rest on.

What settles that: spicy9's `fr-full-collision-census.json` over the full
crawl, answering both halves explicitly — (a) whether `(number, date)` is
unique across the crawled Register, and (b) whether any legacy-form value
also parses as modern-form across the form fence. Until that census exists,
this space is *spellable but not yet proven unique*; the fixtures and the
grammar stand either way, because the date qualifier was adopted on the
strength of a demonstrated collision, not on an absence of one.

**Census coverage is not a hole** (measured 2026-09-02): the pinned corpus
runs 1994-01-03 → 2026-07-23 with **zero rows before 1994**, so the crawl's
1994-onward reach exactly covers the population this space widens.

## Amendment 2026-09-02 (second) — the era is wrong, and a larger gap is named

Two corrections from an independent measurement pass (overseer session,
re-derived here against a second corpus copy; 1,004,233 rows, all document
numbers distinct; the three populations below partition it exactly).

**1. "Pre-2000" is a decade off — the legacy form runs through 2009.**
Measured spans: the bare-legacy `NN-` form spans **1994-01-03 → 2009-08-19**
(395,498 documents); the modern `YYYY-` form does not begin until
**2010-01-06** (480,852, through 2026-07-23). The count this document has
always carried is right; only its era label was wrong. The correction raises
the stakes rather than lowering them: the unspellable population is not a
historical tail, it is **everything through August 2009**, including actively
cited 2000s rulemakings.

**2. A second, larger gap this space does not close: 127,883 documents
(12.73%) match neither form.** Largest families: `E9-`/`E10-`-style
(~119,500, 2003→2013), then `X00-` (~4,400), `C0-`/`C1-` corrections (~3,300,
still issued — through 2026-07-13), `Z4-` (~350), `R0-`/`R1-`
republications (~80), plus small malformed families that look like ingest
defects (`03-26993Filed`, `00-23477-Filed`).

The apparent conflict with RefSpec's "~10,231 letter-opening numbers go
unread" **reconciles exactly, and the reconciliation is the useful fact**:
RefSpec's prose grammar (`_FR_DOCUMENT_FORMS` — correction, republication,
and a `[A-Za-z]\d-\d{4,5}` legacy form) *fullmatches* **117,292** of the
127,883, leaving **10,591** unread — RefSpec's own documented figure, its
deliberate recall decision. So the 117,292 are **detectable but unmintable**:
RefSpec reads them, and no rulespec space spells them. That is a different
defect from the one this ADR fixes, and after this space lands it is the
largest remaining unspellable population by an order of magnitude.

Not proposed here. It needs its own request, its own measured bounds, and
its own decision about whether one sibling scheme covers the letter-opening
families or each family earns its own. Recorded so the next request starts
from measurement instead of rediscovery.

**And the measurement answers that scheme question: one scheme per family.**
The two large families carry different semantics, verified 2026-09-02
(overseer's finding, re-derived here against the pinned corpus):

- **X is self-dating — and its sequence is variable-width, so parse it
  right-anchored.** The X family is **4,400** values, not the 4,194 first
  reported: 4,194 with a five-digit tail plus **206 with a six-digit tail**.
  The original count was filtered by the very shape it was meant to test
  (`X##-#####` admits only a one-digit sequence by construction, so "all
  4,194 match" was a tautology). Parsed **right-anchored** — the last four
  digits are `MMDD`, the sequence is whatever precedes them — `X{YY}-{seq}{MMDD}`
  matches `publication_date` for **4,400 of 4,400**. `X97-10423` is 1997,
  sequence 1, April 23; `X09-101207` is 2009, sequence **10**, December 07,
  and is a real distinct document (74 FR 64213, alongside `X09-11207` at
  74 FR 64129 the same day). A busy day simply carries more documents than
  one digit can number: 2009-12-07 ran to sequence 30.

  **So an X space must be written `X[0-9]{2}-[0-9]{5,6}` at minimum, and
  better still defined right-anchored**, or a future busier day breaks it
  the same way. Written `[0-9]{5}` it would make 206 real documents
  unspellable on the day it sealed — a gap created at birth, inside the work
  whose purpose is closing one. Given the right shape, X still needs no date
  argument and still gains the integrity check the legacy scheme cannot
  have, and it remains the cheapest slice of the 127,883 to close.
- **E is a year code with systematic spillover, and the year is not
  reliable.** `E3`→2003 … `E9`→2009, `E10`→2010, and the spillover into the
  following January is systematic across every head, not one head's quirk
  (E6→2007: 271, E7→2008: 271, E8→2009: ~317, E9→2010: 368, E3→2004: 24).
  Worse for any scheme tempted to read the year out of the number:
  **`E4-20321` was published 2009-08-24** (74 FR 42649, verified against the
  live Register) — five years off its nominal 2004. Year plus sequence, not
  a date, and the year is not even a reliable year — so an E scheme needs an
  external date qualifier exactly the way this one does.

One sibling scheme covering both would have to accept the weaker of the two
contracts and would discard X's self-validation. Per family, then.

**The strip-collision surface, and why the refusal is pinned where it is.**
The X family overlaps the legacy span rather than following it, so the two
spaces are not disjoint by date. Measured: **4,401** letter-form numbers
become well-formed legacy numbers when the leading letter is stripped, and
**2,382** of those have a bare twin in the corpus — 2,372 published on a
different date, 10 on the same date. Against the X family's 4,400 members
that is **54.1%**: stripping the prefix corrupts the *majority* of X
numbers, not an edge case, which is why X can never be normalised that way.
(The 206 six-digit X numbers have zero twins, consistent with existing only
on days busy enough to pass sequence nine.) Raw they are lexically disjoint,
so this space is safe as written; the exposure is any reader that treats the
prefix as noise. Decisively, in **10** of
those collisions the publication date is identical
(`X97-10423`/`97-10423` both 1997-04-23; `X96-31209`/`96-31209` both
1996-12-09; eight more) — for those the date qualifier cannot disambiguate
at all. Hence `artifact-us-frdoc-legacy-letter-prefix-negative`, which pins
the refusal on the raw letter form, one step before the point where no
qualifier could save it.
