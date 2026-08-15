# Dead Signal Data Intelligence

Dead Signal Data Intelligence is the Miner’s read-only research workstation for investigating Once Human’s extracted NeoX/NXPK data without weakening the publication rules used by Dead Signal DB.

It is deliberately separate from the canonical extraction and web-projection path. The normal Miner finishes its authoritative snapshot first. Data Intelligence then analyzes that completed snapshot and writes research artifacts. A research failure is reported by Pipeline Inspector but does not invalidate an otherwise healthy canonical extraction.

## Branded workspace

The existing Miner research entry opens **DEAD SIGNAL / DATA INTELLIGENCE**. The workspace currently contains:

- **NeoX Explorer** — browse extracted structured tables, exact record IDs, and flattened properties across base/current layers.
- **Table Profiler** — field coverage, repeated scalar values, identity-like fields, description-like fields, rare fields, record shapes, and base/current schema deltas.
- **Source Finder** — ranked Weapon Description candidates inherited from exact installed-client identity traces.
- **Evidence Graph** — graph whose edges are created only by exact extracted identifiers and exact Reference Tracer occurrences.
- **Identity Map** — focused Weapon → ID family → table occurrence map.
- **Analytics** — embedded DuckDB warehouse with Polars transformations and Arrow interchange. SQLite Reference Tracer remains identity authority.
- **Workflow Lab** — constrained read-only research nodes such as exact-ID extraction, exact-reference search, exact-record opening, field filtering, translation resolution, and shared-value checks.
- **Pipeline Inspector** — high-level Miner phase timing plus individual module/status telemetry and produced research artifacts.
- **Publication Gate** — advisory eligibility decisions; it never rewrites public website datasets.
- **Discovery** — schema clustering, field co-occurrence, structural outliers, and description hotspots. Discovery is always non-authoritative.
- **Verification** — explicit manual review registry used by Publication Gate. Only user action can create a `VERIFIED` or `CONFLICT` review.

The original exact-evidence Research Console remains available from Data Intelligence for deep tracing.

## Evidence states

Dead Signal keeps these concepts mechanically separate:

1. **EXTRACTED** — a raw value exists in installed-game data.
2. **RESOLVED** — a reference/translation target resolves.
3. **CANDIDATE** — exact identity plus non-conflicting signals make a value worth review.
4. **VERIFIED** — independent evidence has been explicitly reviewed and recorded.
5. **CONFLICT** — sources disagree, a handle is cross-wired/shared in an unsafe way, or manual review found contradictory evidence.
6. **UNRESOLVED** — no sufficient evidence path exists yet.

`PUBLISHABLE` is not an evidence state. It is a separate Publication Gate decision made only when the policy for a field is satisfied.

## Weapon Description policy

For `weapon.description`, Publication Gate currently requires:

- candidate is not conflicted;
- candidate is not shared across multiple Weapon identities;
- manual verification state is `VERIFIED`;
- verification includes `exact_identity`;
- verification includes `independent_source`.

Source Finder, Analytics, Discovery, Evidence Graph, and Workflow Lab **cannot** assign `VERIFIED`.

Manual verification is stored at:

```text
<miner-output>/research/verifications.json
```

Gate review is written to:

```text
<miner-output>/published/reports/dead-signal-publication-gate.json
```

Even a `PUBLISHABLE` gate decision is advisory today. There is intentionally no automatic path from the gate into `published/web/weapons.json`; an explicit projector change must be reviewed separately before any newly verified description can become player-facing.

## Automatic post-run research products

After a successful canonical Miner snapshot, Data Intelligence attempts to produce:

```text
published/reports/
├── weapon-description-identity-investigation.json
├── weapon-description-source-investigation.json
├── dead-signal-source-finder.json
├── dead-signal-table-profiles.json
├── dead-signal-research-suite.json
├── dead-signal-publication-gate.json
├── dead-signal-discovery.json
└── dead-signal-pipeline-inspector.json

catalogs/
└── dead-signal-analytics.duckdb
```

The post-run analyzers are non-publishing and non-fatal. Missing optional analytical runtime support should appear in Pipeline Inspector / self-test rather than silently changing canonical output.

## Analytics architecture

The responsibilities are intentionally divided:

- **SQLite Reference Tracer** — exact scalar occurrence authority.
- **DuckDB** — local analytical SQL warehouse.
- **Polars** — fast dataframe transformation before analytical import.
- **PyArrow** — interchange between dataframe and DuckDB layers.

Analytical SQL is read-only. Data Intelligence accepts `SELECT`, `WITH`, `DESCRIBE`, `SHOW`, and `EXPLAIN` queries; it does not expose mutation statements.

## Discovery policy

Discovery can answer questions such as:

- Which NeoX tables have similar field structures?
- Which field pairs commonly co-occur?
- Which tables contain unusual record shapes?
- Which tables contain both identity-like and description-like fields?

Those results are **leads only**. They cannot create graph edges, verification records, or publication decisions.

## Workflow Lab policy

Workflow Lab executes only a maintained allow-list of deterministic Dead Signal nodes. Its default Weapon Description Trace is:

```text
Weapon Input
  → Extract Exact IDs
  → Find Exact References
  → Open Exact NeoX Records
  → Filter Description-like Fields
  → Resolve Translation
  → Check Shared Values
  → Evidence Result
```

The result remains `CANDIDATE`/`UNRESOLVED` and `BLOCKED` pending independent manual verification.

## Safety boundary

The intended flow is:

```text
GAME FILES
  → RAW EXTRACTION
  → NORMALIZED DATA
  → EXACT EVIDENCE
  → RESEARCH / DISCOVERY
  → MANUAL VERIFICATION
  → PUBLICATION GATE
  → EXPLICIT PROJECTOR CHANGE
```

Never:

```text
similarity / clustering / ML guess → website
```

This boundary applies to future categories as Data Intelligence expands beyond Weapon Descriptions.
