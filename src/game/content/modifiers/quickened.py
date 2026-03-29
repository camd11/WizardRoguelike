"""Quickened modifier — grants bonus charges (cast more often)."""


def modify_stats(spell, stats: dict) -> dict:
    """No stat modification — charge bonus is applied via component data."""
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — quickened is a pure charge bonus."""
    pass
