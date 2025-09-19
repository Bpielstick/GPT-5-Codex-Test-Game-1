"""Core game orchestration for the pixel-art RTS simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import random
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

from . import config
from .ai import AIController
from .camera import Camera
from .entities import (
    STRUCTURE_DEFS,
    UNIT_DEFS,
    ResourceNode,
    Structure,
    StructureDefinition,
    Unit,
    UnitDefinition,
    structures_providing_tech,
)
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
    structures: List[Structure] = field(default_factory=list)
    units: List[Unit] = field(default_factory=list)
    defeated: bool = False
    tech_level: int = 1
    resource_timer: float = config.RESOURCE_TICK_INTERVAL

    def reset_round(self) -> None:
        self.resources = config.INITIAL_RESOURCES
        self.structures.clear()
        self.units.clear()
        self.defeated = False
        self.tech_level = 1
        self.resource_timer = config.RESOURCE_TICK_INTERVAL

    def deposits(self) -> List[Structure]:
        return [s for s in self.structures if s.definition.is_deposit and s.completed and s.alive]

    def count_structures(self, key: str, include_under_construction: bool = True) -> int:
        total = 0
        for structure in self.structures:
            if structure.definition.key != key:
                continue
            if not structure.alive:
                continue
            if structure.completed or include_under_construction:
                total += 1
        return total

    def available_producers(self, unit_key: str) -> List[Structure]:
        producers: List[Structure] = []
        for structure in self.structures:
            if not structure.alive or not structure.completed:
                continue
            if unit_key in structure.definition.produces:
                producers.append(structure)
        return producers

    def structure_by_id(self, structure_id: int) -> Optional[Structure]:
        for structure in self.structures:
            if structure.id == structure_id and structure.alive:
                return structure
        return None


class RTSGame:
    """High-level controller coordinating the match."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.map: GameMap
        self.players: List[PlayerState] = []
        self.camera: Optional[Camera] = None
        self.elapsed_time: float = 0.0
        self.winner_id: Optional[int] = None
        self.resource_nodes: List[ResourceNode] = []
        self._entity_id = itertools.count(1)
        self._resource_id = itertools.count(1)
        self._tile_surfaces: Dict[TileType, pygame.Surface] = {}
        self._unit_surfaces: Dict[Tuple[int, str], pygame.Surface] = {}
        self._structure_surfaces: Dict[str, pygame.Surface] = {}
        self._resource_surface: Optional[pygame.Surface] = None
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
        self.resource_nodes = []
        self._entity_id = itertools.count(1)
        self._resource_id = itertools.count(1)
        self._tile_surfaces = self._create_tile_surfaces()
        self._unit_surfaces.clear()
        self._structure_surfaces.clear()
        self._resource_surface = None

        if not self.players:
            self.players = self._create_players()
        for player in self.players:
            player.reset_round()

        self._place_starting_bases()
        self._spawn_initial_workers()
        self._ensure_land_bridge()
        self._spawn_resource_nodes()

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
        definition = STRUCTURE_DEFS["hq"]
        for player, preferred in zip(self.players, positions):
            tile = self._find_spawn_location_near(preferred)
            self.map.force_clear_area(tile, radius=6)
            world_x, world_y = self.map.to_world(tile)
            base = Structure(
                id=next(self._entity_id),
                player_id=player.id,
                position=pygame.Vector2(world_x, world_y),
                radius=definition.radius,
                max_health=definition.max_health,
                health=definition.max_health,
                definition=definition,
                completed=True,
                construction_remaining=0.0,
            )
            player.structures.append(base)

    def _spawn_initial_workers(self) -> None:
        for player in self.players:
            hq = next((s for s in player.structures if s.definition.key == "hq"), None)
            if hq is None:
                continue
            for _ in range(3):
                spawn = self.find_spawn_tile(player, near_structure=hq)
                if spawn is None:
                    continue
                self.spawn_unit(player, "worker", spawn, jitter=True)

    def _ensure_land_bridge(self) -> None:
        if len(self.players) < 2:
            return
        base_a = self.players[0].structures[0]
        base_b = self.players[1].structures[0]
        start = base_a.tile_position()
        end = base_b.tile_position()
        if a_star(self.map, start, end) is None:
            self.map.carve_path(start, end, radius=2)

    def _spawn_resource_nodes(self) -> None:
        self.resource_nodes = []
        attempts = 0
        target = config.RESOURCE_NODE_COUNT
        while len(self.resource_nodes) < target and attempts < target * 60:
            attempts += 1
            tile = self.map.random_walkable_tile(margin=4)
            if self._resource_too_close(tile):
                continue
            world = self.map.to_world(tile)
            amount = self.rng.uniform(*config.RESOURCE_NODE_AMOUNT_RANGE)
            node = ResourceNode(
                id=next(self._resource_id),
                position=pygame.Vector2(world[0], world[1]),
                amount=amount,
            )
            self.resource_nodes.append(node)

    def _resource_too_close(self, tile: TilePos) -> bool:
        tx, ty = tile
        for node in self.resource_nodes:
            nx, ny = node.tile_position()
            if abs(nx - tx) + abs(ny - ty) < config.RESOURCE_NODE_MIN_DISTANCE:
                return True
        for player in self.players:
            for structure in player.structures:
                sx, sy = structure.tile_position()
                if abs(sx - tx) + abs(sy - ty) < config.RESOURCE_NODE_MIN_DISTANCE:
                    return True
        return False

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

    def _create_tile_surfaces(self) -> Dict[TileType, pygame.Surface]:
        surfaces: Dict[TileType, pygame.Surface] = {}
        for tile_type, base_color in [
            (TileType.GRASS, config.COLORS["grass"]),
            (TileType.FOREST, config.COLORS["forest"]),
            (TileType.MOUNTAIN, config.COLORS["mountain"]),
            (TileType.WATER, config.COLORS["water"]),
        ]:
            surf = pygame.Surface((config.TILE_SIZE, config.TILE_SIZE))
            surf.fill(base_color)
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
            self._update_structures(player, dt)
            self._update_units(player, dt)
            self._refresh_player_state(player)

        self._cleanup_resources()
        self._check_victory()

    def _update_structures(self, player: PlayerState, dt: float) -> None:
        for structure in player.structures:
            if not structure.alive:
                continue
            if not structure.completed:
                structure.construction_remaining = max(0.0, structure.construction_remaining - dt)
                if structure.construction_remaining <= 0.0:
                    structure.completed = True
            elif structure.production_queue:
                structure.production_timer = max(0.0, structure.production_timer - dt)
                if structure.production_timer <= 0.0:
                    unit_def = structure.pop_completed_unit()
                    if unit_def is not None:
                        spawn = self.find_spawn_tile(player, near_structure=structure)
                        if spawn is not None:
                            self.spawn_unit(player, unit_def.key, spawn, jitter=True)

    def _update_units(self, player: PlayerState, dt: float) -> None:
        alive_units: List[Unit] = []
        for unit in player.units:
            if not unit.alive:
                continue
            unit.tick_cooldown(dt)
            if unit.definition.role == "worker":
                self._update_worker(unit, player, dt)
            else:
                self._update_combat_unit(unit, player, dt)
            alive_units.append(unit)
        player.units = alive_units

    def _update_worker(self, unit: Unit, player: PlayerState, dt: float) -> None:
        if unit.worker_state not in {"gather", "deposit"}:
            unit.update_movement(dt, self.map.to_world)

        if unit.worker_state == "idle":
            node = self._choose_resource_node(player)
            if node is not None:
                unit.worker_state = "to_resource"
                unit.worker_target = node.id
                unit.worker_deposit = None
                self.order_unit_to_tile(unit, node.tile_position())
            return

        if unit.worker_state == "to_resource":
            node = self._resource_by_id(unit.worker_target)
            if node is None or node.depleted:
                unit.worker_state = "idle"
                unit.worker_target = None
                unit.clear_path()
                return
            distance = (node.position - unit.position).length()
            if distance <= config.TILE_SIZE * 0.8 or not unit.path:
                unit.worker_state = "gather"
                unit.worker_timer = config.WORKER_GATHER_TIME
                unit.clear_path()
            return

        if unit.worker_state == "gather":
            node = self._resource_by_id(unit.worker_target)
            if node is None or node.depleted:
                unit.worker_state = "idle"
                unit.worker_target = None
                return
            unit.worker_timer = max(0.0, unit.worker_timer - dt)
            if unit.worker_timer <= 0.0:
                unit.worker_cargo = node.harvest(config.WORKER_CAPACITY)
                if unit.worker_cargo <= 0:
                    unit.worker_state = "idle"
                    unit.worker_target = None
                else:
                    deposit = self._nearest_deposit(player, unit.position)
                    if deposit is None:
                        unit.worker_state = "idle"
                        unit.worker_target = None
                        unit.worker_cargo = 0.0
                    else:
                        unit.worker_state = "to_deposit"
                        unit.worker_deposit = deposit.id
                        self.order_unit_to_tile(unit, deposit.tile_position())
            return

        if unit.worker_state == "to_deposit":
            deposit = player.structure_by_id(unit.worker_deposit or -1)
            if deposit is None or not deposit.completed:
                unit.worker_state = "idle"
                unit.worker_target = None
                unit.worker_deposit = None
                return
            unit.update_movement(dt, self.map.to_world)
            distance = (deposit.position - unit.position).length()
            if distance <= deposit.radius + config.TILE_SIZE * 0.6:
                unit.worker_state = "deposit"
                unit.worker_timer = config.WORKER_DEPOSIT_TIME
                unit.clear_path()
            return

        if unit.worker_state == "deposit":
            unit.worker_timer = max(0.0, unit.worker_timer - dt)
            if unit.worker_timer <= 0.0:
                player.resources += unit.worker_cargo
                unit.worker_cargo = 0.0
                unit.worker_state = "idle"
                unit.worker_target = None
                unit.worker_deposit = None
            return

    def _update_combat_unit(self, unit: Unit, player: PlayerState, dt: float) -> None:
        unit.update_movement(dt, self.map.to_world)
        target = self._find_attack_target(unit, player)
        if target is None:
            return
        distance = (target.position - unit.position).length()
        if distance <= unit.definition.attack_range:
            unit.clear_path()
            if unit.can_attack():
                unit.attack(target)
        else:
            target_tile = (
                int(target.position.x // config.TILE_SIZE),
                int(target.position.y // config.TILE_SIZE),
            )
            self.order_unit_to_tile(unit, target_tile)

    def _choose_resource_node(self, player: PlayerState) -> Optional[ResourceNode]:
        available = [node for node in self.resource_nodes if not node.depleted]
        if not available:
            return None
        hq = next((s for s in player.structures if s.definition.key == "hq"), None)
        if hq is None:
            return self.rng.choice(available)
        available.sort(key=lambda node: (node.position - hq.position).length())
        return available[0]

    def _nearest_deposit(self, player: PlayerState, position: pygame.Vector2) -> Optional[Structure]:
        deposits = player.deposits()
        if not deposits:
            return None
        deposits.sort(key=lambda s: (s.position - position).length())
        return deposits[0]

    def _resource_by_id(self, resource_id: Optional[int]) -> Optional[ResourceNode]:
        if resource_id is None:
            return None
        for node in self.resource_nodes:
            if node.id == resource_id and not node.depleted:
                return node
        return None

    def _refresh_player_state(self, player: PlayerState) -> None:
        alive_structures = [s for s in player.structures if s.alive]
        player.structures = alive_structures
        player.tech_level = structures_providing_tech(player.structures)
        alive_units = [u for u in player.units if u.alive]
        player.units = alive_units
        player.defeated = not player.structures and not player.units

    def _cleanup_resources(self) -> None:
        self.resource_nodes = [node for node in self.resource_nodes if not node.depleted]

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
                if distance < closest_distance and distance <= unit.definition.vision_radius:
                    closest_distance = distance
                    closest = enemy_unit
        return closest

    def _enemy_players(self, player: PlayerState) -> Sequence[PlayerState]:
        return [p for p in self.players if p.id != player.id and not p.defeated]

    def find_spawn_tile(self, player: PlayerState, near_structure: Optional[Structure] = None) -> Optional[TilePos]:
        if near_structure is None:
            if not player.structures:
                return None
            near_structure = player.structures[0]
        base_tile = near_structure.tile_position()
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

    def spawn_unit(self, player: PlayerState, unit_key: str, tile: TilePos, jitter: bool = False) -> Optional[Unit]:
        if unit_key not in UNIT_DEFS:
            return None
        definition = UNIT_DEFS[unit_key]
        world_x, world_y = self.map.to_world(tile)
        position = pygame.Vector2(world_x, world_y)
        if jitter:
            position += pygame.Vector2(self.rng.uniform(-2, 2), self.rng.uniform(-2, 2))
        radius = self._unit_radius(definition)
        unit = Unit(
            id=next(self._entity_id),
            player_id=player.id,
            position=position,
            radius=radius,
            max_health=definition.max_health,
            health=definition.max_health,
            definition=definition,
        )
        player.units.append(unit)
        return unit

    def start_structure_construction(self, player: PlayerState, key: str) -> Optional[Structure]:
        if key not in STRUCTURE_DEFS:
            return None
        definition = STRUCTURE_DEFS[key]
        if player.tech_level < definition.required_tech:
            return None
        if player.resources < definition.cost:
            return None
        if len(player.structures) >= config.MAX_STRUCTURES:
            return None
        site = self._find_structure_site(player, definition)
        if site is None:
            return None
        player.resources -= definition.cost
        world_x, world_y = self.map.to_world(site)
        structure = Structure(
            id=next(self._entity_id),
            player_id=player.id,
            position=pygame.Vector2(world_x, world_y),
            radius=definition.radius,
            max_health=definition.max_health,
            health=definition.max_health,
            definition=definition,
            completed=definition.build_time == 0.0,
            construction_remaining=definition.build_time,
        )
        player.structures.append(structure)
        return structure

    def queue_unit_production(self, player: PlayerState, structure: Structure, unit_key: str) -> bool:
        if structure not in player.structures:
            return False
        if not structure.alive or not structure.completed:
            return False
        if unit_key not in UNIT_DEFS:
            return False
        definition = UNIT_DEFS[unit_key]
        if definition.tech_level > player.tech_level:
            return False
        if unit_key not in structure.definition.produces:
            return False
        if len(structure.production_queue) >= 4:
            return False
        if player.resources < definition.cost:
            return False
        player.resources -= definition.cost
        structure.enqueue_unit(definition)
        return True

    def _find_structure_site(self, player: PlayerState, definition: StructureDefinition) -> Optional[TilePos]:
        if not player.structures:
            return None
        anchor = player.structures[0]
        anchor_tile = anchor.tile_position()
        for radius in range(3, 18):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    tile = (anchor_tile[0] + dx, anchor_tile[1] + dy)
                    if not self.map.in_bounds(tile):
                        continue
                    if not self.map.is_walkable(tile):
                        continue
                    world = self.map.to_world(tile)
                    if self._site_blocked(world, definition.radius):
                        continue
                    return tile
        return None

    def _site_blocked(self, world: Tuple[float, float], radius: float) -> bool:
        position = pygame.Vector2(world)
        for player in self.players:
            for structure in player.structures:
                if not structure.alive:
                    continue
                distance = (structure.position - position).length()
                if distance < structure.radius + radius + 8:
                    return True
        return False

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
            if structure.alive:
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
                if not structure.alive:
                    continue
                if structure.tile_position() == tile:
                    return True
        return False

    def _unit_radius(self, definition: UnitDefinition) -> float:
        if definition.role in {"vehicle", "artillery"}:
            return config.TILE_SIZE * 0.65
        if definition.role == "infantry":
            return config.TILE_SIZE * 0.48
        return config.TILE_SIZE * 0.42

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        assert self.camera is not None
        surface.fill(config.COLORS["background"])
        self._draw_map(surface)
        self._draw_resources(surface)
        self._draw_structures(surface)
        self._draw_units(surface)
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

    def _draw_resources(self, surface: pygame.Surface) -> None:
        if not self.resource_nodes:
            return
        sprite = self._get_resource_surface()
        assert self.camera is not None
        for node in self.resource_nodes:
            position = self.camera.world_to_screen(node.position.x, node.position.y)
            rect = sprite.get_rect(center=(int(position.x), int(position.y)))
            surface.blit(sprite, rect)

    def _draw_structures(self, surface: pygame.Surface) -> None:
        assert self.camera is not None
        for player in self.players:
            for structure in player.structures:
                if not structure.alive:
                    continue
                sprite = self._get_structure_surface(player, structure.definition)
                rect = sprite.get_rect(center=self.camera.world_to_screen(structure.position.x, structure.position.y))
                if not structure.completed:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 120))
                    sprite = sprite.copy()
                    sprite.blit(overlay, (0, 0))
                surface.blit(sprite, rect)
                self._draw_health_bar(surface, rect.midtop, structure, width=rect.width)

    def _draw_units(self, surface: pygame.Surface) -> None:
        assert self.camera is not None
        for player in self.players:
            for unit in player.units:
                if not unit.alive:
                    continue
                sprite = self._get_unit_surface(player, unit.definition)
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
                f"{player.name}  Units: {len(player.units):02d}  Structures: {len(player.structures):02d}  "
                f"Resources: {int(player.resources)}  Tech: {player.tech_level}"
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

    def _get_unit_surface(self, player: PlayerState, definition: UnitDefinition) -> pygame.Surface:
        key = (player.id, definition.key)
        if key in self._unit_surfaces:
            return self._unit_surfaces[key]
        size = int(config.TILE_SIZE * (1.0 if definition.role == "infantry" else 1.2))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        body_color = pygame.Color(definition.primary_color)
        accent = pygame.Color(player.primary_color)
        accent.g = min(255, int((accent.g + definition.accent_color.g) / 2))
        accent.b = min(255, int((accent.b + definition.accent_color.b) / 2))
        accent.r = min(255, int((accent.r + definition.accent_color.r) / 2))
        pygame.draw.rect(surf, body_color, surf.get_rect(), border_radius=3)
        inner = surf.get_rect().inflate(-6, -6)
        if definition.role == "vehicle":
            pygame.draw.rect(surf, accent, inner, border_radius=4)
            turret = pygame.Rect(0, 0, inner.width // 2, inner.height // 2)
            turret.center = inner.center
            pygame.draw.rect(surf, player.shadow_color, turret, border_radius=3)
        elif definition.role == "artillery":
            pygame.draw.rect(surf, accent, inner, border_radius=5)
            barrel = pygame.Rect(0, 0, inner.width // 3, inner.height // 2)
            barrel.midleft = inner.midright
            pygame.draw.rect(surf, player.shadow_color, barrel, border_radius=2)
        elif definition.role == "worker":
            pygame.draw.rect(surf, accent, inner, border_radius=4)
            visor = pygame.Rect(0, 0, inner.width // 2, inner.height // 3)
            visor.center = (inner.centerx, inner.centery - 2)
            pygame.draw.rect(surf, player.shadow_color, visor, border_radius=2)
        else:
            pygame.draw.rect(surf, accent, inner, border_radius=3)
            stripe = pygame.Rect(0, 0, inner.width, inner.height // 3)
            stripe.center = inner.center
            pygame.draw.rect(surf, player.shadow_color, stripe, border_radius=2)
        self._unit_surfaces[key] = surf
        return surf

    def _get_structure_surface(self, player: PlayerState, definition: StructureDefinition) -> pygame.Surface:
        if definition.key in self._structure_surfaces:
            base_sprite = self._structure_surfaces[definition.key]
        else:
            size = int(definition.radius * 2.4)
            size = max(size, int(config.TILE_SIZE * 1.8))
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            body = pygame.Rect(0, size // 4, size, size - size // 4)
            roof = pygame.Rect(size // 8, 0, size - size // 4, size // 2)
            pygame.draw.rect(surf, definition.primary_color, body, border_radius=6)
            pygame.draw.rect(surf, definition.accent_color, roof, border_radius=6)
            door = pygame.Rect(0, 0, size // 3, size // 3)
            door.midbottom = body.midbottom
            pygame.draw.rect(surf, pygame.Color(32, 32, 38), door, border_radius=4)
            self._structure_surfaces[definition.key] = surf
            base_sprite = surf
        sprite = base_sprite.copy()
        tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        tint_color = (
            player.primary_color.r,
            player.primary_color.g,
            player.primary_color.b,
            80,
        )
        tint.fill(tint_color)
        sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return sprite

    def _get_resource_surface(self) -> pygame.Surface:
        if self._resource_surface is None:
            size = int(config.TILE_SIZE * 0.9)
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            base_color = pygame.Color(118, 181, 214)
            pygame.draw.polygon(
                surf,
                base_color,
                [
                    (size // 2, 2),
                    (size - 2, size // 3),
                    (size // 2 + 3, size - 2),
                    (2, size - 4),
                    (size // 3, size // 2),
                ],
            )
            highlight = pygame.Surface((size, size), pygame.SRCALPHA)
            highlight.fill((80, 120, 160, 90))
            surf.blit(highlight, (0, 0))
            self._resource_surface = surf
        return self._resource_surface


__all__ = ["RTSGame", "PlayerState"]

