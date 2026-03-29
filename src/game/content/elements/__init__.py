"""Element handlers — define secondary effects for each damage type."""
from __future__ import annotations


def get_element_handler(element_name: str):
    """Get the handler module for an element by name."""
    from game.content.elements import (
        fire, ice, lightning, dark, holy, nature, arcane, poison,
    )
    handlers = {
        "Fire": fire,
        "Ice": ice,
        "Lightning": lightning,
        "Dark": dark,
        "Holy": holy,
        "Nature": nature,
        "Arcane": arcane,
        "Poison": poison,
    }
    return handlers.get(element_name)
