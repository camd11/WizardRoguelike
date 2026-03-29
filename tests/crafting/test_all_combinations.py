"""Combinatorial test: every Element × Shape pair must produce a valid spell.

64 combinations tested parametrically.
"""
import pytest

from game.constants import Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import ELEMENTS, SHAPES
from game.crafting.spell_factory import CraftedSpell


ALL_COMBOS = [
    (ename, sname)
    for ename in ELEMENTS
    for sname in SHAPES
]


@pytest.mark.parametrize("element_name,shape_name", ALL_COMBOS,
                         ids=[f"{e}-{s}" for e, s in ALL_COMBOS])
class TestAllElementShapeCombinations:
    """Every Element × Shape must create a valid, castable spell."""

    def test_creation_succeeds(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)
        assert spell is not None

    def test_has_positive_damage(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)
        assert spell.damage > 0

    def test_has_nonempty_name(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)
        assert len(spell.name) > 0
        assert element_name in spell.name
        assert shape_name in spell.name

    def test_has_element_tag(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)
        assert elem.tag in spell.tags

    def test_has_shape_tag(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)
        assert shape.tag in spell.tags

    def test_cast_generator_completes(self, element_name, shape_name):
        """Cast the spell on a test level and verify the generator terminates."""
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)

        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 7, 7)
        player.add_spell(spell)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 100
        enemy.cur_hp = 100

        # Place enemy based on spell range
        if shape.melee:
            level.add_unit(enemy, 8, 7)
            target_x, target_y = 8, 7
        elif shape.name == "Self":
            target_x, target_y = 7, 7
        elif shape.name == "Cone":
            level.add_unit(enemy, 9, 7)
            target_x, target_y = 9, 7
        else:
            level.add_unit(enemy, 10, 7)
            target_x, target_y = 10, 7

        gen = spell.cast(target_x, target_y)
        steps = 0
        try:
            while True:
                next(gen)
                steps += 1
                if steps > 100:
                    pytest.fail(f"{element_name}+{shape_name} cast() did not terminate in 100 steps")
        except StopIteration:
            pass

    def test_get_impacted_tiles_returns_list(self, element_name, shape_name):
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        spell = CraftedSpell(elem, shape)

        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 7, 7)
        player.add_spell(spell)

        if shape.name == "Self":
            tiles = spell.get_impacted_tiles(7, 7)
        elif shape.melee:
            tiles = spell.get_impacted_tiles(8, 7)
        else:
            tiles = spell.get_impacted_tiles(10, 7)

        assert isinstance(tiles, list)
        assert len(tiles) > 0
