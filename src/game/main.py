"""Main entry point — Pygame init, game loop, state machine.

State flow (modeled on RW2):
  SHOP → LEVEL → SHOP → LEVEL → ... → GAME_OVER

In SHOP: clickable component grid, craft spells, click Start
In LEVEL: turn-based gameplay until all enemies dead or player dies
In GAME_OVER: show stats, press Space to quit or R to restart
"""
from __future__ import annotations

import sys
from enum import Enum, auto

import pygame

from game.core.events import EventOnDamaged, EventOnDeath
from game.game.game_state import Game
from game.game.serialization import load_game, restore_game
from game.rendering.input_handler import InputHandler
from game.rendering.renderer import SCREEN_H, SCREEN_W, Renderer
from game.rendering.ui_shop import ShopUI


class GameMode(Enum):
    SHOP = auto()
    LEVEL = auto()
    GAME_OVER = auto()


def main(seed: int | None = None) -> None:
    """Run the game."""
    pygame.init()
    pygame.display.set_caption("Wizard Roguelike — Spell Crafter")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    # Check for saved game
    save_data = load_game()
    if save_data is not None:
        game = restore_game(save_data)
    else:
        game = Game(seed=seed)

    renderer = Renderer(screen)
    input_handler = InputHandler()
    shop_ui = ShopUI(SCREEN_W, SCREEN_H)
    mode = GameMode.SHOP

    # Hook damage events to renderer for visual feedback
    def _on_damaged(evt):
        renderer.anims.add_damage_number(evt.unit.x, evt.unit.y, evt.damage,
                                          evt.damage_type.color if hasattr(evt.damage_type, 'color') else (255, 80, 40))
        renderer.anims.add_tile_flash(evt.unit.x, evt.unit.y, (255, 100, 50))
        renderer.add_log(f"{evt.unit.name} takes {evt.damage} {evt.damage_type.name} damage")

    def _on_death(evt):
        renderer.add_log(f"{evt.unit.name} is destroyed!")
        renderer.anims.add_death_effect(evt.unit.x, evt.unit.y)

    def _start_level():
        nonlocal mode
        gen_level = game.start_level()
        mode = GameMode.LEVEL
        game.current_level.event_handler.subscribe(EventOnDamaged, _on_damaged)
        game.current_level.event_handler.subscribe(EventOnDeath, _on_death)
        renderer.add_log(f"--- Level {game.level_num}: {gen_level.biome.name} ---")
        renderer.add_log(f"    Enemies: {game.current_level.enemies_remaining()}")

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

        if mode == GameMode.SHOP:
            # Handle shop input (clicks and keyboard)
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    result = shop_ui.handle_click(event.pos[0], event.pos[1], game)
                    if result == "start_level":
                        _start_level()
                elif event.type == pygame.MOUSEMOTION:
                    shop_ui.handle_motion(event.pos[0], event.pos[1])
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and game.player.spells:
                        _start_level()

            if mode == GameMode.SHOP:
                shop_ui.draw(screen, game, renderer.font, renderer.font_large, renderer.font_small)

        elif mode == GameMode.LEVEL:
            if game.current_level and game.current_level.is_awaiting_input:
                input_handler.process_level_events(events, game, renderer)
                action = input_handler.get_action()
                if action is not None:
                    result = game.submit_action(action)
                    for msg in result.get("events", []):
                        renderer.add_log(msg)

                    if result.get("player_dead") or game.game_over:
                        mode = GameMode.GAME_OVER
                    elif result.get("level_clear"):
                        if game.game_over:
                            mode = GameMode.GAME_OVER
                        else:
                            mode = GameMode.SHOP
                            shop_ui.message = f"Level {game.level_num} cleared! +{game.sp_per_level} SP"
                            shop_ui.message_color = (80, 200, 80)
            elif game.current_level:
                game.current_level.advance_spells()
                if not game.player.is_alive():
                    game.defeat = True
                    game.game_over = True
                    mode = GameMode.GAME_OVER

            renderer.render_game(game)

        elif mode == GameMode.GAME_OVER:
            renderer.render_game_over(game)
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        running = False
                    elif event.key == pygame.K_r:
                        # Restart
                        game = Game(seed=None)
                        renderer = Renderer(screen)
                        shop_ui = ShopUI(SCREEN_W, SCREEN_H)
                        mode = GameMode.SHOP

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    seed = None
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            pass
    main(seed=seed)
