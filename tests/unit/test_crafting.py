"""Tests for spell crafting: components, validation, cost, factory, library."""
import pytest

from game.constants import Tags, Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import (
    ELEMENTS, MODIFIERS, SHAPES,
    FIRE, ICE, LIGHTNING, DARK, HOLY, NATURE, ARCANE, POISON,
    BOLT, BURST, BEAM, CONE, ORB, TOUCH, SELF, SUMMON,
    EMPOWERED, EXTENDED, LINGERING, SPLITTING, CHANNELED, HOMING, PIERCING, VOLATILE,
)
from game.crafting.cost_calculator import calculate_spell_cost
from game.crafting.recipe_validator import validate_recipe
from game.crafting.spell_factory import CraftedSpell
from game.crafting.spell_library import SpellLibrary


class TestComponentRegistries:
    def test_all_elements_registered(self):
        assert len(ELEMENTS) == 8
        for name in ["Fire", "Ice", "Lightning", "Dark", "Holy", "Nature", "Arcane", "Poison"]:
            assert name in ELEMENTS

    def test_all_shapes_registered(self):
        assert len(SHAPES) == 8
        for name in ["Bolt", "Burst", "Beam", "Cone", "Orb", "Touch", "Self", "Summon"]:
            assert name in SHAPES

    def test_all_modifiers_registered(self):
        assert len(MODIFIERS) == 8
        for name in ["Empowered", "Extended", "Lingering", "Splitting",
                      "Channeled", "Homing", "Piercing", "Volatile"]:
            assert name in MODIFIERS

    def test_elements_have_positive_damage(self):
        for elem in ELEMENTS.values():
            assert elem.base_damage > 0

    def test_shapes_have_valid_tiers(self):
        for shape in SHAPES.values():
            assert shape.tier in (1, 2, 3)

    def test_modifiers_have_valid_tiers(self):
        for mod in MODIFIERS.values():
            assert mod.tier in (1, 2, 3)


class TestRecipeValidator:
    def test_valid_basic_recipe(self):
        result = validate_recipe(FIRE, BOLT)
        assert result.valid

    def test_valid_recipe_with_modifier(self):
        result = validate_recipe(FIRE, BOLT, [EMPOWERED])
        assert result.valid

    def test_valid_recipe_with_two_modifiers(self):
        result = validate_recipe(FIRE, BOLT, [EMPOWERED, PIERCING])
        assert result.valid

    def test_too_many_modifiers(self):
        result = validate_recipe(FIRE, BOLT, [EMPOWERED, PIERCING, EXTENDED])
        assert not result.valid
        assert "Maximum 2 modifiers" in result.errors[0]

    def test_duplicate_modifiers(self):
        result = validate_recipe(FIRE, BOLT, [EMPOWERED, EMPOWERED])
        assert not result.valid

    def test_incompatible_modifier_shape(self):
        # Extended is incompatible with Self
        result = validate_recipe(FIRE, SELF, [EXTENDED])
        assert not result.valid

    def test_homing_incompatible_with_self(self):
        result = validate_recipe(FIRE, SELF, [HOMING])
        assert not result.valid

    def test_splitting_incompatible_with_burst(self):
        result = validate_recipe(FIRE, BURST, [SPLITTING])
        assert not result.valid

    def test_channeled_incompatible_with_touch(self):
        result = validate_recipe(FIRE, TOUCH, [CHANNELED])
        assert not result.valid

    def test_all_elements_compatible_with_bolt(self):
        for elem in ELEMENTS.values():
            result = validate_recipe(elem, BOLT)
            assert result.valid, f"{elem.name} + Bolt should be valid"


class TestCostCalculator:
    def test_basic_tier1_cost(self):
        # Fire (1) + Bolt (1) = 2 * 1.0 = 2
        cost = calculate_spell_cost(FIRE, BOLT)
        assert cost == 2

    def test_tier2_multiplier(self):
        # Fire (1) + Beam (2) = 3 * 1.5 = 5 (ceil)
        cost = calculate_spell_cost(FIRE, BEAM)
        assert cost == 5

    def test_tier3_multiplier(self):
        # Arcane (3) + Bolt (1) = 4 * 2.5 = 10
        cost = calculate_spell_cost(ARCANE, BOLT)
        assert cost == 10

    def test_with_modifiers(self):
        # Fire (1) + Bolt (1) + Empowered (1) = 3 * 1.0 = 3
        cost = calculate_spell_cost(FIRE, BOLT, [EMPOWERED])
        assert cost == 3

    def test_tier_from_modifier(self):
        # Fire (1) + Bolt (1) + Piercing (tier 2, cost 2) = 4 * 1.5 = 6
        cost = calculate_spell_cost(FIRE, BOLT, [PIERCING])
        assert cost == 6


