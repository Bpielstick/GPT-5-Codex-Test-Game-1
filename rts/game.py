"""Core game loop helpers for the pixel-art RTS simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import random
from typing import List, Optional, Sequence, Tuple

import pygame

from . import config
from .ai import AIController
from .camera import Camera
from .entities import Structure, Unit
from .map import GameMap, TileType
from .utils import TilePos, a_star


@dataclass
class PlayerState:
    id: int
    name: str
    primary_color: pygame.Color
    shadow_color: pygame.Color
    ai: AIController
    resources: float = config.INITIAL_RESOURCES
    production_timer: float = 0.0
    pending_unit_ready: bool = False
    structures: List[Structure] = field(default_factory=list)
    units: List[Unit] = field(default_factory=list)
    defeated: bool = False

    def reset_round(self) -> None:
        self.resources = config.INITIAL_RESOURCES
        self.production_timer = 0.0
        self.pending_unit_ready = False
        self.structures.clear()
        self.units.clear()
        self.defeated = False


class RTSGame:
    """High-level controller coordinating the match."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.map: GameMap
        self.players: List[PlayerState] = []
        self.camera: Optional[Camera] = None
        self.elapsed_time: float = 0.0
        self.winner_id: Optional[int] = None
        self._entity_id = itertools.count(1)
        self._tile_surfaces = {}
        self._unit_surfaces = {}
        self._structure_surface: Optional[pygame.Surface] = None
        self.reset()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def reset(self) -> None:
        map_seed = self.rng.randint(0, 9_999_999)
        self.map = GameMap(config.MAP_WIDTH, config.MAP_HEIGHT, rng=random.Random(map_seed))
        self.camera = Camera(
            config.SCREEN_WIDTH,
            config.SCREEN_HEIGHT - config.UI_BAR_HEIGHT,
            self.map.width * config.TILE_SIZE,
            self.map.height * config.TILE_SIZE,
        )
        self.elapsed_time = 0.0
        self.winner_id = None
        self._entity_id = itertools.count(1)
        self._tile_surfaces = self._create_tile_surfaces()
        self._unit_surfaces = {}
        self._structure_surface = None

        if not self.players:
            self.players = self._create_players()
        for player in self.players:
            player.reset_round()
        self._place_starting_bases()
        if self.camera is not None:
            midpoint = (
                self.map.width * config.TILE_SIZE / 2,
                self.map.height * config.TILE_SIZE / 2,
            )
            self.camera.center_on(*midpoint)

    def _create_players(self) -> List[PlayerState]:
        names = ["Red Horizon", "Blue Dawn"]
        players: List[PlayerState] = []
        for idx in range(2):
            primary, shadow = config.PLAYER_COLORS[idx % len(config.PLAYER_COLORS)]
            ai = AIController(
                name=names[idx],
                aggression=1.0 + idx * 0.25,
                rng=random.Random(self.rng.randint(0, 1_000_000)),
            )
            players.append(
                PlayerState(
                    id=idx,
                    name=names[idx],
                    primary_color=primary,
                    shadow_color=shadow,
                    ai=ai,
                )
            )
        return players

    def _place_starting_bases(self) -> None:
        positions = [
            (8, 8),
            (self.map.width - 9, self.map.height - 9),
        ]
        for player, preferred in zip(self.players, positions):
            tile = self._find_spawn_location_near(preferred)
            self.map.force_clear_area(tile, radius=5)
            world_x, world_y = self.map.to_world(tile)
            base = Structure(
                id=next(self._entity_id),
                player_id=player.id,
                position=pygame.Vector2(world_x, world_y),
                radius=config.TILE_SIZE * 1.3,
                max_health=config.BASE_MAX_HEALTH,
                health=config.BASE_MAX_HEALTH,
                name="Command HQ",
            )
            player.structures.append(base)

    def _find_spawn_location_near(self, preferred: TilePos) -> TilePos:
        px, py = preferred
        for radius in range(2, max(self.map.width, self.map.height)):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    tx, ty = px + dx, py + dy
                    if not self.map.in_bounds((tx, ty)):
                        continue
                    if self.map.is_walkable((tx, ty)):
                        return (tx, ty)
        return self.map.random_walkable_tile()

    def _create_tile_surfaces(self) -> dict[TileType, pygame.Surface]:
        surfaces: dict[TileType, pygame.Surface] = {}
        for tile_type, base_color in [
            (TileType.GRASS, config.COLORS["grass"]),
            (TileType.FOREST, config.COLORS["forest"]),
            (TileType.MOUNTAIN, config.COLORS["mountain"]),
            (TileType.WATER, config.COLORS["water"]),
        ]:
            surf = pygame.Surface((config.TILE_SIZE, config.TILE_SIZE))
            surf.fill(base_color)
            # Add checker dithering for a pixel-art inspired look.
            for y in range(0, config.TILE_SIZE, 2):
                for x in range(0, config.TILE_SIZE, 2):
                    if (x + y) % 4 == 0:
                        darker = pygame.Color(base_color)
                        darker.r = int(darker.r * 0.8)
                        darker.g = int(darker.g * 0.8)
                        darker.b = int(darker.b * 0.8)
                        surf.set_at((x, y), darker)
            surfaces[tile_type] = surf.convert()
        return surfaces

    def _get_unit_surface(self, player: PlayerState) -> pygame.Surface:
        if player.id not in self._unit_surfaces:
            surf = pygame.Surface((int(config.TILE_SIZE * 0.9), int(config.TILE_SIZE * 0.9)), pygame.SRCALPHA)
            surf.fill(player.shadow_color)
            inner_rect = surf.get_rect().inflate(-4, -4)
            pygame.draw.rect(surf, player.primary_color, inner_rect, border_radius=3)
            self._unit_surfaces[player.id] = surf
        return self._unit_surfaces[player.id]

    def _get_structure_surface(self) -> pygame.Surface:
        if self._structure_surface is None:
            size = int(config.TILE_SIZE * 2.2)
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            body_color = pygame.Color(110, 110, 116)
            roof_color = pygame.Color(179, 179, 188)
            pygame.draw.rect(surf, body_color, (0, 6, size, size - 6), border_radius=4)
            pygame.draw.rect(surf, roof_color, (4, 0, size - 8, size // 2), border_radius=4)
            pygame.draw.rect(surf, config.COLORS["grid_shadow"], (0, 6, size, size - 6), width=2, border_radius=4)
            self._structure_surface = surf
        return self._structure_surface

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.winner_id is not None:
            return

        self.elapsed_time += dt
        for player in self.players:
            player.ai.update(dt, self, player)

        for player in self.players:
            alive_units: List[Unit] = []
            for unit in player.units:
                if not unit.alive:
                    continue
                unit.tick_cooldown(dt)
                unit.update_movement(dt, self.map.to_world)
                target = self._find_attack_target(unit, player)
                if target is not None:
                    distance = (target.position - unit.position).length()
                    if distance <= unit.attack_range:
                        unit.clear_path()
                        if unit.can_attack():
                            unit.attack(target)
                    else:
                        # pursue target actively
                        target_tile = (
                            int(target.position.x // config.TILE_SIZE),
                            int(target.position.y // config.TILE_SIZE),
                        )
                        self.order_unit_to_tile(unit, target_tile)
                alive_units.append(unit)
            player.units = alive_units

        self._cleanup_destroyed_structures()
        self._check_victory()

    def _cleanup_destroyed_structures(self) -> None:
        for player in self.players:
            still_alive = []
            defeated = True
            for structure in player.structures:
                if structure.alive:
                    still_alive.append(structure)
                    defeated = False
            player.structures = still_alive
            player.defeated = defeated and not player.units

    def _check_victory(self) -> None:
        alive_players = [p for p in self.players if not p.defeated]
        if len(alive_players) == 1:
            self.winner_id = alive_players[0].id

    def _find_attack_target(self, unit: Unit, owner: PlayerState) -> Optional[Structure | Unit]:
        closest: Optional[Structure | Unit] = None
        closest_distance = float("inf")
        for enemy in self._enemy_players(owner):
            for structure in enemy.structures:
                if not structure.alive:
                    continue
                distance = (structure.position - unit.position).length()
                if distance < closest_distance:
                    closest_distance = distance
                    closest = structure
            for enemy_unit in enemy.units:
                if not enemy_unit.alive:
                    continue
                distance = (enemy_unit.position - unit.position).length()
                if distance < closest_distance and distance <= unit.vision_radius:
                    closest_distance = distance
                    closest = enemy_unit
        return closest

    def _enemy_players(self, player: PlayerState) -> Sequence[PlayerState]:
        return [p for p in self.players if p.id != player.id and not p.defeated]

    def find_spawn_tile(self, player: PlayerState) -> Optional[TilePos]:
        if not player.structures:
            return None
        base = player.structures[0]
        base_tile = base.tile_position()
        for radius in range(1, 8):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if abs(dx) + abs(dy) > radius:
                        continue
                    tile = (base_tile[0] + dx, base_tile[1] + dy)
                    if not self.map.in_bounds(tile):
                        continue
                    if not self.map.is_walkable(tile):
                        continue
                    if self._is_tile_occupied(tile):
                        continue
                    return tile
        return None

    def spawn_unit(self, player: PlayerState, tile: TilePos) -> Unit:
        world_x, world_y = self.map.to_world(tile)
        jitter = pygame.Vector2(self.rng.uniform(-2, 2), self.rng.uniform(-2, 2))
        unit = Unit(
            id=next(self._entity_id),
            player_id=player.id,
            position=pygame.Vector2(world_x, world_y) + jitter,
            radius=config.TILE_SIZE * 0.45,
            max_health=config.UNIT_MAX_HEALTH,
            health=config.UNIT_MAX_HEALTH,
        )
        player.units.append(unit)
        return unit

    def order_unit_to_tile(self, unit: Unit, tile: TilePos) -> None:
        if not self.map.in_bounds(tile):
            return
        unit.set_goal(tile)
        if not self.map.is_walkable(tile):
            tile = self._find_nearest_walkable(tile)
        start = unit.tile_position()
        path = a_star(self.map, start, tile)
        if path is None:
            return
        # Remove the current tile from the path to avoid jittering.
        if path and path[0] == start:
            path = path[1:]
        if path:
            unit.assign_path(path)

    def choose_attack_target(self, player: PlayerState) -> Optional[TilePos]:
        enemies = [p for p in self.players if p.id != player.id and (p.units or p.structures)]
        if not enemies:
            return None
        enemy = self.rng.choice(enemies)
        candidates: List[TilePos] = []
        for structure in enemy.structures:
            candidates.append(structure.tile_position())
        for unit in enemy.units:
            if unit.alive:
                candidates.append(unit.tile_position())
        if not candidates:
            return None
        return self.rng.choice(candidates)

    def _find_nearest_walkable(self, tile: TilePos) -> TilePos:
        if self.map.is_walkable(tile):
            return tile
        for radius in range(1, 10):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    candidate = (tile[0] + dx, tile[1] + dy)
                    if not self.map.in_bounds(candidate):
                        continue
                    if self.map.is_walkable(candidate):
                        return candidate
        return tile

    def _is_tile_occupied(self, tile: TilePos) -> bool:
        for player in self.players:
            for unit in player.units:
                if unit.alive and unit.tile_position() == tile:
                    return True
            for structure in player.structures:
                if structure.tile_position() == tile:
                    return True
        return False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        assert self.camera is not None
        surface.fill(config.COLORS["background"])
        self._draw_map(surface)
        self._draw_entities(surface)
        self._draw_ui(surface, font, small_font)

    def _draw_map(self, surface: pygame.Surface) -> None:
        assert self.camera is not None
        view = self.camera.visible_tile_bounds()
        tile_size = config.TILE_SIZE
        max_x = min(self.map.width, view.left + view.width)
        max_y = min(self.map.height, view.top + view.height)
        for y in range(view.top, max_y):
            for x in range(view.left, max_x):
                tile = self.map.tiles[y][x]
                tile_surface = self._tile_surfaces[tile.type]
                screen_x = int(x * tile_size - self.camera.position.x)
                screen_y = int(y * tile_size - self.camera.position.y)
                surface.blit(tile_surface, (screen_x, screen_y))

    def _draw_entities(self, surface: pygame.Surface) -> None:
        assert self.camera is not None
        for player in self.players:
            for structure in player.structures:
                self._draw_structure(surface, structure)
        for player in self.players:
            for unit in player.units:
                if unit.alive:
                    self._draw_unit(surface, unit, player)

    def _draw_structure(self, surface: pygame.Surface, structure: Structure) -> None:
        assert self.camera is not None
        sprite = self._get_structure_surface()
        rect = sprite.get_rect(center=self.camera.world_to_screen(structure.position.x, structure.position.y))
        surface.blit(sprite, rect)
        self._draw_health_bar(surface, rect.midtop, structure)

    def _draw_unit(self, surface: pygame.Surface, unit: Unit, player: PlayerState) -> None:
        assert self.camera is not None
        sprite = self._get_unit_surface(player)
        rect = sprite.get_rect(center=self.camera.world_to_screen(unit.position.x, unit.position.y))
        surface.blit(sprite, rect)
        self._draw_health_bar(surface, rect.midtop, unit, width=rect.width)

    def _draw_health_bar(
        self,
        surface: pygame.Surface,
        top_center: Tuple[int, int],
        entity: Structure | Unit,
        width: Optional[int] = None,
    ) -> None:
        if entity.health >= entity.max_health:
            return
        if width is None:
            width = int(config.TILE_SIZE * 2.0)
        bar_height = 6
        back_rect = pygame.Rect(0, 0, width, bar_height)
        back_rect.midtop = (top_center[0], top_center[1] - 12)
        pygame.draw.rect(surface, config.COLORS["health_back"], back_rect)
        ratio = max(0.0, entity.health / entity.max_health)
        fill_rect = pygame.Rect(back_rect)
        fill_rect.width = int(back_rect.width * ratio)
        pygame.draw.rect(surface, config.COLORS["health_front"], fill_rect)

    def _draw_ui(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        ui_rect = pygame.Rect(0, config.SCREEN_HEIGHT - config.UI_BAR_HEIGHT, config.SCREEN_WIDTH, config.UI_BAR_HEIGHT)
        pygame.draw.rect(surface, config.COLORS["ui_panel"], ui_rect)
        pygame.draw.rect(surface, config.COLORS["ui_panel_border"], ui_rect, width=2)

        time_text = font.render(f"Time: {self.elapsed_time:05.1f}s", True, config.COLORS["text"])
        surface.blit(time_text, (20, ui_rect.y + 8))

        status_x = 20
        status_y = ui_rect.y + 36
        for player in self.players:
            info = (
                f"{player.name}  Units: {len(player.units):02d}  Resources: {int(player.resources)}"
            )
            if player.defeated:
                info += " (Defeated)"
            text = small_font.render(info, True, player.primary_color)
            surface.blit(text, (status_x, status_y))
            status_y += 18

        if self.winner_id is not None:
            winner = next(p for p in self.players if p.id == self.winner_id)
            banner = font.render(f"{winner.name} wins!", True, winner.primary_color)
            banner_rect = banner.get_rect(center=(config.SCREEN_WIDTH // 2, ui_rect.y + ui_rect.height // 2))
            surface.blit(banner, banner_rect)


__all__ = ["RTSGame", "PlayerState"]
