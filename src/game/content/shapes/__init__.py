"""Shape handlers — define cast() generators for each delivery mechanism."""
from __future__ import annotations


def get_shape_handler(shape_name: str):
    """Get the handler module for a shape by name."""
    from game.content.shapes import (
        bolt, burst, beam, cone, orb, touch, self_cast, summon,
        chain, wall, nova,
    )
    handlers = {
        "Bolt": bolt,
        "Burst": burst,
        "Beam": beam,
        "Cone": cone,
        "Orb": orb,
        "Touch": touch,
        "Self": self_cast,
        "Summon": summon,
        "Chain": chain,
        "Wall": wall,
        "Nova": nova,
    }
    return handlers.get(shape_name)