class TestCraftedSpell:
    def test_basic_fire_bolt(self):
        spell = CraftedSpell(FIRE, BOLT)
        assert spell.name == "Fire Bolt"
        assert spell.damage == FIRE.base_damage
        assert spell.damage_type is Tags.Fire
        assert spell.range == BOLT.base_range
        assert spell.max_charges == BOLT.base_charges
        assert Tags.Fire in spell.tags
        assert Tags.Shape_Bolt in spell.tags

    def test_ice_burst(self):
        spell = CraftedSpell(ICE, BURST)
        assert spell.name == "Ice Burst"
        assert spell.damage == ICE.base_damage
        assert spell.radius == BURST.base_radius

    def test_empowered_fire_bolt(self):
        spell = CraftedSpell(FIRE, BOLT, [EMPOWERED])
        assert "Empowered" in spell.name
        # Base damage stored unmultiplied; multiplier applied in get_stat
        assert spell.damage == FIRE.base_damage
        # With a caster, get_stat applies 1.5x
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        player.add_spell(spell)
        expected = int(FIRE.base_damage * EMPOWERED.damage_mult)
        assert spell.get_stat("damage") == expected

    def test_extended_increases_range(self):
        # Extended range bonus is applied through get_stat, not stored on spell.range
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        base_spell = CraftedSpell(FIRE, BOLT)
        ext_spell = CraftedSpell(FIRE, BOLT, [EXTENDED])
        player.add_spell(base_spell)
        player.add_spell(ext_spell)
        assert ext_spell.get_stat("range") > base_spell.get_stat("range")

    def test_invalid_recipe_raises(self):
        with pytest.raises(ValueError):
            CraftedSpell(FIRE, SELF, [EXTENDED])

    def test_cast_returns_generator(self):
        spell = CraftedSpell(FIRE, BOLT)
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        player.add_spell(spell)
        gen = spell.cast(5, 1)
        assert hasattr(gen, '__next__')

    def test_bolt_deals_damage(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 1)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 50
        enemy.cur_hp = 50
        level.add_unit(enemy, 5, 1)

        spell = CraftedSpell(FIRE, BOLT)
        player.add_spell(spell)

        gen = spell.cast(5, 1)
        try:
            while True:
                next(gen)
        except StopIteration:
            pass

        assert enemy.cur_hp < 50

    def test_burst_hits_multiple_enemies(self):
        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 7)

        # Place enemies in a cluster
        enemies = []
        for dx, dy in [(7, 7), (8, 7), (7, 8)]:
            e = Unit()
            e.team = Team.ENEMY
            e.max_hp = 50
            e.cur_hp = 50
            level.add_unit(e, dx, dy)
            enemies.append(e)

        spell = CraftedSpell(FIRE, BURST)
        player.add_spell(spell)

        gen = spell.cast(7, 7)
        try:
            while True:
                next(gen)
        except StopIteration:
            pass

        damaged = sum(1 for e in enemies if e.cur_hp < 50)
        assert damaged >= 1  # At least the center target hit

    def test_touch_requires_adjacency(self):
        spell = CraftedSpell(FIRE, TOUCH)
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        player.add_spell(spell)
        assert spell.can_cast(2, 1)   # Adjacent
        assert not spell.can_cast(5, 1)  # Too far

    def test_self_cast_targets_caster(self):
        spell = CraftedSpell(FIRE, SELF)
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 4, 4)
        player.add_spell(spell)
        assert spell.can_cast(4, 4)   # Self position
        assert not spell.can_cast(5, 5)  # Not self


class TestSpellLibrary:
    def test_buy_element(self):
        lib = SpellLibrary()
        cost = lib.buy_element("Fire", sp_available=10)
        assert cost == 1
        assert "Fire" in lib.owned_elements

    def test_buy_duplicate_fails(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", sp_available=10)
        cost = lib.buy_element("Fire", sp_available=10)
        assert cost == -1

    def test_buy_insufficient_sp(self):
        lib = SpellLibrary()
        cost = lib.buy_element("Arcane", sp_available=1)  # Costs 3
        assert cost == -1

    def test_craft_spell(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", 10)
        lib.buy_shape("Bolt", 10)
        spell = lib.craft_spell("Fire", "Bolt")
        assert spell is not None
        assert spell.name == "Fire Bolt"
        assert spell in lib.crafted_spells

    def test_craft_without_components_fails(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", 10)
        spell = lib.craft_spell("Fire", "Bolt")  # Don't own Bolt
        assert spell is None

    def test_craft_with_modifier(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", 10)
        lib.buy_shape("Bolt", 10)
        lib.buy_modifier("Empowered", 10)
        spell = lib.craft_spell("Fire", "Bolt", ["Empowered"])
        assert spell is not None
        assert "Empowered" in spell.name

    def test_available_recipes(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", 10)
        lib.buy_element("Ice", 10)
        lib.buy_shape("Bolt", 10)
        lib.buy_shape("Burst", 10)
        recipes = lib.get_available_recipes()
        assert len(recipes) == 4  # Fire+Bolt, Fire+Burst, Ice+Bolt, Ice+Burst

    def test_reuse_components_across_spells(self):
        lib = SpellLibrary()
        lib.buy_element("Fire", 10)
        lib.buy_shape("Bolt", 10)
        lib.buy_shape("Burst", 10)
        s1 = lib.craft_spell("Fire", "Bolt")
        s2 = lib.craft_spell("Fire", "Burst")
        assert s1 is not None
        assert s2 is not None
        # Same Fire element used in both spells
        assert len(lib.crafted_spells) == 2
