"""Visual replay viewer — watch recorded AI games with the Pygame renderer.

Usage:
    python -m game.replay_viewer path/to/replay.json [--speed 5]

Replays are produced by the headless bot's recorder. This viewer steps
through each action with visual rendering so you can watch AI play.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pygame

from game.core.events import EventOnDamaged, EventOnDeath
from game.rendering.renderer import SCREEN_H, SCREEN_W, Renderer
from tests.replay.recorder import ReplayRecorder
from tests.replay.replayer import ReplayReplayer


def view_replay(replay_path: str, actions_per_second: float = 3.0) -> None:
    """Play back a replay file with visual rendering."""
    replay_data = ReplayRecorder.load(replay_path)

    pygame.init()
    pygame.display.set_caption(f"Replay Viewer — seed {replay_data['seed']}")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    renderer = Renderer(screen)

    replayer = ReplayReplayer(replay_data)
    game = replayer.setup()

    # Subscribe events
    def _on_damaged(evt):
        renderer.anims.add_damage_number(evt.unit.x, evt.unit.y, evt.damage, (255, 80, 40))
        renderer.anims.add_tile_flash(evt.unit.x, evt.unit.y, (255, 100, 50))
        renderer.add_log(f"{evt.unit.name} takes {evt.damage} damage")

    def _on_death(evt):
        renderer.add_log(f"{evt.unit.name} destroyed!")

    # Start first level
    game.start_level()
    game.current_level.event_handler.subscribe(EventOnDamaged, _on_damaged)
    game.current_level.event_handler.subscribe(EventOnDeath, _on_death)
    renderer.add_log(f"--- Replay: seed {game.seed} ---")

    frame_idx = 0
    last_action_time = time.time()
    paused = False
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_RIGHT:
                    # Step forward one action
                    if frame_idx < len(replay_data["frames"]):
                        replayer.replay_step(frame_idx)
                        frame_idx += 1
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    actions_per_second = min(30, actions_per_second + 1)
                elif event.key == pygame.K_MINUS:
                    actions_per_second = max(0.5, actions_per_second - 1)

        # Auto-advance if not paused
        if not paused and frame_idx < len(replay_data["frames"]):
            now = time.time()
            if now - last_action_time >= 1.0 / actions_per_second:
                result = replayer.replay_step(frame_idx)
                frame_idx += 1
                last_action_time = now

                if result:
                    for msg in result.get("events", []):
                        renderer.add_log(msg)

                # Handle level transitions
                if game.in_shop and not game.game_over:
                    game.start_level()
                    game.current_level.event_handler.subscribe(EventOnDamaged, _on_damaged)
                    game.current_level.event_handler.subscribe(EventOnDeath, _on_death)

        # Render
        if game.game_over:
            renderer.render_game_over(game)
        elif game.current_level:
            renderer.render_game(game)

        # Status overlay
        status = f"Frame {frame_idx}/{len(replay_data['frames'])}  Speed: {actions_per_second:.0f}/s"
        if paused:
            status += "  [PAUSED - Space to resume, Right to step]"
        font = renderer.font_small
        surf = font.render(status, True, (200, 200, 100))
        screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, 2))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m game.replay_viewer <replay.json> [--speed N]")
        sys.exit(1)

    path = sys.argv[1]
    speed = 3.0
    if "--speed" in sys.argv:
        idx = sys.argv.index("--speed")
        if idx + 1 < len(sys.argv):
            speed = float(sys.argv[idx + 1])

    view_replay(path, speed)
