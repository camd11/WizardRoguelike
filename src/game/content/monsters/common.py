"""Common monster attack spells reused across tiers."""
from __future__ import annotations

from game.constants import Tags
from game.core.spell_base import Spell


class SimpleMeleeAttack(Spell):
    """Basic melee attack for monsters."""

    def __init__(self, damage: int = 5, damage_type=Tags.Physical, name: str = "Bite") -> None:
        self._base_damage = damage
        self._dtype = damage_type
        self._attack_name = name
        super().__init__()

    def on_init(self) -> None:
        self.name = self._attack_name
        self.damage = self._base_damage
        self.damage_type = self._dtype
        self.range = 1
        self.melee = True
        self.tags = [self._dtype]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
        yield


class SimpleRangedAttack(Spell):
    """Basic ranged attack for monsters."""

    def __init__(self, damage: int = 4, damage_type=Tags.Physical,
                 spell_range: int = 5, name: str = "Shot") -> None:
        self._base_damage = damage
        self._dtype = damage_type
        self._range = spell_range
        self._attack_name = name
        super().__init__()

    def on_init(self) -> None:
        self.name = self._attack_name
        self.damage = self._base_damage
        self.damage_type = self._dtype
        self.range = self._range
        self.tags = [self._dtype]

    def cast(self, x, y):
        if self.level:
            from game.core.shapes import bolt
            from game.core.types import Point
            start = Point(self.caster.x, self.caster.y)
            end = Point(x, y)
            for stage in bolt(self.level, start, end):
                for p in stage:
                    unit = self.level.get_unit_at(p.x, p.y)
                    if unit and unit.team != self.caster.team:
                        self.level.deal_damage(p.x, p.y, self.get_stat("damage"),
                                               self.damage_type, self)
                        return
                yield


class SimpleBreathAttack(Spell):
    """Breath/cone attack for monsters."""

    def __init__(self, damage: int = 6, damage_type=Tags.Fire,
                 radius: int = 3, name: str = "Fire Breath") -> None:
        self._base_damage = damage
        self._dtype = damage_type
        self._radius = radius
        self._attack_name = name
        super().__init__()

    def on_init(self) -> None:
        self.name = self._attack_name
        self.damage = self._base_damage
        self.damage_type = self._dtype
        self.radius = self._radius
        self.range = 0
        self.can_target_self = True
        self.cool_down = 3
        self.tags = [self._dtype]

    def cast(self, x, y):
        if self.level:
            from game.core.shapes import cone
            from game.core.types import Point
            origin = Point(self.caster.x, self.caster.y)
            target = Point(x, y)
            for stage in cone(self.level, origin, target, self.radius):
                for p in stage:
                    if p.x == origin.x and p.y == origin.y:
                        continue
                    unit = self.level.get_unit_at(p.x, p.y)
                    if unit and unit.team != self.caster.team:
                        self.level.deal_damage(p.x, p.y, self.get_stat("damage"),
                                               self.damage_type, self)
                yield
