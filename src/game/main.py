"""Main entry point — Pygame init, game loop, state machine.

State flow (modeled on RW2):
  SHOP → LEVEL → SHOP → LEVEL → ... → GAME_OVER

In SHOP: player buys components, crafts spells, presses Enter to start
In LEVEL: turn-based gameplay until all enemies dead or player dies
In GAME_OVER: show stats, press Space to quit
"""
from __future__ import annotations

import sys
from enum import Enum, auto

import pygame

from game.core.events import EventOnDamaged, EventOnDeath
from game.game.game_state import Game
from game.rendering.input_handler import InputHandler
from game.rendering.renderer import SCREEN_H, SCREEN_W, Renderer


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

    game = Game(seed=seed)
    renderer = Renderer(screen)
    input_handler = InputHandler()
    mode = GameMode.SHOP

    # Hook damage events to renderer for visual feedback
    def _on_damaged(evt):
        renderer.anims.add_damage_number(evt.unit.x, evt.unit.y, evt.damage, (255, 80, 40))
        renderer.anims.add_tile_flash(evt.unit.x, evt.unit.y, (255, 100, 50))
        renderer.add_log(f"{evt.unit.name} takes {evt.damage} {evt.damage_type.name} damage")

    def _on_death(evt):
        renderer.add_log(f"{evt.unit.name} is destroyed!")

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

        if mode == GameMode.SHOP:
            # Render shop
            renderer.render_shop(game)

            # Draw input field
            _draw_shop_input(screen, renderer, input_handler)

            start = input_handler.process_shop_events(events, game, renderer)
            if start:
                gen_level = game.start_level()
                mode = GameMode.LEVEL
                # Subscribe damage/death events for this level
                game.current_level.event_handler.subscribe(EventOnDamaged, _on_damaged)
                game.current_level.event_handler.subscribe(EventOnDeath, _on_death)
                renderer.add_log(f"--- Level {game.level_num}: {gen_level.biome.name} ---")

        elif mode == GameMode.LEVEL:
            if game.current_level and game.current_level.is_awaiting_input:
                # Player's turn — process input
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
            elif game.current_level:
                # Advance spell animations (one frame per render tick)
                game.current_level.advance_spells()

                # Check if player died during enemy phase
                if not game.player.is_alive():
                    game.defeat = True
                    game.game_over = True
                    mode = GameMode.GAME_OVER

            renderer.render_game(game)

        elif mode == GameMode.GAME_OVER:
            renderer.render_game_over(game)
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    running = False

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


def _draw_shop_input(screen: pygame.Surface, renderer: Renderer,
                     input_handler: InputHandler) -> None:
    """Draw the text input field at the bottom of the shop screen."""
    font = renderer.font
    y = SCREEN_H - 50

    # Message
    if input_handler.shop_message:
        msg_surf = font.render(input_handler.shop_message, True, (255, 220, 100))
        screen.blit(msg_surf, (40, y - 20))

    # Input prompt
    prompt = f"> {input_handler.shop_input}_"
    prompt_surf = font.render(prompt, True, (200, 200, 200))
    screen.blit(prompt_surf, (40, y))


if __name__ == "__main__":
    seed = None
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            pass
    main(seed=seed)
