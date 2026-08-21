# Evidence Graph Phase 12 — Evidence Assessment and Review

Phase 12 turns generalized claims into an operational human-review surface without changing deterministic proof authority.

## Requirement assessment

Every claim can be rendered as a requirement-by-requirement assessment. Each declared requirement receives one of these review states:

- `SATISFIED`
- `PARTIAL`
- `MISSING`
- `UNRESOLVED`
- `CONFLICT`

These are review-display states only. The authoritative claim result remains one of the generalized Evidence Graph states (`PROVEN`, `PARTIAL`, `UNRESOLVED`, `NOT APPLICABLE`, `CONFLICT`).

Every unresolved, partial, or conflicting claim must expose at least one actionable reason. If an adapter omitted a specific missing owner, the review engine explicitly asks for the exact owner/runtime consumer instead of inventing one.

## Review queue

`build_review_queue()` provides:

- domain filtering;
- deterministic launch-impact ordering;
- invalidated-claim priority;
- shared missing-owner/reason grouping;
- exact source-record navigation targets;
- dependency-based consumer-search leads.

Conflict has the highest base launch impact, followed by unresolved and partial claims. Phase 11 invalidation adds priority without changing the claim's evidence state.

## Manual review overlay

Manual reviews are stored separately under:

`research/claim-reviews.json`

Allowed manual states:

- `VERIFIED`
- `CONFLICT`

A manual review requires:

- exact claim key;
- reviewer identity;
- evidence note;
- optional source reference;
- timestamp.

Manual reviews are explicitly removable.

### Critical authority rule

Manual review **cannot assign `PROVEN`**. It has:

- `deterministic_proof_override: false`
- `publication_authority: false`

The overlay records accountable human research. It does not rewrite adapter output, generalized claims, installed-game evidence, or website publication decisions.

## Bounded evidence bundles

Reviewers may export research-only bundles for selected claim keys. Bundles are bounded by claim/evidence limits and contain:

- entity identity;
- selected claim;
- requirement assessment;
- exact-record navigation;
- dependency/consumer leads.

They never contain publication authority.

## AI boundary

AI may:

- summarize an assessment;
- explain missing requirements;
- prioritize review items;
- suggest exact identifiers or owner tables to investigate.

AI may not:

- assign `PROVEN`;
- invent an evidence edge;
- override deterministic assessment;
- convert a manual review into deterministic proof;
- publish automatically.

## Exit criteria

Phase 12 is complete when:

1. every unresolved/partial/conflicting claim produces an actionable review reason;
2. requirements are individually visible;
3. review items can be filtered by domain and ordered by launch impact;
4. shared missing owners/reasons are grouped;
5. exact source records and consumer-search leads are exposed;
6. manual verification/conflict records are attributable and removable;
7. bounded evidence bundles can be exported;
8. no review operation can assign deterministic `PROVEN` or publication authority.
