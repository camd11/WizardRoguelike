"""Empowered modifier — damage multiplier applied during stat calculation."""


def modify_stats(spell, stats: dict) -> dict:
    """Increase damage by the modifier's damage_mult."""
    if "damage" in stats:
        for mod in spell._modifiers:
            if mod.name == "Empowered":
                stats["damage"] = int(stats["damage"] * mod.damage_mult)
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — empowered is a pure stat modifier."""
    pass
