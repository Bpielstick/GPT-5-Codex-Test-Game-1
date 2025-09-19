"""Entity definitions, blueprints, and runtime state for the RTS game."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import pygame

from . import config


@dataclass(frozen=True)
class UnitDefinition:
    """Immutable blueprint describing a unit archetype."""

    key: str
    name: str
    role: str  # worker, infantry, vehicle, artillery, scout
    max_health: float
    speed: float
    attack_damage: float
    attack_range: float
    attack_cooldown: float
    vision_radius: float
    cost: int
    build_time: float
    tech_level: int
    primary_color: pygame.Color
    accent_color: pygame.Color


@dataclass(frozen=True)
class StructureDefinition:
    """Immutable blueprint describing a structure archetype."""

    key: str
    name: str
    radius: float
    max_health: float
    cost: int
    build_time: float
    produces: Tuple[str, ...]
    required_tech: int
    provides_tech: int
    is_deposit: bool
    primary_color: pygame.Color
    accent_color: pygame.Color


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
    definition: StructureDefinition
    completed: bool = True
    construction_remaining: float = 0.0
    production_queue: List[UnitDefinition] = field(default_factory=list)
    production_timer: float = 0.0

    def tile_position(self) -> Tuple[int, int]:
        return (int(self.position.x // config.TILE_SIZE), int(self.position.y // config.TILE_SIZE))

    def enqueue_unit(self, definition: UnitDefinition) -> None:
        self.production_queue.append(definition)
        if len(self.production_queue) == 1:
            self.production_timer = definition.build_time

    def pop_completed_unit(self) -> Optional[UnitDefinition]:
        if not self.production_queue:
            return None
        unit_def = self.production_queue.pop(0)
        if self.production_queue:
            self.production_timer = self.production_queue[0].build_time
        else:
            self.production_timer = 0.0
        return unit_def


@dataclass
class Unit(Entity):
    definition: UnitDefinition
    attack_cooldown_remaining: float = 0.0
    path: List[Tuple[int, int]] = field(default_factory=list)
    _path_index: int = 0
    _goal_tile: Optional[Tuple[int, int]] = None
    worker_state: str = "idle"
    worker_target: Optional[int] = None
    worker_deposit: Optional[int] = None
    worker_cargo: float = 0.0
    worker_timer: float = 0.0

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
            direction.scale_to_length(min(self.definition.speed * dt, distance))
            self.position += direction

    def tick_cooldown(self, dt: float) -> None:
        if self.attack_cooldown_remaining > 0:
            self.attack_cooldown_remaining = max(0.0, self.attack_cooldown_remaining - dt)

    def can_attack(self) -> bool:
        return self.attack_cooldown_remaining <= 0.0 and self.definition.attack_damage > 0

    def attack(self, target: Entity) -> None:
        target.take_damage(self.definition.attack_damage)
        self.attack_cooldown_remaining = self.definition.attack_cooldown


@dataclass
class ResourceNode:
    id: int
    position: pygame.Vector2
    amount: float

    def tile_position(self) -> Tuple[int, int]:
        return (int(self.position.x // config.TILE_SIZE), int(self.position.y // config.TILE_SIZE))

    def harvest(self, requested: float) -> float:
        if self.amount <= 0:
            return 0.0
        gathered = min(self.amount, requested)
        self.amount -= gathered
        return gathered

    @property
    def depleted(self) -> bool:
        return self.amount <= 0


def build_palette() -> Dict[str, Tuple[pygame.Color, pygame.Color]]:
    """Generate a consistent palette for structure/unit silhouettes."""

    return {
        "worker": (pygame.Color(232, 214, 170), pygame.Color(187, 156, 109)),
        "infantry": (pygame.Color(205, 82, 80), pygame.Color(140, 40, 35)),
        "ranger": (pygame.Color(215, 170, 88), pygame.Color(163, 122, 52)),
        "tank": (pygame.Color(120, 148, 110), pygame.Color(65, 93, 72)),
        "artillery": (pygame.Color(138, 128, 180), pygame.Color(84, 78, 120)),
        "hq": (pygame.Color(122, 133, 148), pygame.Color(78, 86, 101)),
        "refinery": (pygame.Color(172, 132, 76), pygame.Color(101, 66, 28)),
        "barracks": (pygame.Color(124, 164, 130), pygame.Color(76, 110, 82)),
        "factory": (pygame.Color(158, 110, 116), pygame.Color(99, 64, 70)),
        "lab": (pygame.Color(116, 134, 178), pygame.Color(70, 82, 128)),
    }


PALETTE = build_palette()


UNIT_DEFS: Dict[str, UnitDefinition] = {
    "worker": UnitDefinition(
        key="worker",
        name="Engineer",
        role="worker",
        max_health=70,
        speed=85,
        attack_damage=2,
        attack_range=1.5 * config.TILE_SIZE,
        attack_cooldown=1.4,
        vision_radius=8 * config.TILE_SIZE,
        cost=60,
        build_time=2.0,
        tech_level=1,
        primary_color=PALETTE["worker"][0],
        accent_color=PALETTE["worker"][1],
    ),
    "infantry": UnitDefinition(
        key="infantry",
        name="Shock Trooper",
        role="infantry",
        max_health=110,
        speed=90,
        attack_damage=10,
        attack_range=2.8 * config.TILE_SIZE,
        attack_cooldown=0.9,
        vision_radius=9 * config.TILE_SIZE,
        cost=120,
        build_time=3.0,
        tech_level=1,
        primary_color=PALETTE["infantry"][0],
        accent_color=PALETTE["infantry"][1],
    ),
    "ranger": UnitDefinition(
        key="ranger",
        name="Ranger",
        role="infantry",
        max_health=90,
        speed=110,
        attack_damage=7,
        attack_range=4.0 * config.TILE_SIZE,
        attack_cooldown=0.6,
        vision_radius=11 * config.TILE_SIZE,
        cost=150,
        build_time=3.6,
        tech_level=2,
        primary_color=PALETTE["ranger"][0],
        accent_color=PALETTE["ranger"][1],
    ),
    "tank": UnitDefinition(
        key="tank",
        name="Vanguard Tank",
        role="vehicle",
        max_health=240,
        speed=70,
        attack_damage=24,
        attack_range=3.2 * config.TILE_SIZE,
        attack_cooldown=1.1,
        vision_radius=9 * config.TILE_SIZE,
        cost=240,
        build_time=5.5,
        tech_level=2,
        primary_color=PALETTE["tank"][0],
        accent_color=PALETTE["tank"][1],
    ),
    "artillery": UnitDefinition(
        key="artillery",
        name="Siege Artillery",
        role="artillery",
        max_health=180,
        speed=60,
        attack_damage=40,
        attack_range=5.0 * config.TILE_SIZE,
        attack_cooldown=2.4,
        vision_radius=12 * config.TILE_SIZE,
        cost=320,
        build_time=6.2,
        tech_level=3,
        primary_color=PALETTE["artillery"][0],
        accent_color=PALETTE["artillery"][1],
    ),
}


STRUCTURE_DEFS: Dict[str, StructureDefinition] = {
    "hq": StructureDefinition(
        key="hq",
        name="Command HQ",
        radius=1.6 * config.TILE_SIZE,
        max_health=900,
        cost=0,
        build_time=0.0,
        produces=("worker", "infantry"),
        required_tech=1,
        provides_tech=1,
        is_deposit=True,
        primary_color=PALETTE["hq"][0],
        accent_color=PALETTE["hq"][1],
    ),
    "refinery": StructureDefinition(
        key="refinery",
        name="Refinery",
        radius=1.4 * config.TILE_SIZE,
        max_health=650,
        cost=250,
        build_time=8.0,
        produces=(),
        required_tech=1,
        provides_tech=1,
        is_deposit=True,
        primary_color=PALETTE["refinery"][0],
        accent_color=PALETTE["refinery"][1],
    ),
    "barracks": StructureDefinition(
        key="barracks",
        name="Barracks",
        radius=1.3 * config.TILE_SIZE,
        max_health=520,
        cost=180,
        build_time=6.0,
        produces=("infantry", "ranger"),
        required_tech=1,
        provides_tech=2,
        is_deposit=False,
        primary_color=PALETTE["barracks"][0],
        accent_color=PALETTE["barracks"][1],
    ),
    "factory": StructureDefinition(
        key="factory",
        name="Armor Foundry",
        radius=1.5 * config.TILE_SIZE,
        max_health=700,
        cost=320,
        build_time=8.5,
        produces=("tank",),
        required_tech=2,
        provides_tech=2,
        is_deposit=False,
        primary_color=PALETTE["factory"][0],
        accent_color=PALETTE["factory"][1],
    ),
    "lab": StructureDefinition(
        key="lab",
        name="Research Lab",
        radius=1.2 * config.TILE_SIZE,
        max_health=480,
        cost=280,
        build_time=7.5,
        produces=("artillery",),
        required_tech=2,
        provides_tech=3,
        is_deposit=False,
        primary_color=PALETTE["lab"][0],
        accent_color=PALETTE["lab"][1],
    ),
}


def structures_providing_tech(structures: Iterable[Structure]) -> int:
    """Return the highest tech level provided by the given structures."""

    tech_level = 1
    for structure in structures:
        if structure.completed and structure.alive:
            tech_level = max(tech_level, structure.definition.provides_tech)
    return min(tech_level, config.MAX_TECH_LEVEL)


__all__ = [
    "Entity",
    "Structure",
    "Unit",
    "ResourceNode",
    "UnitDefinition",
    "StructureDefinition",
    "UNIT_DEFS",
    "STRUCTURE_DEFS",
    "structures_providing_tech",
]

