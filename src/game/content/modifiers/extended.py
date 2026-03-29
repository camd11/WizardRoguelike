"""Extended modifier — range bonus applied during stat calculation."""


def modify_stats(spell, stats: dict) -> dict:
    """Increase range by the modifier's range_bonus."""
    if "range" in stats:
        for mod in spell._modifiers:
            if mod.name == "Extended":
                stats["range"] = stats["range"] + mod.range_bonus
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — extended is a pure stat modifier."""
    pass
