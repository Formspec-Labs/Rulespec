# RS-P3: Register a `rkaf:formspec-need` artifact-identifier scheme

- **Date:** 2026-07-27
- **Status:** **ACCEPTED and landed 2026-07-28 in `c283d94`.** See "Resolution"
  at the foot of this document for what changed against the text below.
- **Origin:** Formspec Needs Specification, Appendix C proposal RS-P3
  (`formspec-stack/formspec/specs/needs/needs-spec.md`)
- **Consumers:** Rulespec, Formspec
- **Touches:** `spec/rkaf-core.md` §4.1 (`rkaf:artifactIdentifierScheme`), §3
  (closed-taxonomy discipline), §11 (compatibility)

## What Formspec is asking for

Add `rkaf:formspec-need` to the closed `rkaf:artifactIdentifierScheme` enum,
denoting a Formspec Needs Document `url` + `need.id` pair:

```
<docUrl>#<needId>              e.g. https://benefits.example.gov/apps/assistance/needs#proof-of-filing
<docUrl>#<needId>@<revision>   e.g. …/needs#proof-of-filing@2
```

The `@<revision>` suffix is optional. A Formspec Need carries an integer
`revision` covering its statement and grounding; an assertion that needs to
pin the wording it saw uses the suffixed form, one that tracks the Need as
currently worded omits it. This mirrors the pinning discipline the needs spec
already draws between authored citations (unpinned) and generated anchors
(pinned).

Per the closed-taxonomy discipline (§3), adding an enum value requires a
release with a declared URI.

## Acceptance criteria

*(Verbatim from the needs spec's Appendix C.)*

1. **Enum value declared** in `rkaf:artifactIdentifierScheme`.
2. **One positive fixture** of an assertion citing a product Need as evidence
   subject.
3. **One negative fixture**: a mutable URL carried without the scheme tag is
   rejected.

The negative is the important one. §4.1 already requires that "an Artifact
identifier MUST resolve to, or be derived from, one immutable edition,
publication, snapshot, or content payload" — a bare Needs Document URL is a
current-state URL, exactly the class §4.1 rejects for eCFR. The scheme tag is
what makes the `#<needId>@<revision>` form legible as an edition rather than a
live page.

## What this buys, and who it buys it for

Formspec gains nothing structural. It gains the **reverse edge**.

Today the citation runs one way: a Need cites a Rulespec assertion as evidence
that the need is legitimate. With this scheme registered, an assertion can cite
a product Need first-class — a compliance finding, an adopted policy position,
a regulator's determination can name the product commitment it is about. "The
policy corpus knows what the product committed to" becomes expressible, and
Formspec does nothing to make it so.

Without the scheme, the same citation is possible via `rkaf:partner-defined`,
but a Need citation becomes indistinguishable from an arbitrary partner URI in
federation queries. That is the whole cost of not doing this.

## Cost to Rulespec's charter

**Low but real.** One closed-enum extension, release-gated, naming a partner
format in the universal vocabulary. Precedent exists: `rkaf:eli`, `rkaf:uslm`,
`rkaf:aknt-eId`, `rkaf:doi`, `rkaf:isbn`, `rkaf:issn` all name external
schemes. The charter's first boundary ("universal ontology, not
consumer-coupled") is about *shapes*, and this adds no shape — it adds one
value to a list whose entire purpose is naming external identifier grammars.

## Why Formspec cannot do this from its side

The enum is closed and Rulespec owns it. This is the only proposal in the set
where the asymmetry is total: the assertion→need direction is unreachable
without a Rulespec change, and Formspec's own citation direction already works.

## Open questions for the maintainer

- **Fragment grammar.** `#<needId>@<revision>` puts a version marker inside a
  URI fragment. Rulespec's existing schemes carry versioning in the path
  (`rkaf:eli`) or in a hash (`rkaf:cid`). If a fragment-embedded revision reads
  wrong here, the alternative is a separate `rkaf:hasArtifactVersion`-style
  property — but that is a bigger change than one enum value, and the needs
  spec would rather have the small one.
- **Release shape.** TODO.md's "US regulatory vocabulary and rulemaking
  follow-through" section already carries an open decision on how to cut the
  next release. This enum value should join that decision rather than force its
  own tag.

## Resolution — landed 2026-07-28 (`c283d94`)

Accepted. `rkaf:formspec-need` is the thirteenth value of the closed
`rkaf:artifactIdentifierScheme` enum. All three acceptance criteria are met,
with one correction to the third.

Two places where this document and the contract had drifted, both resolved in
the contract's favour:

**No per-scheme grammar.** This document reads as though the scheme tag could
carry a checkable `<docUrl>#<needId>[@<revision>]` grammar the way `rkaf:us-cfr`
and its five siblings do. It cannot. Those live in the US rulemaking profile,
where `rkaf:hasRegulatoryIdentifier` and `rkaf:regulatoryIdentifierScheme` are
both SCALAR, so a conditional keyed on the scheme can close a pattern over the
identifier. The kernel pair is 1..* / 1..*: no positional correspondence
exists, and closing a pattern over the identifier list would force every
co-declared identifier on a multi-scheme Artifact to match the Needs grammar.
The kernel therefore closes the VALUE SET and not a grammar over it.

**The negative fails on the missing declaration, not on mutability.** The
acceptance criterion says "a mutable URL carried without the scheme tag is
rejected", which reads as if mutability were detectable. §4.1's
immutable-edition rule has never been mechanically checked for ANY scheme —
there is no fixture rejecting an eCFR URL either. What the gate catches is the
absent `rkaf:artifactIdentifierScheme`, which is REQUIRED (1..*). A producer
asserting the tag over a bare Needs Document URL is non-conforming, but as a
producer obligation in the posture of §4.7.3 rule 3 and §2.4's
`rkaf:extractionMethod` agreement. §4.1 now says both things outright.

The open question on fragment grammar is answered by the above: the
`@<revision>` suffix is carried as a producer-side convention inside the
identifier string, and no `rkaf:hasArtifactVersion`-style property was minted.
The release-shape question is unchanged and still rides the open
"decide the release shape" item in TODO.md.

Coverage: `fixtures/artifact-formspec-need-positive.jsonld`,
`fixtures/negatives/artifact-formspec-need-without-scheme-negative.jsonld`,
two rows in `tools/constraints_parity.py`, and a
`rkaf:ArtifactIdentifierScheme` entry in the vocabulary's closed-enum list.
Contract digest moved `sha256:7d45dcd2…` -> `sha256:8166af8a…`.
