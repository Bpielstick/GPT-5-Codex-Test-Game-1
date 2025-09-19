"""Entry point for the Command & Conquer inspired pixel-art RTS observer."""

from __future__ import annotations

import sys

import pygame

from rts import config
from rts.game import RTSGame
from rts.ui import UIManager


def main() -> int:
    pygame.init()
    pygame.display.set_caption("Pixel Commanders")
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.Font(config.UI_FONT_NAME, 24)
    small_font = pygame.font.Font(config.UI_FONT_NAME, 16)

    game = RTSGame()
    ui = UIManager()

    paused = False

    def pause_game() -> None:
        nonlocal paused
        paused = True

    def resume_game() -> None:
        nonlocal paused
        paused = False

    def restart_game() -> None:
        nonlocal paused
        game.reset()
        paused = False

    button_y = config.SCREEN_HEIGHT - config.UI_BAR_HEIGHT + 14
    start_x = config.SCREEN_WIDTH - (config.BUTTON_SIZE[0] + config.BUTTON_PADDING) * 3 - 20

    ui.add_button("Pause", (start_x, button_y), pause_game)
    ui.add_button(
        "Resume",
        (start_x + config.BUTTON_SIZE[0] + config.BUTTON_PADDING, button_y),
        resume_game,
    )
    ui.add_button(
        "Restart",
        (
            start_x + 2 * (config.BUTTON_SIZE[0] + config.BUTTON_PADDING),
            button_y,
        ),
        restart_game,
    )

    running = True
    while running:
        dt_ms = clock.tick(config.FRAME_RATE)
        dt = dt_ms / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                break
            if ui.handle_event(event):
                continue

        keys = pygame.key.get_pressed()
        if game.camera is not None:
            dx = dy = 0.0
            scroll_amount = config.CAMERA_SCROLL_SPEED * dt
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= scroll_amount
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += scroll_amount
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= scroll_amount
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += scroll_amount
            if dx or dy:
                game.camera.move(dx, dy)

        if not paused:
            game.update(dt)

        game.draw(screen, font, small_font)
        ui.draw(screen, font)

        if paused:
            overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            paused_text = font.render("Paused", True, config.COLORS["text"])
            screen.blit(paused_text, paused_text.get_rect(center=screen.get_rect().center))

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
