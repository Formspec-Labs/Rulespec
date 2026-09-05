# Request: a lexical space for E-prefixed Federal Register document numbers

- **Date:** 2026-09-05
- **Status:** Requested — decision is the owner's. Filed ahead of demand under
  the overseer's 2026-09-05 sequencing: **not cut**, because it closes no
  served gap today. Written so it is ready to cut as `0.2.0-pre.19` the day a
  consumer names itself.
- **Requesting products:** none named yet. SpicySearch (linking/serving) and
  RefSpec (minting) inherit it the way they inherited `rkaf:us-frdoc-legacy`
  and `rkaf:us-frdoc-x`; RefSpec's column-licensed admission path (REF-052)
  already carries every mechanism this family needs except the grammar.
- **Provenance:** the second amendment of
  `2026-09-02-us-frdoc-legacy-space-request.md` named this family and
  measured its tail widths; the 2026-09-05 platform investigation re-derived
  its era and heads. Every number below was re-derived for this document with
  DuckDB 1.5.5 over the preserved 1,004,233-row `federal_register.parquet`
  (`corpora/_preserved-2026-08-27/rulespec-stabilization-baseline-final`),
  using `^E[0-9]{1,2}-[0-9]+$` as the family predicate.

## The population

**119,517 of 1,004,233 `document_number` values (11.9%) are the E form**
(`E9-31172`, `E3-00004`: an `E`, a one- or two-digit head, a hyphen, a one- to
five-digit tail). Every one of them is distinct — **zero duplicate numbers**,
and therefore zero same-number collisions of the `00-111` kind that forced the
legacy scheme's date qualifier. Every one carries a parseable
`publication_date` (**zero null or empty dates**).

**The family is closed.** First date 2003-10-07, last date 2010-01-25; the
modern four-digit-year form took over in January 2010. Nothing can join it,
so every count here is final rather than provisional.

Heads, with first and last dates and the January spillover the second
amendment described (rows whose year is one past the head's nominal year; all
of them fall in January):

| head | documents | first | last | spilled into next January |
|---|---|---|---|---|
| E3 | 639 | 2003-10-07 | 2004-01-06 | 24 |
| E4 | 3,829 | 2004-01-05 | 2009-08-24 | 40 |
| E5 | 7,842 | 2005-01-06 | 2006-01-13 | 176 |
| E6 | 21,718 | 2006-01-06 | 2007-01-12 | 271 |
| E7 | 24,601 | 2007-01-08 | 2008-01-24 | 271 |
| E8 | 30,297 | 2008-01-07 | 2009-01-29 | 318 |
| E9 | 30,590 | 2009-01-06 | 2010-01-25 | 368 |
| E10 | 1 | 2010-01-06 | 2010-01-06 | 0 |

`E4` also carries the one row that is off by more than a January:
**`E4-20321` was published 2009-08-24**, five years past its nominal year
(the second amendment verified it against the live Register). The head is a
label, not a date.

Tail widths over the 119,517: **1 → 51, 2 → 514, 3 → 5,149, 4 → 44,385,
5 → 69,418**. Specimens by width: `E4-1`, `E4-10`, `E4-100`, `E4-1000`,
`E9-31172`. **641 tails are zero-padded** (`E3-00004`, the family's first
document, 2003-10-07), all of them five wide, and **no padded tail has an
unpadded twin** — `E3-4` does not exist — so the published string is the only
form the family has ever had.

What the documents are: 99,563 Notices, 11,572 Rules, 7,992 Proposed Rules,
372 Presidential Documents, 18 Uncategorized. This is the 2003–2010 Register:
the era of most rules still in force and still cited.

**Today none of the 119,517 is spellable** by `rkaf:us-frdoc`,
`rkaf:us-frdoc-legacy`, or `rkaf:us-frdoc-x` (0/0/0 matched). Of the 123,769
values the second amendment counted outside all three spaces, this family is
**96.6%**. After it, the whole remaining unspellable population is about
4,250 values (0.42%): `C` corrections 3,282 (still issued), `Z` 346, the 286
sub-floor modern numbers, 240 legacy-shaped numbers carrying a suffix
(`94-10196-2`, `94-10956Filed`), `R` republications 79, and a handful of
ingest defects.

Seven values open with `E` and are not the family: `E3-2013-2261` and six of
the form `E9-22494Filed`. They are ingest artifacts, not identifiers; this
request does not admit them, and they stay counted as unspellable.

## Why it matters

A search over the 2003–2010 Register today returns bodies whose citations
dead-end: an `E9-` or `E8-` number in a later rule's preamble links to
nothing, two catalogs holding the same document cannot be joined by number,
and every cross-reference into 11.9% of the corpus stops at the text. This is
the largest identity gap left in the Register by an order of magnitude, and
the last one that touches an era anyone routinely cites.

## What the number is, and what a scheme must not read out of it

- **The head is a year code with systematic spillover, and once badly wrong.**
  Every head spills into the following January (24 to 368 documents each), and
  `E4-20321` is 2009. A scheme that derived a year or a date from the head
  would be wrong for 1,468 documents by a month and for one by five years.
  The head is preserved as part of identity, the way `X` is; it is never
  interpreted.
