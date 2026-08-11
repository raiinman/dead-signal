# Dead Signal // Visual Bible

## Design target

**Dark tactical workstation with controlled colored instrumentation layered over the existing planner flow.**

Dead Signal should feel dark, tactical, precise, dangerous, technical, and readable. It should not feel like generic cyberpunk, corporate SaaS, a wiki with red paint, or a neon casino.

## 80 / 20 rule

Preserve roughly 80% of the existing Build Lab structure and workflow. Improve the remaining 20% through hierarchy, section identity, spacing, depth, status feedback, and restrained motion.

Do not redesign the planner simply because a new visual treatment is possible.

## Color semantics

### Brand

- Signal Red: `#E6323E`
- Deep Signal Red: `#761820`
- Signal wash: `rgba(230, 50, 62, 0.10)`

Use for Dead Signal identity, primary actions, selected navigation, strong focus, and important alerts.

### Rarity colors are item-only

Rarity colors belong to game-item meaning and must not become section colors.

In particular, **gold / amber is reserved for Legendary item meaning**. Do not use gold or amber as Weapons, Armor, section-header, or navigation identity.

The same principle applies to saturated rarity blue and purple: section accents should be cooler, darker, and less saturated than item rarity colors.

### Structural section accents

- Global / Plan: Signal Red `#E6323E`
- Weapons: Gunmetal Blue `#58778C`
- Calibration / technical data: Technical Cyan `#39BFC6`
- Armor: Cold Steel `#718394`
- Mods / notes / analysis support: Muted Indigo `#6A6F9C`
- Deviations / build systems: Deep Teal `#388C82`
- Report / compare / tooling: Instrument Blue `#527EAD`

Structural colors identify location. Rarity colors identify the item.

## Surface ladder

Adjacent interface layers should not use the exact same darkness.

- Void: `#050709`
- Background: `#070A0D`
- Workspace: `#090D11`
- Panel: `#0D1318`
- Raised card: `#121920`
- Interactive raised: `#172129`
- Divider: `#26313A`

## Section grammar

Every major Build Lab section should share one structure:

1. Section number / identifier
2. Small technical eyebrow
3. Human-readable title
4. Optional one-line purpose
5. Status at the opposite edge
6. Thin structural accent rail or top line

Use color as instrumentation: rails, small icons, headings, status details, restrained inner tints. Do not fill entire sections with loud color.

## Information priority

Every important card should answer, in this order:

1. What is it?
2. What state is it in?
3. What does it do?
4. What can the player change?
5. What detail is secondary?

Vital mechanical information must never be visually treated like footnote text.

## Calibration language

Calibration uses Technical Cyan structurally because it is one of Dead Signal's strongest technical differentiators.

Deterministic and RNG information should look distinct:

- Fixed / deterministic information: solid cyan rail / border treatment
- Player RNG information: dashed or segmented cyan treatment

Do not mix the deterministic fixed Style effect with the random roll controls into one undifferentiated block.

## Build modes

### MY GEAR // ACTUAL BUILD

Cool-neutral workstation treatment. Uses player-entered account/server RNG.

### GOD ROLL // THEORETICAL BUILD

Use Signal Red + white with a subtle hatch or analytical pattern. Do **not** use Legendary gold to represent God Roll.

The mode difference must be unmistakable but should not become a completely separate website theme.

## Status language

Use color because status has meaning, not for decoration.

- READY / VALID / CONNECTED: restrained teal-green
- NEEDS INPUT / INVALID / MISSING RNG: Signal Red / warning red
- LIVE DATA: restrained teal-green with a small indicator
- SNAPSHOT / FALLBACK: neutral steel

Never fabricate social or operational numbers simply to make the UI look busy.

## Motion

Allowed:

- 1–2 px hover lift
- short border-brightening transition
- nav underline / active rail transition
- status fade between states
- brief data-update flash
- short picker opacity / scale transition

Avoid:

- constant pulsing
- floating cards
- rotating decorative icons
- moving rainbow gradients
- animation that makes the planner tiring during long sessions

Dead Signal should feel alive through **response**, not constant movement.

## Data trust rule

If Dead Signal displays a number as factual, we should be able to prove where it came from.

Prefer real mined / normalized corpus counts and clearly labeled live-vs-snapshot states. Never invent online-user counts, build counts, ratings, DPS, or performance metrics for visual effect.

## One-line design test

> Does this make the information easier to understand while making Dead Signal feel more alive?

If a change only makes the interface prettier, it is optional. If it improves information hierarchy and personality together, it belongs in the system.
