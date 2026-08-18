# Dead Signal — Current Handoff

Current operational handoff:

- `HANDOFF-2026-08-18-CODEX-WEAPON-IDENTITY-SPINE-IMPLEMENTATION.md`

Read order for a new engineering/research session:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-2026-08-17-MINER-ARCHITECTURE-UPGRADE.md`
4. `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`
5. `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY.md`
6. `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY-COMPLETE.md`
7. `HANDOFF-2026-08-18-WEAPON-IDENTITY-SPINE-TRACE.md`
8. `HANDOFF-2026-08-18-CODEX-WEAPON-IDENTITY-SPINE-IMPLEMENTATION.md`

For current operational state, the Weapon identity-spine implementation handoff supersedes older Miner/Weapons handoffs where they conflict. Older handoffs remain evidence history and design rationale.

Key current transition:

- stable Miner release boundary remains `v1.5.14.62`;
- local Codex has direct access to the completed Miner output and persistent architecture databases;
- use local files/indexes rather than asking the user to upload large Intelligence workspaces;
- the old 120 Weapon set was produced by blueprint-first admission and is no longer assumed to equal installed Weapon identity;
- the completed trace found an installed union of 132 credible Weapon identities, but 132 is an evidence boundary, not a hard-coded target and not proof of universal simultaneous scenario availability;
- the next canonical engineering task is to rebase Weapon discovery on current `item_data + equip_data + equip_origin_data`, use achievement family data only as corroboration, and treat blueprint/progression/craftability/availability as separate evidence states;
- after the canonical Weapon identity set changes, recompute Cradle applicability and all downstream publication/readiness/diagnostic counts;
- do not hard-code the external catalog or its count;
- do not reopen the ownerless fixed-skill branch unless new typed installed-game evidence changes its state;
- do not cut a new Miner release until the identity model, downstream recomputation, publication and tests form a coherent release boundary;
- `tools/miner.zip` remains protected and must stay untouched.
