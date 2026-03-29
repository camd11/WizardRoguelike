"""AI behavior system for monsters.

Each unit gets an AIBehavior that determines how it acts.
Behaviors: Melee (rush), Ranged (kite), Caster (stay at range, use best spell),
Coward (flee when low HP), Boss (use abilities tactically).

Modeled on RW2's simple but effective AI: monsters pick the best available
spell, then move toward (or away from) their target.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from game.core.actions import CastAction, MoveAction, PassAction
from game.core.types import Point

if TYPE_CHECKING:
    from game.core.unit import Unit


class AIRole(Enum):
    MELEE = auto()      # Rush toward player, attack in melee
    RANGED = auto()     # Stay at range, shoot, kite if too close
    CASTER = auto()     # Use best spell available, stay at max range
    SUPPORT = auto()    # Buff allies, heal, stay behind
    BOSS = auto()       # Use abilities on cooldown, aggressive but not reckless


def get_ai_action(unit: Unit) -> MoveAction | CastAction | PassAction:
    """Determine the best action for an AI unit based on its role.

    Includes intentional imperfection — monsters make suboptimal choices
    ~20% of the time to keep the game fair and fun.
    """
    if unit.level is None:
        return PassAction()

    role = _determine_role(unit)
    target = _find_priority_target(unit)

    if target is None:
        return PassAction()

    # Imperfect AI: 35% chance to just rush toward target regardless.
    # Use deterministic hash based on position + turn for reproducible behavior.
    turn = unit.level.turn_no if unit.level else 0
    imperfect_hash = hash((unit.x, unit.y, unit.name, turn)) % 100
    if role != AIRole.BOSS and imperfect_hash < 35:
        return _move_toward(unit, target)

    # Check for flee condition (any role)
    if _should_flee(unit, target, role):
        flee_move = _get_flee_move(unit, target)
        if flee_move:
            return flee_move

    # Try to cast the best spell
    best_cast = _find_best_cast(unit, target, role)
    if best_cast:
        return best_cast

    # Movement based on role
    return _get_role_movement(unit, target, role)


def _determine_role(unit: Unit) -> AIRole:
    """Determine AI role from unit's spell loadout."""
    has_melee = False
    has_ranged = False
    max_range = 0

    for spell in unit.spells:
        if spell.melee or spell.range <= 1:
            has_melee = True
        else:
            has_ranged = True
            max_range = max(max_range, spell.range)

    # Check if boss by HP threshold
    if unit.max_hp >= 50:
        return AIRole.BOSS

    if has_ranged and not has_melee:
        return AIRole.RANGED
    if has_ranged and has_melee:
        return AIRole.CASTER
    return AIRole.MELEE


def _find_priority_target(unit: Unit) -> Unit | None:
    """Find the best target to attack.

    Priority: player > lowest HP enemy > nearest enemy.
    """
    if unit.level is None:
        return None

    enemies = [u for u in unit.level.units
               if u.team != unit.team and u.is_alive()]

    if not enemies:
        return None

    # Always prioritize the player
    players = [u for u in enemies if u.is_player()]
    if players:
        return players[0]

    # Otherwise target lowest HP (finish off wounded)
    return min(enemies, key=lambda u: (u.cur_hp, _dist(unit, u)))


def _should_flee(unit: Unit, target: Unit, role: AIRole) -> bool:
    """Determine if the unit should flee."""
    hp_pct = unit.cur_hp / max(1, unit.max_hp)

    # Bosses don't flee until very low
    if role == AIRole.BOSS:
        return hp_pct < 0.15

    # Ranged units flee if too close
    if role == AIRole.RANGED:
        dist = _dist(unit, target)
        if dist <= 2 and hp_pct < 0.5:
            return True

    # Anyone flees at very low HP
    return hp_pct < 0.2


def _find_best_cast(unit: Unit, target: Unit, role: AIRole) -> CastAction | None:
    """Find the best spell to cast.

    Considers: damage efficiency, cooldown state, range, AOE value.
    """
    best_action = None
    best_score = -1

    for spell in unit.spells:
        if not spell.can_pay_costs():
            continue

        # Check if we can hit the target
        if not spell.can_cast(target.x, target.y):
            continue

        score = _score_spell(unit, spell, target, role)
        if score > best_score:
            best_score = score
            best_action = CastAction(spell=spell, x=target.x, y=target.y)

    return best_action


