"""Player spell book — manages owned components and crafted spells."""
from __future__ import annotations

from game.crafting.components import Element, Modifier, Shape, ELEMENTS, SHAPES, MODIFIERS
from game.crafting.cost_calculator import calculate_spell_cost
from game.crafting.recipe_validator import validate_recipe
from game.crafting.spell_factory import CraftedSpell


class SpellLibrary:
    """Manages the player's owned components and crafted spell book.

    Components are purchased once with SP. Crafting from owned components
    is free and can be done any time between levels.
    """

    def __init__(self) -> None:
        self.owned_elements: set[str] = set()
        self.owned_shapes: set[str] = set()
        self.owned_modifiers: set[str] = set()
        self.crafted_spells: list[CraftedSpell] = []
        self.sp_spent: int = 0

    def buy_element(self, name: str, sp_available: int) -> int:
        """Buy an element. Returns SP cost, or -1 if can't afford / already owned."""
        if name in self.owned_elements:
            return -1
        elem = ELEMENTS.get(name)
        if elem is None:
            return -1
        if sp_available < elem.sp_cost:
            return -1
        self.owned_elements.add(name)
        self.sp_spent += elem.sp_cost
        return elem.sp_cost

    def buy_shape(self, name: str, sp_available: int) -> int:
        """Buy a shape. Returns SP cost, or -1 if can't afford / already owned."""
        if name in self.owned_shapes:
            return -1
        shape = SHAPES.get(name)
        if shape is None:
            return -1
        if sp_available < shape.sp_cost:
            return -1
        self.owned_shapes.add(name)
        self.sp_spent += shape.sp_cost
        return shape.sp_cost

    def buy_modifier(self, name: str, sp_available: int) -> int:
        """Buy a modifier. Returns SP cost, or -1 if can't afford / already owned."""
        if name in self.owned_modifiers:
            return -1
        mod = MODIFIERS.get(name)
        if mod is None:
            return -1
        if sp_available < mod.sp_cost:
            return -1
        self.owned_modifiers.add(name)
        self.sp_spent += mod.sp_cost
        return mod.sp_cost

    def can_craft(self, element_name: str, shape_name: str,
                  modifier_names: list[str] | None = None) -> tuple[bool, list[str]]:
        """Check if a recipe can be crafted from owned components.

        Returns (can_craft, list of error messages).
        """
        errors = []
        mod_names = modifier_names or []

        if element_name not in self.owned_elements:
            errors.append(f"Element '{element_name}' not owned")
        if shape_name not in self.owned_shapes:
            errors.append(f"Shape '{shape_name}' not owned")
        for mn in mod_names:
            if mn not in self.owned_modifiers:
                errors.append(f"Modifier '{mn}' not owned")

        if errors:
            return False, errors

        # Validate recipe compatibility
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        mods = [MODIFIERS[mn] for mn in mod_names]
        result = validate_recipe(elem, shape, mods)
        if not result.valid:
            return False, result.errors

        return True, []

    def craft_spell(self, element_name: str, shape_name: str,
                    modifier_names: list[str] | None = None) -> CraftedSpell | None:
        """Craft a spell from owned components. Returns None if invalid."""
        can, errors = self.can_craft(element_name, shape_name, modifier_names)
        if not can:
            return None

        mod_names = modifier_names or []
        elem = ELEMENTS[element_name]
        shape = SHAPES[shape_name]
        mods = [MODIFIERS[mn] for mn in mod_names]

        spell = CraftedSpell(elem, shape, mods)
        self.crafted_spells.append(spell)
        return spell

    def remove_spell(self, spell: CraftedSpell) -> bool:
        """Remove a crafted spell from the book."""
        if spell in self.crafted_spells:
            self.crafted_spells.remove(spell)
            return True
        return False

    def get_available_recipes(self) -> list[tuple[str, str, list[str]]]:
        """List all valid recipes from owned components (without modifiers).

        Returns list of (element_name, shape_name, []) tuples.
        For modifier combos, call can_craft() individually.
        """
        recipes = []
        for ename in self.owned_elements:
            for sname in self.owned_shapes:
                can, _ = self.can_craft(ename, sname)
                if can:
                    recipes.append((ename, sname, []))
        return recipes
