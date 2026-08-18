# Dead Signal — Codex Handoff: Weapon Cradle Applicability

> **Canonical repo:** `raiinman/dead-signal`
> **Branch:** `main`
> **Date:** 2026-08-18 America/Phoenix
> **Current canonical boundary:** `c1031be`
> **Stable Miner:** `v1.5.14.62`
> **Release source commit:** `386e05a`
> **Updater commit:** `11ea607`
> **Release workflow:** `32152160998` — SUCCESS
>
> Read this handoff after `PROJECT-RULES.md` and `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`.

---

# Objective

Continue the **Weapons launch lane**. Do not pivot into a general Cradle project.

The immediate target is:

> **Prove, from installed Once Human evidence, exactly how Cradle effects become applicable or incompatible with individual weapons, then integrate that result into the authoritative Weapons publication pipeline.**

Cradle compatibility/applicability is being investigated because it is a missing player-facing relationship on weapon records.

Do not begin Attachment, Calibration, Ammo, Acquisition, Melee, or Variant-lineage work until this lane is either solved or explicitly blocked by exact evidence.

---

# Current release state

The Miner architecture/release boundary is clean.

- Canonical GitHub `main`: `c1031be`
- Stable Miner: `v1.5.14.62`
- Tag: `miner-v1.5.14.62`
- GitHub Actions run `32152160998`: SUCCESS
- Source tests: 184 passed
- Focused Intelligence tests: 7 passed
- Windows build: passed
- Packaged self-test: passed
- Release asset verification: passed
- ZIP size: `133,611,898` bytes
- SHA-256: `82956c1a25e25974907c96d656c3200a69a3d94d8a9264420914ab00343c8356`
- Stable updater manifest points to the verified `.62` release asset
- `tools/miner.zip` remains untouched/uncommitted

Do not spend this session reworking the `.62` release boundary unless a Cradle investigation exposes a real architecture defect.

---

# Why this is the next Weapons blocker

Dead Signal already has:

- 120 weapons
- 170 Cradle records in normalized data
- the new persistent table registry
- the persistent static PYC consumer index
- the persistent typed reference graph
- the analytics warehouse
- semantic registry / publication infrastructure

The missing player-facing question is not merely “what Cradles exist?” It is:

> **For a given weapon, which Cradle effects apply, which do not, and what exact installed-game condition proves that result?**

Do not infer compatibility from English wording or community classifications.

Examples of unacceptable inference:

- “This says Shotgun, therefore every Shotgun is compatible.”
- “This is a rifle Cradle, therefore it must apply to Assault Rifles and Snipers.”
- “The IDs look similar, therefore they are related.”
- “A Cradle record exists, therefore it is currently active.”

Compatibility must be reconstructed from the data and the static consumer logic.

---

# Local-first rule

Codex has direct access to the user's completed local Miner output. Use it.

Primary local output:

```text
C:\Users\mikea\Documents\Dead Signal Miner
```

Use the persistent local architecture directly rather than generating another broad forensic export:

```text
catalogs\dead-signal-table-registry.sqlite
catalogs\dead-signal-consumer-index.sqlite
catalogs\dead-signal-reference-graph.sqlite
catalogs\dead-signal-analytics.duckdb
```

Also use the already-mined Base/Current snapshots and relevant published/research JSON when an exact record must be inspected.

The guiding principle remains:

> **Query the local persistent architecture first. Inspect source records second. Run a new bounded analyzer only if the indexes cannot answer the exact question. Do not launch another full-corpus brute-force scan.**

---

# Known Cradle evidence / leads

Prior work surfaced the following Cradle-related installed-data leads. Treat these as starting points, not finished semantics.

Known normalized state:

- 170 Cradle records
- prior research observed approximately 94 active/current config references

Previously surfaced client-data tables include:

```text
client_data/cradle_mesh_map.json
client_data/cradle_override_style_data.json
client_data/cradle_tip_effect_data.json
```

Previously surfaced high-value static consumer leads include:

```text
UIEquipmentData.pyc
  cradle_override_entry
  gun_type
  key_word_no
  key_word_lst

entities/clientavatar_members/impEquip.pyc
  cradle_override
  weapon_type
```

Do not assume these symbols alone establish applicability. Reconstruct the exact code-scope logic and exact data owners.

---

# Required research sequence

## 1. Establish the exact Cradle data model

Use the table registry and exact source inspection to identify the tables/records that define:

- Cradle identity
- active/current Cradle configuration
- Cradle effect / skill / buff identity
- override entry / override style
- weapon selector fields
- gun-type / weapon-type fields
- keyword-number / keyword-list fields
- any inclusion/exclusion or scenario/version gating

Separate:

- active/current records
- historical/legacy records
- generic presentation records
- player-facing effect records

Do not use record count alone as evidence of current applicability.

Produce a concise local research artifact describing the proven Cradle data model and exact owner fields.

## 2. Query the Consumer Index

Query exact code scopes for at least:

```text
cradle_override
cradle_override_entry
weapon_type
gun_type
key_word_no
key_word_lst
```

Also follow any exact symbols/functions returned by those scopes.

Inspect code objects/scopes statically. Never execute game bytecode.

The objective is to recover the actual branching/condition logic used by the client for applicability.

For every meaningful condition, record:

- PYC relative path
- function/qualname
- relevant co_names / co_varnames / string constants / safe instruction evidence
- exact data field(s) consumed
- exact comparison/membership relationship if statically recoverable

## 3. Reconstruct selector semantics

Determine whether Cradle applicability depends on one or more of:

- weapon category
- internal `weapon_type`
- internal `gun_type`
- keyword membership
- keyword exclusion
- Cradle override entry
- style/entry mapping
- active configuration state
- scenario/season gating
- another exact installed field discovered during the trace