def _score_spell(unit: Unit, spell, target: Unit, role: AIRole) -> float:
    """Score a spell's tactical value."""
    score = spell.get_stat("damage") * 10

    # Bonus for killing the target
    if spell.get_stat("damage") >= target.cur_hp:
        score += 50

    # Bonus for AOE (might hit multiple)
    if spell.radius > 0:
        score += 20

    # Ranged units prefer ranged attacks
    if role == AIRole.RANGED and spell.range > 1:
        score += 15

    # Melee units prefer melee (higher damage usually)
    if role == AIRole.MELEE and spell.melee:
        score += 10

    # Boss uses high-cooldown abilities when available (don't waste them)
    if role == AIRole.BOSS and spell.cool_down > 0:
        score += 30  # Priority on special abilities

    # Penalty for overkill waste
    overkill = spell.get_stat("damage") - target.cur_hp
    if overkill > 0:
        score -= overkill * 2

    return score


def _get_role_movement(unit: Unit, target: Unit, role: AIRole) -> MoveAction | PassAction:
    """Get movement based on AI role."""
    dist = _dist(unit, target)

    if unit.stationary:
        return PassAction()

    if role == AIRole.RANGED:
        # Try to maintain range 3-5
        ideal_range = 4
        if dist < ideal_range:
            # Back away
            flee = _get_flee_move(unit, target)
            if flee:
                return flee
        elif dist > ideal_range + 2:
            # Move closer
            return _move_toward(unit, target)
        else:
            # Good range — strafe (move perpendicular)
            return _strafe(unit, target)

    elif role == AIRole.CASTER:
        # Stay at max spell range
        max_range = max((s.range for s in unit.spells if s.range > 0), default=1)
        if dist < max_range - 1:
            flee = _get_flee_move(unit, target)
            if flee:
                return flee
        return _move_toward(unit, target)

    else:
        # Melee / Boss: rush toward target
        return _move_toward(unit, target)


def _move_toward(unit: Unit, target: Unit) -> MoveAction | PassAction:
    """Move one step toward target using pathfinding."""
    if unit.level is None:
        return PassAction()

    path = unit.level.find_path(unit.x, unit.y, target.x, target.y, unit.flying)
    if path and len(path) > 1:
        nx, ny = path[1]
        tile = unit.level.tiles[nx][ny]
        if tile.can_walk(unit.flying):
            return MoveAction(x=nx, y=ny)

    return PassAction()


def _get_flee_move(unit: Unit, threat: Unit) -> MoveAction | None:
    """Move one step away from threat."""
    if unit.level is None:
        return None

    ux, uy = unit.x, unit.y
    tx, ty = threat.x, threat.y

    # Move in opposite direction from threat
    dx = 0 if tx == ux else (-1 if tx > ux else 1)
    dy = 0 if ty == uy else (-1 if ty > uy else 1)

    # Try direct flee, then perpendicular options
    candidates = [(ux + dx, uy + dy)]
    if dx != 0:
        candidates.append((ux + dx, uy))
    if dy != 0:
        candidates.append((ux, uy + dy))
    # Perpendicular
    if dx == 0:
        candidates.extend([(ux + 1, uy + dy), (ux - 1, uy + dy)])
    if dy == 0:
        candidates.extend([(ux + dx, uy + 1), (ux + dx, uy - 1)])

    for nx, ny in candidates:
        if unit.level.in_bounds(nx, ny):
            tile = unit.level.tiles[nx][ny]
            if tile.can_walk(unit.flying):
                return MoveAction(x=nx, y=ny)

    return None


def _strafe(unit: Unit, target: Unit) -> MoveAction | PassAction:
    """Move perpendicular to the target (maintain distance, change angle)."""
    if unit.level is None:
        return PassAction()

    ux, uy = unit.x, unit.y
    tx, ty = target.x, target.y
    dx, dy = tx - ux, ty - uy

    # Perpendicular directions
    perp_moves = []
    if abs(dx) >= abs(dy):
        perp_moves = [(ux, uy + 1), (ux, uy - 1)]
    else:
        perp_moves = [(ux + 1, uy), (ux - 1, uy)]

    for nx, ny in perp_moves:
        if unit.level.in_bounds(nx, ny):
            tile = unit.level.tiles[nx][ny]
            if tile.can_walk(unit.flying):
                return MoveAction(x=nx, y=ny)

    return PassAction()


def _dist(a: Unit, b: Unit) -> int:
    """Chebyshev distance between two units."""
    return max(abs(a.x - b.x), abs(a.y - b.y))
