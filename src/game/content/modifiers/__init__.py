"""Modifier handlers — enhance crafted spells with additional effects."""
from __future__ import annotations


def get_modifier_handler(modifier_name: str):
    """Get the handler module for a modifier by name."""
    from game.content.modifiers import (
        empowered, extended, lingering, splitting,
        channeled, homing, piercing, volatile,
        quickened, widened, vampiric,
    )
    handlers = {
        "Empowered": empowered,
        "Extended": extended,
        "Lingering": lingering,
        "Splitting": splitting,
        "Channeled": channeled,
        "Homing": homing,
        "Piercing": piercing,
        "Volatile": volatile,
        "Quickened": quickened,
        "Widened": widened,
        "Vampiric": vampiric,
    }
    return handlers.get(modifier_name)
