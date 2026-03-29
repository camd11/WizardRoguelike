"""JSON save/load system for game state.

Saves between levels (during shop phase). Captures:
- Seed and level number
- SP and owned components
- Crafted spell recipes (element + shape + modifiers)
- Player HP and buffs
- Stats (turns, kills)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.game.game_state import Game

SAVE_DIR = Path.home() / ".wizard_roguelike" / "saves"


def save_game(game: Game, slot: int = 0) -> Path:
    """Save game state to JSON. Returns the save file path."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    path = SAVE_DIR / f"save_{slot}.json"

    # Collect crafted spell recipes
    spell_recipes = []
    for spell in game.spell_library.crafted_spells:
        recipe = {
            "element": spell._element.name,
            "shape": spell._shape.name,
            "modifiers": [m.name for m in spell._modifiers],
        }
        spell_recipes.append(recipe)

    data = {
        "version": 1,
        "seed": game.seed,
        "level_num": game.level_num,
        "sp": game.sp,
        "total_turns": game.total_turns,
        "enemies_killed": game.enemies_killed,
        "player": {
            "cur_hp": game.player.cur_hp,
            "max_hp": game.player.max_hp,
            "shields": game.player.shields,
        },
        "library": {
            "owned_elements": sorted(game.spell_library.owned_elements),
            "owned_shapes": sorted(game.spell_library.owned_shapes),
            "owned_modifiers": sorted(game.spell_library.owned_modifiers),
            "spell_recipes": spell_recipes,
        },
    }

    path.write_text(json.dumps(data, indent=2))
    return path


def load_game(slot: int = 0) -> dict | None:
    """Load game state from JSON. Returns None if no save exists."""
    path = SAVE_DIR / f"save_{slot}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def restore_game(save_data: dict) -> Game:
    """Create a Game instance from save data."""
    from game.game.game_state import Game

    game = Game(seed=save_data["seed"])
    game.level_num = save_data["level_num"]
    game.sp = save_data["sp"]
    game.total_turns = save_data["total_turns"]
    game.enemies_killed = save_data["enemies_killed"]

    # Restore player HP
    game.player.max_hp = save_data["player"]["max_hp"]
    game.player.cur_hp = save_data["player"]["cur_hp"]
    game.player.shields = save_data["player"]["shields"]

    # Restore owned components
    lib = game.spell_library
    for name in save_data["library"]["owned_elements"]:
        lib.owned_elements.add(name)
    for name in save_data["library"]["owned_shapes"]:
        lib.owned_shapes.add(name)
    for name in save_data["library"]["owned_modifiers"]:
        lib.owned_modifiers.add(name)

    # Restore crafted spells
    for recipe in save_data["library"]["spell_recipes"]:
        spell = lib.craft_spell(
            recipe["element"],
            recipe["shape"],
            recipe["modifiers"] if recipe["modifiers"] else None,
        )
        if spell:
            game.player.add_spell(spell)

    game.in_shop = True  # Saves happen during shop phase
    return game


def delete_save(slot: int = 0) -> bool:
    """Delete a save file."""
    path = SAVE_DIR / f"save_{slot}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def list_saves() -> list[dict]:
    """List all save files with summary info."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    saves = []
    for path in sorted(SAVE_DIR.glob("save_*.json")):
        try:
            data = json.loads(path.read_text())
            saves.append({
                "slot": int(path.stem.split("_")[1]),
                "level": data["level_num"],
                "sp": data["sp"],
                "kills": data["enemies_killed"],
                "hp": data["player"]["cur_hp"],
            })
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return saves