- **The tail is variable-width and sometimes padded.** One to five digits,
  with 641 five-wide padded values. The published string is preserved
  verbatim; stripping zeros would change a published identifier for no gain
  (there are no twins to reconcile) and would break RefSpec's verbatim rule.
- **Strip surface.** Removing the `E` from `E3`–`E9` numbers leaves a
  single-digit head, which no space admits. Removing it from the single `E10`
  member leaves `10-31397`, a legacy-shaped bare number with **no bare twin**
  in the corpus. The exposure is a reader that treats the letter as noise, as
  it was for X; pin the refusal on the stripped form regardless.

## Options

**A — A bare sibling scheme (recommended).**
Add `rkaf:us-frdoc-e` to `#USRegulatoryIdentifierScheme` with lexical space

```
^urn:rkaf:us:frdoc-e:E(3|4|5|6|7|8|9|10)-[0-9]{1,5}$
```

The published number is the identity, verbatim: head, hyphen, tail, padding
and all. No date argument. The reasoning is the measurement: the legacy
scheme's qualifier exists to disambiguate real same-number collisions, and
this family, closed and fully censused, has none. The bare number is already
a stable identity across every catalog that holds it, and two catalogs that
disagree about a publication date still mint one IRI for one document.

The head set is sealed to the eight measured heads because the family is
closed: `E0`, `E1`, `E2`, and `E11` upward never existed, so admitting them
would admit only typos. *Variant A′*, `E[0-9]{1,2}-[0-9]{1,5}`, keeps the
regex family-shaped like the legacy space's `[0-9]{2}` head; it buys nothing
in recall and is not recommended.

*What this reverses:* the second amendment's sentence that "an E scheme needs
an external date qualifier exactly the way this one does." That sentence
reasoned from the head's unreliability as a date. The qualifier's job in the
legacy scheme is disambiguation, not dating, and this document measured that
there is nothing to disambiguate.

**B — A date-qualified sibling scheme.**

```
^urn:rkaf:us:frdoc-e:E(3|4|5|6|7|8|9|10)-[0-9]{1,5}:[0-9]{4}-[0-9]{2}-[0-9]{2}$
```

The legacy shape exactly. *For:* one qualifier discipline for both historical
families, and the date rides along as a licensed fact. *Against:* the number
cannot self-check the date the way X does, so the qualifier is an assertion
rather than an integrity check; a catalog that records a different
publication date mints a second IRI for the same document, a false split the
bare scheme cannot produce; and every mint needs the date column (available:
zero nulls, so this is a cost, not a blocker).

**C — Widen `rkaf:us-frdoc-legacy` to admit the family.**
Rejected for the reason the second amendment already gave: one scheme
covering two families accepts the weaker contract of the two, and the legacy
space is a sealed public contract since pre.17.

## What adoption takes (per pre.18's own mechanics)

The X space shipped in `c34094b` across 29 files; this family follows the
same path.

- **CUE:** `rkaf:us-frdoc-e` joins the scheme disjunction and gains its
  identifier-pattern conditional in
  `constraints/profiles/us-rulemaking/us-regulatory-artifact.cue`;
  `make compile` regenerates the Rust binding under
  `crates/rkaf-core/src/generated/profiles/us_rulemaking/`.
- **Contract:** `tools/build_contract_exports.py` regenerates `contract/enums.py`
  and `contract/terms.py`; `tools/constraints_parity.py`,
  `tools/test_constraints_compile.py`, and `tools/test_semantic_carriers.py`
  gain the E cases.
- **Spec:** a scheme-table row and the refusal rules in `spec/rkaf-rulemaking.md`;
  fixture rows in `spec/rkaf-conformance.md`.
- **Fixtures.** Positives, one per measured boundary: tail widths one through
  five (`E4-1`, `E4-10`, `E4-100`, `E4-1000`, `E9-31172`), the padded first
  document (`E3-00004`), the single `E10` member (`E10-31397`), and the
  off-year row (`E4-20321`, published 2009-08-24, to pin that the head is not
  read). Negatives: the letter stripped (`9-31172`, `10-31397`), a six-digit
  tail, an unsealed head (`E2-`, `E11-`), a suffixed ingest defect
  (`E9-22494Filed`), a modern-form twin (`2009-31172`), and the family
  negative that already exists for legacy, re-pointed at this space.
- **Version:** `0.2.0-pre.19` across `VERSION`, `pyproject.toml`,
  `crates/Cargo.toml`, `context/rkaf-context.jsonld`, and the reference-corpus
  manifest; a `CHANGELOG.md` entry; the tag `v0.2.0-pre.19` in the same commit
  that moves `VERSION`, so consumers verify the re-vendor against a name.
- **RefSpec:** `mint_federal_register_document_iri` grows an E branch under
  the same `column_licensed` flag, with no date argument under option A.

## Decision requested

1. **A or B** — bare or date-qualified. Recommendation: **A**, on the
   measurement that the family is closed and collision-free.
2. **Sealed heads or loose** — `E(3|…|10)` or `E[0-9]{1,2}`. Recommendation:
   **sealed**, because the family is closed.
3. **When to cut** — not now. The day SpicySearch or RefSpec names the
   2003–2010 Register as a served gap, this document is the bounds and the
   fixture list; nothing here needs re-measuring first.
