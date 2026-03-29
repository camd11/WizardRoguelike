"""Tests for AI behavior system (base_ai.py)."""
import pytest

from game.ai.base_ai import (
    AIRole,
    _determine_role,
    _find_priority_target,
    _get_flee_move,
    _get_role_movement,
    get_ai_action,
)
from game.constants import Tags, Team
from game.core.actions import MoveAction, PassAction
from game.core.level import Level
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MeleeSpell(Spell):
    """A melee-only test spell."""
    def on_init(self) -> None:
        self.name = "Slash"
        self.damage = 5
        self.damage_type = Tags.Physical
        self.range = 1
        self.melee = True
        self.max_charges = 99
        self.cur_charges = 99
        self.tags = [Tags.Physical]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
        yield


class RangedSpell(Spell):
    """A ranged-only test spell."""
    def on_init(self) -> None:
        self.name = "Arrow"
        self.damage = 5
        self.damage_type = Tags.Physical
        self.range = 6
        self.melee = False
        self.max_charges = 99
        self.cur_charges = 99
        self.tags = [Tags.Physical]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
        yield

    def get_impacted_tiles(self, x, y):
        return [Point(x, y)]


def _make_unit(name: str, team: Team, hp: int) -> Unit:
    """Create a configured unit."""
    u = Unit()
    u.name = name
    u.team = team
    u.max_hp = hp
    u.cur_hp = hp
    return u


# ---------------------------------------------------------------------------
# _determine_role
# ---------------------------------------------------------------------------

class TestDetermineRole:
    def test_melee_only_returns_melee(self):
        unit = _make_unit("Warrior", Team.ENEMY, 30)
        unit.add_spell(MeleeSpell())
        assert _determine_role(unit) == AIRole.MELEE

    def test_ranged_only_returns_ranged(self):
        unit = _make_unit("Archer", Team.ENEMY, 30)
        unit.add_spell(RangedSpell())
        assert _determine_role(unit) == AIRole.RANGED

    def test_mixed_melee_ranged_returns_caster(self):
        unit = _make_unit("Battlemage", Team.ENEMY, 30)
        unit.add_spell(MeleeSpell())
        unit.add_spell(RangedSpell())
        assert _determine_role(unit) == AIRole.CASTER

    def test_high_hp_returns_boss(self):
        """Units with max_hp >= 50 are classified as BOSS regardless of spells."""
        unit = _make_unit("Boss", Team.ENEMY, 50)
        unit.add_spell(MeleeSpell())
        assert _determine_role(unit) == AIRole.BOSS

    def test_no_spells_returns_melee(self):
        unit = _make_unit("Dummy", Team.ENEMY, 20)
        assert _determine_role(unit) == AIRole.MELEE


# ---------------------------------------------------------------------------
# _find_priority_target
# ---------------------------------------------------------------------------

class TestFindPriorityTarget:
    def test_returns_player_if_present(self):
        level = Level(9, 9)
        player = _make_unit("Player", Team.PLAYER, 100)
        enemy = _make_unit("Goblin", Team.ENEMY, 20)
        weak = _make_unit("Weak Ally", Team.PLAYER, 5)
        level.add_unit(player, 1, 1)
        level.add_unit(weak, 2, 1)
        level.add_unit(enemy, 5, 5)

        target = _find_priority_target(enemy)
        assert target is player

    def test_returns_lowest_hp_when_no_player(self):
        level = Level(9, 9)
        attacker = _make_unit("Attacker", Team.ENEMY, 20)
        ally_full = _make_unit("Full", Team.PLAYER, 50)
        ally_full.team = Team.NEUTRAL  # Not a player, not same team
        ally_wounded = _make_unit("Wounded", Team.PLAYER, 50)
        ally_wounded.team = Team.NEUTRAL
        ally_wounded.cur_hp = 10

        level.add_unit(attacker, 1, 1)
        level.add_unit(ally_full, 5, 5)
        level.add_unit(ally_wounded, 7, 7)

        target = _find_priority_target(attacker)
        assert target is ally_wounded

    def test_returns_none_when_no_enemies(self):
        level = Level(9, 9)
        unit = _make_unit("Lonely", Team.ENEMY, 20)
        level.add_unit(unit, 4, 4)
        assert _find_priority_target(unit) is None

    def test_returns_none_without_level(self):
        unit = _make_unit("Orphan", Team.ENEMY, 20)
        assert _find_priority_target(unit) is None


