# WizardRoguelike — Claude Code Project Guide

## Quick Start
```bash
cd /home/ryan/Documents/WizardRoguelike
. .venv/bin/activate
python -m game.main          # Play the game
python -m pytest tests/ -q   # Run 1000+ tests
```

## What This Is
A tactical roguelike inspired by Rift Wizard 2, with a **spell crafting system** as the core differentiator. Instead of buying premade spells, players combine Elements + Shapes + Modifiers to create spells. The game is built with Python/Pygame-ce and uses RW2's art assets (symlinked) during development.

## Project Principles

### DO
- Use RW2 as the template for game design decisions (not standard roguelike conventions)
- Keep all game logic pygame-free (core/, crafting/, content/, generation/, ai/, game/ have ZERO pygame imports)
- Write tests for every new system — target >90% coverage on core + crafting
- Use the existing tag_bonuses stat pipeline for new bonuses (don't create parallel systems)
- Use generator-based spell execution (cast() yields between animation frames)
- Use deterministic hashes (not random.random()) for AI behavior to support replays
- Keep the Game.get_state() API complete for headless Claude Code players

### DON'T
- Make standard roguelike rooms+corridors — levels use RW2-style fill → mutate → validate (see terrain.py)
- Hardcode damage/stat values in tests — use component references (FIRE.base_damage, not 12)
- Apply stat modifiers in both _apply_modifier_stats() AND get_stat() — that's the Empowered double-apply bug (already fixed)
- Use random.random() in game logic — use GameRNG or deterministic hashes for reproducibility
- Add pygame imports to non-rendering modules

## Architecture Overview

### Directory Structure
```
src/game/
  core/          # Engine (ZERO pygame) — Level, Unit, Buff, Spell, Events, Shapes
  crafting/      # Spell crafting — Components, CraftedSpell factory, Synergies, Masteries
  content/       # Game content — elements/, shapes/, modifiers/, monsters/, equipment, consumables
  generation/    # Level gen — RW2-style terrain.py, biomes, populator
  ai/            # Monster AI — role-based behavior (melee/ranged/caster/boss)
  game/          # Game state — Game class, save/load, SP economy
  rendering/     # Pygame rendering (ONLY package with pygame imports)

tests/
  unit/          # Fast isolated tests
  integration/   # Multi-system chains
  crafting/      # Combinatorial (all Element×Shape pairs)
  generation/    # Connectivity, determinism
  property/      # Hypothesis fuzz tests
  simulation/    # Headless bot, Claude judge
  replay/        # Recorder/replayer
```

### Key Files
| File | Purpose |
|------|---------|
| `core/level.py` | Grid, damage pipeline, turn structure (iter_frame), FOV, pathfinding |
| `core/unit.py` | Entity with stat pipeline (get_stat), buff management, AI dispatch |
| `core/buff.py` | Buff system with 4 stack types, symmetric apply/unapply |
| `core/spell_base.py` | Spell base class with generator-based cast() |
| `crafting/components.py` | Element, Shape, Modifier dataclasses + registries |
| `crafting/spell_factory.py` | CraftedSpell — composes spells from components at runtime |
| `crafting/synergies.py` | Element-pair combo bonuses |
| `crafting/component_upgrades.py` | Mastery tiers (element + shape upgrades) |
| `generation/terrain.py` | RW2-style fill → mutate → validate terrain generation |
| `generation/level_generator.py` | Full level pipeline (terrain → populate) |
| `ai/base_ai.py` | Role-based monster AI with flee/kite/tactical casting |
| `game/game_state.py` | Game class — run management, SP economy, get_state() API |
| `game/serialization.py` | JSON save/load between levels |
| `rendering/renderer.py` | Pygame renderer (RW2-style panel layout) |
| `rendering/ui_shop.py` | Clickable shop UI with craft preview |
| `main.py` | Entry point — title screen → shop → level → game over |

### Spell Crafting System
A spell = Element + Shape + 0-2 Modifiers.

**Elements** (8): Fire, Ice, Lightning, Dark, Holy, Nature, Arcane, Poison
- Each has base_damage, secondary effect (burn DOT, freeze, stun, lifedrain, etc.)
- Defined in `crafting/components.py`, handlers in `content/elements/`

**Shapes** (11): Bolt, Burst, Beam, Cone, Orb, Touch, Self, Summon, Chain, Wall, Nova
- Each has base_range, base_radius, base_charges
- Handlers in `content/shapes/` provide cast() generators and get_impacted_tiles()

**Modifiers** (11): Empowered, Extended, Lingering, Splitting, Channeled, Homing, Piercing, Volatile, Quickened, Widened, Vampiric
- Modify stats (damage mult, range bonus) or add post-hit effects
- Incompatibility rules prevent broken combos (e.g., Homing + Self)

**Stat Pipeline**: `Unit.get_stat(base, spell, attr)` applies:
- global_bonuses (from equipment, masteries)
- tag_bonuses (from synergies, element masteries)
- Percentage variants of both
- Modifier stat adjustments via modify_stats() in CraftedSpell.get_stat()

### Damage Pipeline
`Level.deal_damage(x, y, amount, damage_type, source)`:
1. Find unit at tile (or damageable prop like Lair)
2. Check damage instance cap (prevents infinite loops)
3. Apply resistance (with pierce reduction from source)
4. Check shields
5. Cap damage to current HP
6. Apply damage, fire EventOnDamaged
7. Kill check → fire EventOnDeath

### Turn Structure (iter_frame generator)
1. Drain spell animation queue
2. Increment turn, reset per-turn state
3. Cache unit list (new summons don't act this turn)
4. Player phase: wait for input → execute action → drain spells → advance buffs
5. Enemy phase: AI decision → execute action → drain spells → advance buffs
6. Advance props (lairs) and clouds
7. Cleanup dead units, tick temporary summons
8. yield True (turn complete)

### Level Generation (RW2-style)
NOT rooms+corridors. Uses `generation/terrain.py`:
1. Fill grid with walls
2. Apply 1-3 seed mutators: paths, lumps, noise, squares, grid
3. Apply 0-2 modifiers: cellular_automata, symmetry, border, expand, pillars
4. Validate: min 50 floors, min 100 walls
5. Ensure connectivity via flood-fill + path carving
6. Populate: player → exit → monsters (on reachable tiles only)

### Monster AI (ai/base_ai.py)
Role-based with intentional imperfection (35% chance to just rush):
- **MELEE**: Rush toward target
- **RANGED**: Maintain distance, kite, strafe
- **CASTER**: Stay at max spell range
- **BOSS**: Use abilities on cooldown, aggressive

### Headless Game API (for Claude Code players)
```python
game = Game(seed=42)
game.buy_component("element", "Fire")
game.craft_spell("Fire", "Bolt")
game.start_level()
state = game.get_state()  # Full game state as dict
result = game.submit_action(CastAction(spell, x, y))
```

`get_state()` returns: player stats, spell list, tile grid with FOV, available_actions (valid moves + castable spells with target lists), equipment, synergies, masteries, consumables.

## Testing
```bash
pytest tests/ -q                      # All tests (~2.5s)
pytest tests/ -m "not slow"           # Skip simulation sweep
pytest tests/simulation/ -v -m ""     # Full bot sweep
pytest tests/property/ -v             # Hypothesis fuzz
```

## Balance (as of 2026-03-29)
- Elements: Fire 12, Ice 10, Lightning 14, Dark 11, Holy 11, Nature 9, Arcane 16, Poison 8
- Player: 150 HP, 10 starting SP, 5 SP/level
- Bolt 8 charges, Burst 5, Beam 6, Touch 16, Cone 3
- Smart bot achieves avg 3.3/5 levels (challenging for humans, winnable with good play)
- Lairs only on final level (level 5)

## Content Totals
- 8 elements, 11 shapes, 11 modifiers = 968+ base spell combos
- 41 monsters (tier 1-3, variants, special with unique mechanics)
- 20 equipment, 6 consumables, 7 synergies, element/shape masteries
- 5 biomes, RW2-style terrain generation

## Known Issues / TODO
- Sound/music not implemented (planned: Suno + ElevenLabs)
- Using RW2 art assets (planned: ComfyUI 32x32+ hand-painted)
- Only 5 levels (framework supports more)
- No meta-progression between runs
- Lairs need smarter bot interaction (bot can't pathfind to destroy them well)
- Some Hypothesis tests are flaky due to terrain generation randomness
