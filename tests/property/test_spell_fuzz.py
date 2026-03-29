"""Property-based tests: fuzz random spell combinations with Hypothesis."""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from game.constants import Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import ELEMENTS, SHAPES, MODIFIERS
from game.crafting.recipe_validator import validate_recipe
from game.crafting.spell_factory import CraftedSpell

element_names = sorted(ELEMENTS.keys())
shape_names = sorted(SHAPES.keys())
modifier_names = sorted(MODIFIERS.keys())


@st.composite
def random_recipe(draw):
    """Generate a random (element, shape, modifiers) tuple."""
    elem_name = draw(st.sampled_from(element_names))
    shape_name = draw(st.sampled_from(shape_names))
    num_mods = draw(st.integers(min_value=0, max_value=2))
    mod_names = draw(st.lists(
        st.sampled_from(modifier_names),
        min_size=num_mods, max_size=num_mods,
        unique=True,
    ))
    return elem_name, shape_name, mod_names


@pytest.mark.property
class TestSpellFuzz:

    @given(recipe=random_recipe())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_recipes_never_crash_on_creation(self, recipe):
        """Any valid recipe must produce a spell without crashing."""
        elem_name, shape_name, mod_names = recipe
        elem = ELEMENTS[elem_name]
        shape = SHAPES[shape_name]
        mods = [MODIFIERS[mn] for mn in mod_names]

        result = validate_recipe(elem, shape, mods)
        if result.valid:
            spell = CraftedSpell(elem, shape, mods)
            assert spell.damage > 0
            assert len(spell.name) > 0
            assert len(spell.tags) >= 2

    @given(recipe=random_recipe())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_recipes_never_crash_on_cast(self, recipe):
        """Any valid recipe must cast without crashing."""
        elem_name, shape_name, mod_names = recipe
        elem = ELEMENTS[elem_name]
        shape = SHAPES[shape_name]
        mods = [MODIFIERS[mn] for mn in mod_names]

        result = validate_recipe(elem, shape, mods)
        if not result.valid:
            return  # Skip invalid recipes

        spell = CraftedSpell(elem, shape, mods)

        level = Level(20, 20)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 10, 10)
        player.add_spell(spell)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 200
        enemy.cur_hp = 200

        if shape.melee:
            level.add_unit(enemy, 11, 10)
            tx, ty = 11, 10
        elif shape.name == "Self":
            tx, ty = 10, 10
        elif shape.name == "Cone":
            level.add_unit(enemy, 13, 10)
            tx, ty = 13, 10
        else:
            level.add_unit(enemy, 14, 10)
            tx, ty = 14, 10

        gen = spell.cast(tx, ty)
        steps = 0
        try:
            while True:
                next(gen)
                steps += 1
                if steps > 200:
                    break  # Prevent infinite loops in fuzz
        except StopIteration:
            pass

    @given(recipe=random_recipe())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_recipes_raise_on_creation(self, recipe):
        """Invalid recipes must raise ValueError."""
        elem_name, shape_name, mod_names = recipe
        elem = ELEMENTS[elem_name]
        shape = SHAPES[shape_name]
        mods = [MODIFIERS[mn] for mn in mod_names]

        result = validate_recipe(elem, shape, mods)
        if not result.valid:
            with pytest.raises(ValueError):
                CraftedSpell(elem, shape, mods)
