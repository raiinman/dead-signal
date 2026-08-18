# Dead Signal — Current Handoff

Current operational handoff:

- `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`

Read order for a new engineering/research session:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-2026-08-17-MINER-ARCHITECTURE-UPGRADE.md`
4. `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`

For current operational state, the 2026-08-18 Codex local takeover handoff supersedes older Miner/Weapons handoffs where they conflict. Older handoffs remain evidence history and design rationale.

Key current transition:

- local Codex now has direct access to the user's completed Miner output and persistent architecture databases;
- use local files/indexes rather than asking the user to upload multi-gigabyte Intelligence bundles;
- first priorities are validating the post-v1.5.14.61 architecture, fixing the ~6 GB shareable Intelligence export, bounding the oversized snapshot diff, and then using the local indexes to close remaining launch blockers;
- do not reopen the ownerless fixed-skill branch unless new typed installed-game evidence changes its state.