Do not assign English meaning to raw enum/integer values until an installed-data or static-consumer proof path exists.

If a selector remains only a raw code, keep it raw and unresolved rather than guessing.

## 4. Prove controls before scaling

Before generating any 120-weapon mapping, choose a small set of weapons that exercises distinct categories/types and prove compatibility manually through the reconstructed logic.

At minimum include controls from several different classes, such as:

- one Assault Rifle
- one Shotgun
- one Sniper Rifle
- one SMG
- one LMG
- one Pistol
- one Bow/Crossbow if applicable
- one Melee weapon if the logic can reach melee

Use canonical Dead Signal weapons and exact local records.

For each control, produce evidence in this shape:

```text
Weapon
→ exact weapon/gun/type/keyword record(s)
→ exact Cradle selector record
→ exact consumer condition
→ COMPATIBLE / NOT COMPATIBLE / UNRESOLVED
→ evidence provenance
```

A negative result must be proven by the condition logic; absence of a join alone is not enough unless the consumer explicitly makes absence decisive.

## 5. Scale only after controls agree

Once the selector semantics are proven, generate the full weapon × Cradle applicability mapping.

The output must distinguish at least:

- `compatible-exact`
- `incompatible-exact`
- `not-applicable`
- `unresolved`

Do not collapse unresolved into incompatible.

Prefer a normalized relationship representation over a giant 120 × 170 dense matrix if the same truth can be represented compactly through selector groups plus exact weapon membership.

## 6. Integrate into the persistent architecture

If the rule is proven, encode it so Dead Signal remembers it after future patches.

Expected integration may include, as appropriate:

- semantic registry definition(s)
- typed reference graph relation(s)
- family/selector registry if genuinely useful
- dependency invalidation for relevant source tables/PYC consumers
- coverage dashboard field
- self-diagnostic checks
- website delta detection

Do not hard-code a one-off list of compatible weapon names if an exact installed selector relationship exists.

## 7. Integrate into Weapons publication

The end product is a **weapon relationship**, not merely a research report.

Update the authoritative weapon publication path so the website/build planner can consume proven Cradle applicability without importing research-only noise.

Publication must preserve evidence gating and should expose enough provenance in the evidence sidecar for later verification.

Do not bloat the lean browser feed unnecessarily.

## 8. Tests

Add focused regression tests for:

- selector decoding / relation construction
- at least one positive compatibility control
- at least one negative compatibility control
- unresolved values remain unresolved
- inactive/legacy Cradle records do not leak into active compatibility
- no broad scalar collision joins
- no sibling/family leakage
- publication does not promote unproven compatibility

Run the relevant focused tests and the full Miner source suite before pushing.

---

# Evidence doctrine — non-negotiable

- Installed Once Human data mined by Dead Signal is authoritative.
- External/community/reference sites are not evidence.
- Never execute game bytecode.
- Static PYC inspection is allowed.
- Never fuzzy-match IDs.
- Never promote bare scalar equality into ownership.
- Never global-join repeated integers/strings without typed field proof.
- Never infer missing relation = incompatible unless the consumer proves that behavior.
- Never infer current/active from existence alone.
- Never infer enum meaning from community parity.
- Local-over-shared precedence must be preserved where the game uses it.
- Sibling/family inheritance requires an exact allowed-domain rule; no leakage.
- If exact proof ends in a raw code, publish the raw code only if useful and leave the semantic label unresolved.

---

# Fixed-skill lane remains closed

Do not reopen the ownerless fixed-skill investigation during this session unless Cradle work unexpectedly returns new exact typed evidence that materially changes that state.

Current ownerless fixed-skill result remains:

```text
14 public weapon records
→ 11 unique fixed-skill codes
→ exact blueprint references exist
→ fixed-skill consumer/routing architecture exists
→ no alternate exact current passive owner proven
→ player-facing mechanic remains unresolved
```

This is not the current objective.

---

# Do not optimize the compiler yet

The old high-level Weapon forensic stages still rerun longer than ideal even when their low-level inputs are cached. That is a legitimate future optimization, but it is not this handoff's objective.

Do not interrupt the Cradle research lane to redesign `RUN CHANGED STAGES` unless the current investigation is genuinely blocked by a pipeline defect.

---

# Deliverables

Codex should finish this session with as many of the following as exact evidence supports:

1. A concise Cradle applicability research report.
2. Exact static-consumer proof for the applicability condition(s).
3. Exact mapping from relevant Cradle selectors to weapon selector fields.
4. Proven control examples across multiple weapon types.
5. Full active weapon-Cradle applicability relationships, if the rule is proven.
6. Persistent architecture integration.
7. Weapons publication integration.
8. Focused tests and full source-test results.
9. Small coherent commits pushed directly to canonical `main`.
10. An update appended to this handoff or the current takeover handoff summarizing:
    - what was proven
    - what remains unresolved
    - files/commits changed
    - test results
    - resulting Weapons coverage change
    - the next Weapons blocker

Do not cut a new Miner release merely because research code changed. Release only at a meaningful tested product boundary and only if the change needs to reach the user's installed Miner immediately.

---

# Definition of done

This lane is complete when Dead Signal can answer, for a player-facing weapon and active Cradle effect:

> **“Does this Cradle apply to this weapon?”**

with one of:

```text
YES — exact installed condition proves compatibility
NO — exact installed condition proves incompatibility
UNRESOLVED — installed evidence is insufficient
```

and that answer is generated through the canonical data/publication pipeline rather than manually curated guesswork.

After that, return to the Weapons launch queue. Likely next lanes are Attachment compatibility, Calibration compatibility, selectable Ammo, acquisition edge cases, melee display semantics, variant lineage, and the remaining description conflict — but choose the next lane based on the actual updated coverage dashboard, not assumptions.
