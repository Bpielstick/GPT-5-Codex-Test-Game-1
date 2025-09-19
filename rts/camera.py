"""Camera logic for viewing sections of the large map."""

from __future__ import annotations

from dataclasses import dataclass
import pygame

from . import config


@dataclass
class Camera:
    width: int
    height: int
    map_pixel_width: int
    map_pixel_height: int

    def __post_init__(self) -> None:
        self.position = pygame.Vector2(0.0, 0.0)
        self.clamp_to_bounds()

    def clamp_to_bounds(self) -> None:
        max_x = max(0, self.map_pixel_width - self.width)
        max_y = max(0, self.map_pixel_height - self.height)
        self.position.x = max(0.0, min(self.position.x, max_x))
        self.position.y = max(0.0, min(self.position.y, max_y))

    def move(self, dx: float, dy: float) -> None:
        self.position.x += dx
        self.position.y += dy
        self.clamp_to_bounds()

    def center_on(self, x: float, y: float) -> None:
        self.position.x = x - self.width / 2
        self.position.y = y - self.height / 2
        self.clamp_to_bounds()

    def world_to_screen(self, x: float, y: float) -> pygame.Vector2:
        return pygame.Vector2(x - self.position.x, y - self.position.y)

    def screen_to_world(self, x: float, y: float) -> pygame.Vector2:
        return pygame.Vector2(x + self.position.x, y + self.position.y)

    def visible_tile_bounds(self) -> pygame.Rect:
        left = int(self.position.x // config.TILE_SIZE)
        top = int(self.position.y // config.TILE_SIZE)
        width = int(self.width // config.TILE_SIZE) + 2
        height = int(self.height // config.TILE_SIZE) + 2
        return pygame.Rect(left, top, width, height)


__all__ = ["Camera"]
