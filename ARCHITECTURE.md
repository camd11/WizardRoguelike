# Architecture Guide

## Design Philosophy

This game follows **Rift Wizard 2's design principles**:

1. **Combat only** — no exploration, inventory tetris, or story padding
2. **Total build freedom** — all spell components available from the start (purchased with SP)
3. **Simple AI, complex enemies** — monster variety > AI sophistication
4. **Tag-based synergies** — element/shape tags drive bonus interactions
5. **Generator-based spells** — `cast()` yields between animation frames for visual pacing
6. **Symmetric buff lifecycle** — bonuses accumulated on apply, reversed on unapply

## Module Dependency Graph

```
rendering/ ──→ game/ ──→ crafting/ ──→ core/
                │           │
                ├──→ generation/ ──→ core/
                │           │
                ├──→ content/ ──→ core/ + crafting/
                │
                └──→ ai/ ──→ core/
```

**Rule**: Only `rendering/` imports pygame. Everything else is pure Python.

## Core Engine (src/game/core/)

### Level (level.py)
The central game object. Owns the tile grid, unit list, event handler, and spell animation queue.

**Critical methods**:
- `deal_damage(x, y, amount, damage_type, source)` — THE damage pipeline. All damage goes through here.
- `iter_frame()` — Generator that drives the turn loop. Yields `False` (animation frame) or `True` (turn complete). Player actions come in via `.send()`.
- `act_cast(unit, spell, x, y)` — Queues a spell generator into `active_spells` deque.
- `advance_spells()` — Calls `next()` on each active spell generator. Uses `del` by index (NOT `.remove()` by value — that was a bug).
- `has_los(start, end)` — Bresenham line-of-sight check.
- `compute_fov(x, y, radius)` — tcod symmetric shadowcast.
- `find_path(x0, y0, x1, y1, flying)` — tcod A* pathfinding.

### Unit (unit.py)
An entity on the grid. Has HP, spells, buffs, resistances, and stat bonus accumulators.

**Stat pipeline** (`get_stat(base, spell, attr)`):
```
pct = global_pct + sum(tag_pct for matching tags in spell.tags)
abs = global_abs + sum(tag_abs for matching tags in spell.tags)
result = floor(base * (100 + pct) / 100) + abs
```

### Buff (buff.py)
Temporary or permanent effects. Stack types:
- `STACK_NONE` — reject second application
- `STACK_DURATION` — refresh duration
- `STACK_REPLACE` — remove old, apply new
- `STACK_INTENSITY` — allow multiple instances

**Lifecycle**: `on_init()` → `apply(owner)` → `advance()` (each turn) → `unapply()`

Bonuses are accumulated into owner's `global_bonuses`, `tag_bonuses`, `resists` on apply and reversed on unapply. This symmetry is CRITICAL — breaking it causes stat leaks.

### Events (events.py)
Event dispatcher with entity-specific + global triggers. **Snapshot-safe**: handler list is copied before iteration to prevent mutation during dispatch.

Key events: `EventOnDamaged`, `EventOnDeath`, `EventOnSpellCast`, `EventOnMoved`, `EventOnBuffApply`

### Shapes (shapes.py)
Geometry iterators for spell targeting: `bolt()`, `burst()`, `beam()`, `cone()`. Each yields lists of Points per "stage" (animation ring). The shape content handlers (`content/shapes/`) use these to implement `cast()` generators.

## Spell Crafting (src/game/crafting/)

### CraftedSpell (spell_factory.py)
The core class. Constructed from Element + Shape + 0-2 Modifiers.

**IMPORTANT**: Damage multipliers (Empowered) are applied ONLY in `get_stat()` via `modify_stats()`, NOT in `_apply_modifier_stats()`. The latter only handles non-stat-pipeline values (radius bonus, charges, duration). This prevents the Empowered double-apply bug.

**Cast flow**:
1. `cast(x, y)` — entry point, handles homing retarget + channeling
2. `_shape_cast(x, y)` — delegates to shape handler's `cast()`
3. Shape handler iterates geometry, calls `level.deal_damage()` per hit point
4. After each hit: `_apply_element_secondary()` and `_apply_modifier_effects()`

### Components (components.py)
Frozen dataclasses: `Element`, `Shape`, `Modifier`. All registered in `ELEMENTS`, `SHAPES`, `MODIFIERS` dicts. Adding a new component:
1. Add the dataclass instance to components.py
2. Create handler module in content/elements/ or content/shapes/ or content/modifiers/
3. Register in the __init__.py handler lookup
4. Add pseudo-tag to constants.py if it's a shape (for mastery bonuses)

### Synergies (synergies.py)
Passive bonuses that activate when player owns two specific elements. Applied as permanent SynergyBuff. Checked on every component purchase.

### Masteries (component_upgrades.py)
Tiered upgrades for owned components. Element Mastery I/II/III adds tag_bonuses. Shape Mastery adds range/radius/damage. Applied as permanent MasteryBuff.

## Content (src/game/content/)

