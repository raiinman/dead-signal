# Dead Signal — Current Handoff

Current operational handoff:

- `HANDOFF-2026-08-18-EVIDENCE-GRAPH-EXPANSION-PHASE-0.md`

Approved implementation plan:

- `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md`

Read order for a new engineering/research session:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-2026-08-17-MINER-ARCHITECTURE-UPGRADE.md`
4. `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`
5. `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY.md`
6. `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY-COMPLETE.md`
7. `HANDOFF-2026-08-18-WEAPON-IDENTITY-SPINE-TRACE.md`
8. `HANDOFF-2026-08-18-CODEX-WEAPON-IDENTITY-SPINE-IMPLEMENTATION.md`
9. `HANDOFF-2026-08-18-WEAPON-IDENTITY-SPINE-COMPLETE.md`
10. `HANDOFF-2026-08-18-WEAPON-LAUNCH-WARNINGS-AND-ATTACHMENTS.md`
11. `HANDOFF-2026-08-18-WEAPONS-V1-SCHEMA-LOCK.md`
12. `HANDOFF-2026-08-18-MINER-IDENTITY-TRACE-WORKSPACE.md`
13. `HANDOFF-2026-08-18-NORMAL-GPT-EVIDENCE-FIRST-MINER.md`
14. `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md`
15. `HANDOFF-2026-08-18-EVIDENCE-GRAPH-EXPANSION-PHASE-0.md`

For current operational state, the Evidence Graph Expansion Phase 0 handoff is authoritative. Phase 0 is complete and Phase 1 is next. The Weapons v1 Schema Lock remains authoritative for evidence semantics; older handoffs remain evidence history and design rationale.

Key current transition:

- local Codex now has direct access to the user's completed Miner output and persistent architecture databases;
- use local files/indexes rather than asking the user to upload multi-gigabyte Intelligence bundles;
- the Weapon Identity Spine is implemented from current `item_data + equip_data` identity with blueprint/progression as conditional enrichment;
- the current source-derived `.62` result is 130 identities: 117 standard-blueprint, 7 nonstandard-blueprint, and 6 special-equipped; this is observed output, not a hard-coded or universal active count;
- all 130 identities carry gated exact/unresolved/not-applicable relationships for 87 active Cradles and reach downstream site publication;
- scenario activation remains unresolved for the six special-equipped identities;
- use the persistent indexes and the exact consumer trace in the new handoff before running any new scan;
- do not reopen the ownerless fixed-skill branch unless new typed installed-game evidence changes its state.
- ten melee recipes now have exact seasonal formula owners while their material bodies remain unresolved;
- Morgan has an exact one-level Blueprint Star owner while its gear-tier owner remains unresolved;
- attachment compatibility publishes only direct installed-game text plus explicit generic category claims; named-model wording is not guessed into IDs;
- Calibration compatibility and selectable Ammo are projected from exact typed owners;
- Weapons v1 is schema-locked; change its core identity/relationship contract only when new installed-game evidence requires a revision;
- stable Miner release is `v1.5.14.64`; it opens directly on the first-class Evidence Graph workspace;
- `.63` nested the new workspace too deeply; `.64` corrected that and passed the complete manifest-last release workflow;
- `tools/miner.zip` remains protected and untouched.
