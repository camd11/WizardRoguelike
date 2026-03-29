"""Widened modifier — increases radius for AOE spells."""


def modify_stats(spell, stats: dict) -> dict:
    """Increase radius by 1 for AOE shapes."""
    if "radius" in stats:
        for mod in spell._modifiers:
            if mod.name == "Widened":
                stats["radius"] += 1
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — widened is a pure stat modifier."""
    pass