### Element Handlers (elements/*.py)
Each provides `apply_secondary(spell, level, x, y)` — called after damage on each hit tile. Examples: fire.py applies BurnBuff, ice.py applies FreezeBuff, lightning.py 25% chance StunBuff.

### Shape Handlers (shapes/*.py)
Each provides `cast(spell, x, y) -> Generator` and `get_impacted_tiles(spell, x, y) -> list[Point]`. Cast generators iterate geometry, deal damage, and call element/modifier hooks.

### Modifier Handlers (modifiers/*.py)
Each provides `modify_stats(spell, stats) -> stats` (for stat adjustments) and `apply_effect(spell, level, x, y)` (for post-hit effects). `modify_stats` must check if the relevant key exists in stats dict.

### Monsters
Factory functions that return configured Unit instances. Tiers:
- **tier1.py**: Basic enemies (Rat, Skeleton, Slime, Goblin, Imp)
- **tier2.py**: Mid-game (Fire/Ice Elemental, Orc Warrior, Dark Mage, Young Dragon)
- **tier3.py**: Bosses with unique mechanics (Lich Lord, Fire Dragon, Orc Warlord, Spider Queen, Storm Elemental)
- **variants.py**: Elemental variants + special types (11 monsters)
- **special.py**: Unique mechanics — auras, summoners, explosive, shield, multi-attack, teleport, debuff, swarm (15 monsters)

### spawn_tables.py
Maps difficulty (1-5) to available monster spawn functions. Higher difficulty = more variety + tougher monsters.

## Level Generation (src/game/generation/)

### terrain.py — RW2-Style Generation
**NOT rooms+corridors**. Uses fill → mutate → validate:

1. **Fill**: Entire grid set to walls
2. **Seed mutators** (1-3): `seed_paths`, `seed_lumps`, `seed_noise`, `seed_squares`, `seed_grid`
3. **Modifiers** (0-2): `mod_cellular_automata`, `mod_symmetry_x/y`, `mod_border`, `mod_expand_floors`, `mod_pillars`
4. **Validation**: Min 50 floors, min 100 walls. Fix loop if needed.
5. **Connectivity**: Flood-fill labeling → carve paths between disconnected regions

### level_generator.py — Full Pipeline
Terrain → find floors → place player → place exit (far from player) → place monsters (only on reachable tiles).

### Populator
`get_reachable_floors()` uses BFS from player position to ensure all spawned enemies are reachable. Lairs placed at difficulty 5 only.

## AI (src/game/ai/)

### base_ai.py
`get_ai_action(unit)` determines behavior based on role:
- Role determined from spell loadout (has_melee, has_ranged, max_hp threshold for BOSS)
- Target selection: player priority, then lowest HP enemy
- Flee when HP < 20% (BOSS: < 15%)
- 35% imperfection: sometimes just rushes forward (deterministic hash, not random)
- Spell scoring: damage efficiency, kill potential, AOE value, role preference

## Game State (src/game/game/)

### game_state.py — Game Class
Manages the full run: SP economy, level transitions, component purchasing, spell crafting.

**Key API**:
- `buy_component(type, name)` — purchase element/shape/modifier
- `craft_spell(element, shape, modifiers)` — create and equip a spell
- `buy_mastery(name)` — purchase mastery upgrade
- `start_level()` — generate next level, begin gameplay
- `submit_action(action)` — send player action, advance game, return result dict
- `get_state()` — complete game state as dict (for headless play / serialization)

### serialization.py
JSON save/load. Saves: seed, level_num, SP, owned components, spell recipes (not full objects), player HP. Restores by re-creating the Game and re-crafting spells.

## Rendering (src/game/rendering/)

### renderer.py
RW2-style layout: left panel (character/spells/equipment/synergies) → center (level grid) → right panel (examine/combat log/consumables). FOV dimming on non-visible tiles.

### ui_shop.py
Clickable 3-column layout (elements/shapes/modifiers). Click to select+buy, craft preview, mastery section, synergy display.

### input_handler.py
WASD/arrows move, 1-9 select spell, click to cast, Tab auto-target, Space pass, F1-F6 consumables, ? help overlay.

### asset_loader.py
Loads RW2 sprites from symlinked `assets/rl_data/`. Falls back to colored rectangles if asset missing. Scales 16px to 32px.

## Testing Strategy

| Category | Directory | What | Count |
|----------|-----------|------|-------|
| Unit | tests/unit/ | Individual class behavior | ~500 |
| Integration | tests/integration/ | Multi-system chains | ~30 |
| Crafting | tests/crafting/ | All Element×Shape combos | ~450 |
| Generation | tests/generation/ | Connectivity, determinism | ~15 |
| Property | tests/property/ | Hypothesis fuzz | ~500 examples |
| Simulation | tests/simulation/ | Headless bot runs | ~15 |
| Replay | tests/replay/ | Record/replay determinism | ~3 |

**Test fixtures** (tests/conftest.py): `small_level`, `player`, `enemy`, `level_with_combatants`, `SimpleTestSpell`

**Key principle**: Tests reference component data (e.g., `FIRE.base_damage`) not hardcoded numbers, so balance changes don't break tests.
