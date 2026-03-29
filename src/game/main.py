"""Main entry point — Pygame init, game loop, state machine.

State flow:
  TITLE → SHOP → LEVEL → SHOP → ... → GAME_OVER → TITLE

TITLE: New Game / Continue / Quit
SHOP: clickable component grid, craft spells, click Start
LEVEL: turn-based gameplay until all enemies dead or player dies
GAME_OVER: show stats, press Space to return to title or R to restart
"""
from __future__ import annotations

import sys
from enum import Enum, auto

import pygame

from game.core.events import EventOnDamaged, EventOnDeath
from game.game.game_state import Game
from game.game.serialization import delete_save, list_saves, load_game, restore_game
from game.rendering.input_handler import InputHandler
from game.rendering.renderer import SCREEN_H, SCREEN_W, Renderer
from game.rendering.ui_shop import ShopUI


class GameMode(Enum):
    TITLE = auto()
    SHOP = auto()
    LEVEL = auto()
    GAME_OVER = auto()


def _draw_title(screen: pygame.Surface, font_large, font, font_small, has_save: bool) -> dict:
    """Draw title screen. Returns button rects."""
    screen.fill((12, 10, 20))

    # Title
    title = "WIZARD ROGUELIKE"
    subtitle = "Spell Crafter"
    t_surf = font_large.render(title, True, (255, 220, 100))
    s_surf = font.render(subtitle, True, (180, 180, 200))
    screen.blit(t_surf, (SCREEN_W // 2 - t_surf.get_width() // 2, 180))
    screen.blit(s_surf, (SCREEN_W // 2 - s_surf.get_width() // 2, 225))

    # Tagline
    tag = "Combine Elements, Shapes, and Modifiers to craft your spells"
    tag_surf = font_small.render(tag, True, (120, 120, 140))
    screen.blit(tag_surf, (SCREEN_W // 2 - tag_surf.get_width() // 2, 260))

    buttons = {}
    btn_w, btn_h = 240, 44
    btn_x = SCREEN_W // 2 - btn_w // 2
    y = 320

    # New Game button
    new_rect = pygame.Rect(btn_x, y, btn_w, btn_h)
    pygame.draw.rect(screen, (60, 80, 120), new_rect, border_radius=6)
    pygame.draw.rect(screen, (100, 120, 160), new_rect, 2, border_radius=6)
    lbl = font.render("New Game", True, (220, 220, 240))
    screen.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2, y + 10))
    buttons["new"] = new_rect
    y += 60

    # Continue button (only if save exists)
    if has_save:
        cont_rect = pygame.Rect(btn_x, y, btn_w, btn_h)
        pygame.draw.rect(screen, (50, 90, 60), cont_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 140, 90), cont_rect, 2, border_radius=6)
        lbl = font.render("Continue", True, (200, 255, 200))
        screen.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2, y + 10))
        buttons["continue"] = cont_rect
        y += 60

    # Quit button
    quit_rect = pygame.Rect(btn_x, y, btn_w, btn_h)
    pygame.draw.rect(screen, (80, 40, 40), quit_rect, border_radius=6)
    pygame.draw.rect(screen, (140, 60, 60), quit_rect, 2, border_radius=6)
    lbl = font.render("Quit", True, (220, 180, 180))
    screen.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2, y + 10))
    buttons["quit"] = quit_rect

    # Version info
    ver = font_small.render("v0.1 — 8 elements, 11 shapes, 11 modifiers, 40+ monsters", True, (60, 60, 80))
    screen.blit(ver, (SCREEN_W // 2 - ver.get_width() // 2, SCREEN_H - 40))

    return buttons


def main(seed: int | None = None) -> None:
    """Run the game."""
    pygame.init()
    pygame.display.set_caption("Wizard Roguelike — Spell Crafter")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    renderer = Renderer(screen)
    input_handler = InputHandler()
    shop_ui = ShopUI(SCREEN_W, SCREEN_H)
    mode = GameMode.TITLE
    game = None
    title_buttons = {}

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

        if mode == GameMode.TITLE:
            has_save = bool(list_saves())
            title_buttons = _draw_title(screen, renderer.font_large, renderer.font,
                                         renderer.font_small, has_save)
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if title_buttons.get("new") and title_buttons["new"].collidepoint(mx, my):
                        delete_save()  # Fresh start
                        game = Game(seed=seed)
                        shop_ui = ShopUI(SCREEN_W, SCREEN_H)
                        renderer = Renderer(screen)
                        mode = GameMode.SHOP
                    elif title_buttons.get("continue") and title_buttons["continue"].collidepoint(mx, my):
                        save_data = load_game()
                        if save_data:
                            game = restore_game(save_data)
                            renderer = Renderer(screen)
                            shop_ui = ShopUI(SCREEN_W, SCREEN_H)
                            mode = GameMode.SHOP
                    elif title_buttons.get("quit") and title_buttons["quit"].collidepoint(mx, my):
                        running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        game = Game(seed=seed)
                        shop_ui = ShopUI(SCREEN_W, SCREEN_H)
                        renderer = Renderer(screen)
                        mode = GameMode.SHOP

        elif mode == GameMode.SHOP:
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
                        delete_save()
                        mode = GameMode.TITLE
                    elif event.key == pygame.K_r:
                        delete_save()
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
