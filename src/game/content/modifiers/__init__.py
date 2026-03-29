"""Modifier handlers — enhance crafted spells with additional effects."""
from __future__ import annotations


def get_modifier_handler(modifier_name: str):
    """Get the handler module for a modifier by name."""
    from game.content.modifiers import (
        empowered, extended, lingering, splitting,
        channeled, homing, piercing, volatile,
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
    }
    return handlers.get(modifier_name)
