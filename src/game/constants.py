"""Game-wide constants, enums, and tag definitions."""
from __future__ import annotations

from enum import Enum, IntEnum, auto
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Grid / Display
# ---------------------------------------------------------------------------
TILE_SIZE = 16  # pixels (matches RW2 assets; will become 32+ with custom art)
LEVEL_SIZE = 28  # tiles per side (28x28 grid)

# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------
class Team(IntEnum):
    PLAYER = 0
    ENEMY = 1
    NEUTRAL = 2


# ---------------------------------------------------------------------------
# Tile types
# ---------------------------------------------------------------------------
class TileType(Enum):
    FLOOR = auto()
    WALL = auto()
    CHASM = auto()


# ---------------------------------------------------------------------------
# Buff stack types
# ---------------------------------------------------------------------------
class StackType(Enum):
    STACK_NONE = auto()       # Rejects second application
    STACK_DURATION = auto()   # Refreshes duration
    STACK_REPLACE = auto()    # Removes old, applies new
    STACK_INTENSITY = auto()  # Effects stack additively


# ---------------------------------------------------------------------------
# Buff type classification
# ---------------------------------------------------------------------------
class BuffType(Enum):
    BUFF = auto()
    CURSE = auto()
    PASSIVE = auto()
    EQUIPMENT = auto()


# ---------------------------------------------------------------------------
# Equipment slots
# ---------------------------------------------------------------------------
class EquipSlot(Enum):
    STAFF = auto()
    ROBE = auto()
    HEAD = auto()
    GLOVES = auto()
    BOOTS = auto()
    AMULET = auto()


# ---------------------------------------------------------------------------
# Tag system — elements, spell schools, shape pseudo-tags
# ---------------------------------------------------------------------------
class Tag:
    """A tag that can be applied to spells, units, buffs, etc."""

    _registry: dict[str, Tag] = {}

    def __init__(self, name: str, color: tuple[int, int, int] = (255, 255, 255)) -> None:
        self.name = name
        self.color = color
        Tag._registry[name] = self

    def __repr__(self) -> str:
        return f"Tag({self.name!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tag):
            return self.name == other.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    def get(cls, name: str) -> Tag:
        return cls._registry[name]


class Tags:
    """Central tag registry. All tags defined here."""

    # Elements (damage types)
    Fire = Tag("Fire", (255, 80, 20))
    Ice = Tag("Ice", (100, 200, 255))
    Lightning = Tag("Lightning", (255, 255, 60))
    Dark = Tag("Dark", (100, 20, 120))
    Holy = Tag("Holy", (255, 255, 200))
    Nature = Tag("Nature", (50, 200, 50))
    Arcane = Tag("Arcane", (180, 80, 255))
    Poison = Tag("Poison", (100, 200, 0))
    Physical = Tag("Physical", (180, 180, 180))

    # Spell schools
    Sorcery = Tag("Sorcery", (200, 60, 60))
    Conjuration = Tag("Conjuration", (60, 200, 60))
    Enchantment = Tag("Enchantment", (60, 60, 200))

    # Shape pseudo-tags (for category upgrades)
    Shape_Bolt = Tag("Shape_Bolt", (200, 200, 200))
    Shape_Burst = Tag("Shape_Burst", (200, 200, 200))
    Shape_Beam = Tag("Shape_Beam", (200, 200, 200))
    Shape_Cone = Tag("Shape_Cone", (200, 200, 200))
    Shape_Orb = Tag("Shape_Orb", (200, 200, 200))
    Shape_Touch = Tag("Shape_Touch", (200, 200, 200))
    Shape_Self = Tag("Shape_Self", (200, 200, 200))
    Shape_Summon = Tag("Shape_Summon", (200, 200, 200))

    # Unit type tags
    Living = Tag("Living", (200, 150, 100))
    Undead = Tag("Undead", (100, 100, 100))
    Demon = Tag("Demon", (200, 50, 50))
    Dragon = Tag("Dragon", (200, 200, 50))
    Construct = Tag("Construct", (150, 150, 200))

    @classmethod
    def elements(cls) -> list[Tag]:
        return [cls.Fire, cls.Ice, cls.Lightning, cls.Dark,
                cls.Holy, cls.Nature, cls.Arcane, cls.Poison, cls.Physical]


# Damage type cap (maximum resistance percentage)
MAX_RESIST = 100

# Damage instance cap per unit per turn (prevent infinite loops)
DAMAGE_INSTANCE_CAP = 50
