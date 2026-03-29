# Wizard Roguelike — Spell Crafter

A tactical roguelike where you craft spells from components instead of finding them. Combine **8 elements**, **11 shapes**, and **11 modifiers** to create thousands of unique spells. Fight through 5 procedurally generated levels with 41+ unique monsters.

Inspired by [Rift Wizard 2](https://store.steampowered.com/app/2058570/Rift_Wizard_2/) by Dylan White.

## Play

```bash
# Setup (first time)
git clone https://github.com/camd11/WizardRoguelike.git
cd WizardRoguelike
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"

# Symlink RW2 assets (optional — game works with colored fallback rectangles)
ln -s "/path/to/Rift Wizard 2/RiftWizard2/rl_data" assets/rl_data

# Play
python -m game.main
```

## How It Works

### Spell Crafting
Buy **components** with SP (Skill Points). Combine them into spells:

| Component | Examples | What It Does |
|-----------|----------|-------------|
| **Element** | Fire, Ice, Lightning, Arcane | Damage type + secondary effect (burn, freeze, stun, pierce) |
| **Shape** | Bolt, Burst, Beam, Cone, Chain, Wall, Nova | How the spell is delivered (projectile, AOE, piercing line, etc.) |
| **Modifier** | Empowered (+50% damage), Lingering (creates zone), Vampiric (heals on hit) | Enhances the spell (0-2 per spell) |

Example: **Empowered Lightning Burst** = Lightning + Burst + Empowered = AOE lightning explosion with 50% bonus damage.

Components are bought once — craft unlimited spells from owned components for free.

### Combat
- Turn-based on a grid
- 5 levels of increasing difficulty
- Monsters use role-based AI (melee rush, ranged kite, caster stay-at-range, boss tactics)
- Destroy all enemies (and lairs on level 5) to advance

### Progression
- SP gained per level cleared
- Equipment drops (20 items across 6 slots)
- Consumables (potions, scrolls)
- Element synergies (owning Fire + Ice unlocks "Steam Power" bonus)
- Component masteries (Fire Mastery I/II/III for increasing bonuses)

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| Q E Z C | Move diagonally |
| 1-9 | Select spell |
| Left Click | Cast spell at target |
| Tab | Auto-target nearest enemy |
| Space | Pass turn |
| F1-F6 | Use consumable |
| ? / H | Help overlay |
| F11 | Toggle fullscreen |

## Watch AI Play

```bash
# Record a bot game
python -c "
from tests.simulation.smart_bot import SmartBot
bot = SmartBot(seed=42, record=True)
bot.play_full_run()
bot.recorder.save('replay.json')
"

# Watch it visually (pause with Space, step with Right arrow)
python -m game.replay_viewer replay.json --speed 5
```

## Test

```bash
pytest tests/ -q                    # All 1000+ tests (~2.5s)
pytest tests/ -m "not slow"         # Skip slow simulation sweep
pytest tests/property/ -v           # Hypothesis fuzz testing
```

## For Developers

See [CLAUDE.md](CLAUDE.md) for project rules and conventions.
See [ARCHITECTURE.md](ARCHITECTURE.md) for system-by-system technical documentation.

## Tech Stack

- **Python 3.11+** with **Pygame-ce** for rendering
- **tcod** for pathfinding and FOV
- **Hypothesis** for property-based testing
- Zero external game engines — custom architecture modeled on RW2

## License

Placeholder — intended as a learning/hobby project.
