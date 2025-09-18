"""Entity definitions for units and structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pygame

from . import config


@dataclass
class Entity:
    id: int
    player_id: int
    position: pygame.Vector2
    radius: float
    max_health: float
    health: float

    def take_damage(self, amount: float) -> None:
        self.health -= amount

    @property
    def alive(self) -> bool:
        return self.health > 0

    def heal_full(self) -> None:
        self.health = self.max_health


@dataclass
class Structure(Entity):
    name: str = "Base"

    def tile_position(self) -> Tuple[int, int]:
        return (int(self.position.x // config.TILE_SIZE), int(self.position.y // config.TILE_SIZE))


@dataclass
class Unit(Entity):
    speed: float = config.UNIT_SPEED
    attack_damage: float = config.UNIT_ATTACK_DAMAGE
    attack_range: float = config.UNIT_ATTACK_RANGE
    attack_cooldown: float = config.UNIT_ATTACK_COOLDOWN
    vision_radius: float = config.UNIT_VISION_RADIUS
    _cooldown_remaining: float = 0.0
    path: List[Tuple[int, int]] = field(default_factory=list)
    _path_index: int = 0
    _goal_tile: Optional[Tuple[int, int]] = None

    def tile_position(self) -> Tuple[int, int]:
        return (int(self.position.x // config.TILE_SIZE), int(self.position.y // config.TILE_SIZE))

    def set_goal(self, goal_tile: Tuple[int, int]) -> None:
        if goal_tile != self._goal_tile:
            self._goal_tile = goal_tile
            self.path.clear()
            self._path_index = 0

    def assign_path(self, path: List[Tuple[int, int]]) -> None:
        self.path = path
        self._path_index = 0

    def clear_path(self) -> None:
        self.path.clear()
        self._path_index = 0

    def update_movement(self, dt: float, to_world) -> None:
        if not self.path or self._path_index >= len(self.path):
            return

        target_tile = self.path[self._path_index]
        target_world = pygame.Vector2(*to_world(target_tile))
        direction = target_world - self.position
        distance = direction.length()
        if distance < 1.0:
            self._path_index += 1
            return
        if distance > 0:
            direction.scale_to_length(min(self.speed * dt, distance))
            self.position += direction

    def tick_cooldown(self, dt: float) -> None:
        if self._cooldown_remaining > 0:
            self._cooldown_remaining = max(0.0, self._cooldown_remaining - dt)

    def can_attack(self) -> bool:
        return self._cooldown_remaining <= 0.0

    def attack(self, target: Entity) -> None:
        target.take_damage(self.attack_damage)
        self._cooldown_remaining = self.attack_cooldown


__all__ = ["Entity", "Structure", "Unit"]
