# Evidence Graph Phase 0 Compatibility Contract

This contract freezes the current Weapons v1 Evidence Graph before generalized entity and adapter work begins.

## Protected behavior

- `weapon_graph(identity)` continues to return schema `dead-signal-evidence-graph`.
- The payload retains `schema`, `schema_version`, `brand`, `subject`, `record_counts`, `nodes`, `edges`, and `policy`.
- `subject.type` remains `weapon` for the legacy entry point.
- A weapon root node remains present.
- Exact graph edges remain authoritative and provenance-backed.
- Discovery and similarity cannot create edges.
- Graph presence never grants automatic publication permission.
- Missing identities remain unresolved rather than disappearing.
- Output ordering and canonical hashing remain deterministic for the same snapshot.

## Representative cohorts

The committed baseline covers:

- SOCR - The Last Valor — standard ranged control;
- Baseball Bat — melee applicability control;
- Morgan — nonstandard-blueprint control;
- Ultra Force — special-equipped control;
- AKM — no-fixed-skill-reference control.

The fixture IDs are exact installed identities. They are regression subjects, not a hard-coded corpus definition.

## Performance policy

Observed trace time, node count, edge count, occurrence count, artifact size, and graph hash describe the captured local snapshot. They are not universal constants and do not fail CI merely because installed data changes.

Semantic compatibility failures do fail tests. Performance regressions must be reviewed against the committed observation before a release, with cold/warm timing and snapshot fingerprints recorded.

## Phase 1 rule

Generalized entities and domain adapters may extend the schema through new versioned entry points. They must not silently change or remove this legacy Weapons v1 contract. An intentional incompatible change requires a schema-version change, migration notes, regression updates, and explicit approval.