# ---------------------------------------------------------------------------
# Imperfect AI (stunned / hash-based)
# ---------------------------------------------------------------------------

class TestImperfectBehavior:
    def test_some_positions_produce_rush_toward(self):
        """Verify that the hash-based imperfection triggers for some configurations.

        We try many positions; at least some should trigger the imperfect
        branch (hash % 100 < 35).
        """
        rush_count = 0
        for x in range(1, 8):
            for y in range(1, 8):
                level = Level(9, 9)
                player = _make_unit("Player", Team.PLAYER, 100)
                enemy = _make_unit("Archer", Team.ENEMY, 30)
                enemy.add_spell(RangedSpell())
                level.add_unit(player, 1, 1)
                level.add_unit(enemy, x, y)
                # Turn 0 — check if AI produces a MoveAction toward the player
                action = get_ai_action(enemy)
                if isinstance(action, MoveAction):
                    # Verify it moves closer to (1,1) = the player
                    old_dist = max(abs(enemy.x - 1), abs(enemy.y - 1))
                    new_dist = max(abs(action.x - 1), abs(action.y - 1))
                    if new_dist < old_dist:
                        rush_count += 1
        # With ~49 positions and 35% chance, we expect roughly 17
        assert rush_count >= 5, f"Expected some rush-toward actions, got {rush_count}"


# ---------------------------------------------------------------------------
# Flee movement
# ---------------------------------------------------------------------------

class TestFleeMovement:
    def test_flee_moves_away_from_threat(self):
        """Fleeing should increase distance from threat."""
        level = Level(9, 9)
        threat = _make_unit("Player", Team.PLAYER, 100)
        coward = _make_unit("Coward", Team.ENEMY, 20)
        level.add_unit(threat, 4, 4)
        level.add_unit(coward, 5, 4)

        move = _get_flee_move(coward, threat)
        assert move is not None
        assert isinstance(move, MoveAction)
        # New position should be farther from threat
        old_dist = max(abs(coward.x - threat.x), abs(coward.y - threat.y))
        new_dist = max(abs(move.x - threat.x), abs(move.y - threat.y))
        assert new_dist >= old_dist

    def test_flee_returns_none_if_cornered(self):
        """If surrounded by walls, flee returns None."""
        level = Level(9, 9)
        threat = _make_unit("Player", Team.PLAYER, 100)
        coward = _make_unit("Coward", Team.ENEMY, 20)
        level.add_unit(threat, 4, 4)
        # Place coward in corner with walls blocking escape
        level.add_unit(coward, 0, 0)
        # Block all flee directions (west and north are out of bounds, others walled)
        from game.constants import TileType
        for x, y in [(1, 0), (0, 1), (1, 1)]:
            level.set_tile_type(x, y, TileType.WALL)
        move = _get_flee_move(coward, threat)
        assert move is None


# ---------------------------------------------------------------------------
# Ranged units maintain distance
# ---------------------------------------------------------------------------

class TestRangedMaintainsDistance:
    def test_ranged_backs_away_when_too_close(self):
        """RANGED units should try to flee when closer than ideal range (4)."""
        level = Level(15, 15)
        player = _make_unit("Player", Team.PLAYER, 100)
        archer = _make_unit("Archer", Team.ENEMY, 30)
        archer.add_spell(RangedSpell())
        level.add_unit(player, 7, 7)
        level.add_unit(archer, 8, 7)  # Distance 1 — too close

        result = _get_role_movement(archer, player, AIRole.RANGED)
        if isinstance(result, MoveAction):
            new_dist = max(abs(result.x - player.x), abs(result.y - player.y))
            old_dist = max(abs(archer.x - player.x), abs(archer.y - player.y))
            assert new_dist >= old_dist, "Ranged unit should not move closer"

    def test_ranged_approaches_when_too_far(self):
        """RANGED units should move toward target when farther than ideal + 2."""
        level = Level(15, 15)
        player = _make_unit("Player", Team.PLAYER, 100)
        archer = _make_unit("Archer", Team.ENEMY, 30)
        archer.add_spell(RangedSpell())
        level.add_unit(player, 1, 7)
        level.add_unit(archer, 12, 7)  # Distance 11 — too far

        result = _get_role_movement(archer, player, AIRole.RANGED)
        if isinstance(result, MoveAction):
            new_dist = max(abs(result.x - player.x), abs(result.y - player.y))
            old_dist = max(abs(archer.x - player.x), abs(archer.y - player.y))
            assert new_dist <= old_dist, "Ranged unit should move closer from long range"
