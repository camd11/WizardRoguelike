"""Test modifier stacking: every compatible modifier pair with Fire+Bolt."""
import pytest

from game.constants import Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import MODIFIERS, FIRE, BOLT
from game.crafting.recipe_validator import validate_recipe
from game.crafting.spell_factory import CraftedSpell


# All single modifiers with Fire+Bolt
SINGLE_MODS = [name for name in MODIFIERS]

# All valid pairs
VALID_PAIRS = []
for i, name_a in enumerate(sorted(MODIFIERS.keys())):
    for name_b in sorted(MODIFIERS.keys())[i + 1:]:
        mod_a = MODIFIERS[name_a]
        mod_b = MODIFIERS[name_b]
        result = validate_recipe(FIRE, BOLT, [mod_a, mod_b])
        if result.valid:
            VALID_PAIRS.append((name_a, name_b))

# All invalid pairs (for negative testing)
INVALID_PAIRS = []
for i, name_a in enumerate(sorted(MODIFIERS.keys())):
    for name_b in sorted(MODIFIERS.keys())[i + 1:]:
        mod_a = MODIFIERS[name_a]
        mod_b = MODIFIERS[name_b]
        result = validate_recipe(FIRE, BOLT, [mod_a, mod_b])
        if not result.valid:
            INVALID_PAIRS.append((name_a, name_b))


@pytest.mark.parametrize("mod_name", SINGLE_MODS)
class TestSingleModifiers:
    def test_creation_succeeds(self, mod_name):
        mod = MODIFIERS[mod_name]
        result = validate_recipe(FIRE, BOLT, [mod])
        if result.valid:
            spell = CraftedSpell(FIRE, BOLT, [mod])
            assert spell is not None
            assert mod_name in spell.name

    def test_cast_completes(self, mod_name):
        mod = MODIFIERS[mod_name]
        result = validate_recipe(FIRE, BOLT, [mod])
        if not result.valid:
            pytest.skip(f"{mod_name} incompatible with Fire+Bolt")

        spell = CraftedSpell(FIRE, BOLT, [mod])
        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 7)
        player.add_spell(spell)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 100
        enemy.cur_hp = 100
        level.add_unit(enemy, 5, 7)

        gen = spell.cast(5, 7)
        steps = 0
        try:
            while True:
                next(gen)
                steps += 1
                if steps > 100:
                    pytest.fail(f"Fire+Bolt+{mod_name} did not terminate")
        except StopIteration:
            pass


@pytest.mark.parametrize("mod_a,mod_b", VALID_PAIRS,
                         ids=[f"{a}+{b}" for a, b in VALID_PAIRS])
class TestValidModifierPairs:
    def test_creation_succeeds(self, mod_a, mod_b):
        spell = CraftedSpell(FIRE, BOLT, [MODIFIERS[mod_a], MODIFIERS[mod_b]])
        assert spell is not None

    def test_cast_completes(self, mod_a, mod_b):
        spell = CraftedSpell(FIRE, BOLT, [MODIFIERS[mod_a], MODIFIERS[mod_b]])
        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 7)
        player.add_spell(spell)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 100
        enemy.cur_hp = 100
        level.add_unit(enemy, 5, 7)

        gen = spell.cast(5, 7)
        steps = 0
        try:
            while True:
                next(gen)
                steps += 1
                if steps > 100:
                    pytest.fail(f"Fire+Bolt+{mod_a}+{mod_b} did not terminate")
        except StopIteration:
            pass


@pytest.mark.parametrize("mod_a,mod_b", INVALID_PAIRS,
                         ids=[f"{a}+{b}" for a, b in INVALID_PAIRS])
class TestInvalidModifierPairs:
    def test_creation_raises(self, mod_a, mod_b):
        with pytest.raises(ValueError):
            CraftedSpell(FIRE, BOLT, [MODIFIERS[mod_a], MODIFIERS[mod_b]])
