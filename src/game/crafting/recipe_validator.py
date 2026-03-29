"""Validate spell crafting recipes (Element + Shape + 0-2 Modifiers)."""
from __future__ import annotations

from dataclasses import dataclass, field

from game.crafting.components import Element, Modifier, Shape


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_recipe(element: Element, shape: Shape,
                    modifiers: list[Modifier] | None = None) -> ValidationResult:
    """Validate a spell recipe.

    Rules:
    1. Exactly one Element and one Shape (enforced by signature)
    2. 0-2 Modifiers
    3. No duplicate modifiers
    4. No incompatible modifier+shape pairs
    5. No incompatible modifier+modifier pairs
    """
    errors = []
    mods = modifiers or []

    # Rule 2: modifier count
    if len(mods) > 2:
        errors.append(f"Maximum 2 modifiers allowed, got {len(mods)}")

    # Rule 3: no duplicates
    mod_names = [m.name for m in mods]
    if len(mod_names) != len(set(mod_names)):
        errors.append("Duplicate modifiers are not allowed")

    # Rule 4: modifier-shape incompatibilities
    for mod in mods:
        if shape.name in mod.incompatible_with:
            errors.append(
                f"Modifier '{mod.name}' is incompatible with shape '{shape.name}'"
            )

    # Rule 5: modifier-modifier incompatibilities
    for i, mod_a in enumerate(mods):
        for mod_b in mods[i + 1:]:
            if mod_a.name in mod_b.incompatible_with:
                errors.append(
                    f"Modifier '{mod_b.name}' is incompatible with modifier '{mod_a.name}'"
                )
            if mod_b.name in mod_a.incompatible_with:
                errors.append(
                    f"Modifier '{mod_a.name}' is incompatible with modifier '{mod_b.name}'"
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
