"""Integration test: full turn cycle with player and enemies."""
from game.constants import Tags, Team
from game.core.actions import CastAction, MoveAction, PassAction
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import FIRE, BOLT
from game.crafting.spell_factory import CraftedSpell


class TestFullTurnCycle:
    def test_player_move_and_enemy_acts(self):
        """Advance a full turn: player moves, enemies take their turns."""
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 4)

        # Enemy far away (won't attack, will try to move closer)
        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 20
        enemy.cur_hp = 20
        from game.content.monsters.common import SimpleMeleeAttack
        enemy.add_spell(SimpleMeleeAttack(damage=3))
        level.add_unit(enemy, 7, 4)

        turns = level.iter_frame()

        # Advance to player input
        result = next(turns)
        assert level.is_awaiting_input

        # Player moves right
        result = turns.send(MoveAction(x=2, y=4))
        assert player.x == 2

        # Continue advancing until next turn
        while True:
            try:
                result = next(turns)
                if result is True:
                    break  # Turn complete
                if level.is_awaiting_input:
                    break  # Next player input
            except StopIteration:
                break

    def test_player_casts_and_kills_enemy(self):
        """Player casts a spell that kills an enemy in the turn loop."""
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 4)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 5
        enemy.cur_hp = 5
        level.add_unit(enemy, 4, 4)

        spell = CraftedSpell(FIRE, BOLT)
        player.add_spell(spell)

        turns = level.iter_frame()
        next(turns)  # Advance to player input
        assert level.is_awaiting_input

        turns.send(CastAction(spell=spell, x=4, y=4))

        # Run until turn ends
        while True:
            try:
                result = next(turns)
                if result is True:
                    break
                if level.is_awaiting_input:
                    break
            except StopIteration:
                break

        assert not enemy.is_alive()
