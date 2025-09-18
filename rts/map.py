"""Procedural map generation and navigation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import random
from typing import Iterator, List, Optional, Tuple

from . import config


class TileType(Enum):
    """Different kinds of terrain the map can contain."""

    WATER = 0
    GRASS = 1
    FOREST = 2
    MOUNTAIN = 3


@dataclass(frozen=True)
class Tile:
    """Represents a single tile in the world grid."""

    type: TileType
    elevation: float
    movement_cost: float

    @property
    def walkable(self) -> bool:
        return self.type in {TileType.GRASS, TileType.FOREST}


class GameMap:
    """The procedurally generated battlefield grid."""

    def __init__(self, width: int, height: int, rng: Optional[random.Random] = None):
        self.width = width
        self.height = height
        self.rng = rng or random.Random()
        self.tiles: List[List[Tile]] = []
        self._generate()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def _generate(self) -> None:
        base_noise = self._generate_height_field()
        tiles: List[List[Tile]] = []
        cx, cy = self.width / 2.0, self.height / 2.0
        max_dist = math.hypot(cx, cy)
        for y in range(self.height):
            row: List[Tile] = []
            for x in range(self.width):
                height_value = base_noise[y][x]
                # Encourage land near the centre for better battlegrounds.
                dist = math.hypot(x - cx, y - cy) / max_dist
                height_value -= dist * 0.35
                height_value = max(0.0, min(1.0, height_value))
                tile = self._classify_tile(height_value)
                row.append(tile)
            tiles.append(row)
        self.tiles = tiles

    def _generate_height_field(self) -> List[List[float]]:
        width, height = self.width, self.height
        values = [[self.rng.random() for _ in range(width)] for _ in range(height)]
        # Multiple smoothing passes to create continents and patches.
        passes = int(max(width, height) / 16)
        for _ in range(max(4, passes)):
            values = self._smooth(values)
            values = self._add_perturbation(values, amplitude=0.08)
        return values

    def _smooth(self, values: List[List[float]]) -> List[List[float]]:
        width, height = self.width, self.height
        smoothed = [[0.0 for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                total = 0.0
                count = 0
                for ny in range(max(0, y - 1), min(height, y + 2)):
                    for nx in range(max(0, x - 1), min(width, x + 2)):
                        total += values[ny][nx]
                        count += 1
                smoothed[y][x] = total / count
        return smoothed

    def _add_perturbation(self, values: List[List[float]], amplitude: float) -> List[List[float]]:
        width, height = self.width, self.height
        perturbed = [[0.0 for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                offset = (self.rng.random() - 0.5) * 2 * amplitude
                perturbed[y][x] = max(0.0, min(1.0, values[y][x] + offset))
        return perturbed

    def _classify_tile(self, value: float) -> Tile:
        if value < 0.26:
            return Tile(TileType.WATER, value, movement_cost=10.0)
        if value < 0.55:
            return Tile(TileType.GRASS, value, movement_cost=1.0)
        if value < 0.78:
            return Tile(TileType.FOREST, value, movement_cost=1.7)
        return Tile(TileType.MOUNTAIN, value, movement_cost=12.0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def in_bounds(self, tile_pos: Tuple[int, int]) -> bool:
        x, y = tile_pos
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, tile_pos: Tuple[int, int]) -> Tile:
        x, y = tile_pos
        return self.tiles[y][x]

    def is_walkable(self, tile_pos: Tuple[int, int]) -> bool:
        return self.in_bounds(tile_pos) and self.get_tile(tile_pos).walkable

    def movement_cost(self, tile_pos: Tuple[int, int]) -> float:
        tile = self.get_tile(tile_pos)
        return tile.movement_cost

    def neighbors(self, tile_pos: Tuple[int, int]) -> Iterator[Tuple[int, int]]:
        x, y = tile_pos
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.in_bounds((nx, ny)) and self.is_walkable((nx, ny)):
                yield (nx, ny)

    def random_walkable_tile(self, margin: int = 4) -> Tuple[int, int]:
        """Return a random walkable tile away from the borders."""

        for _ in range(5000):
            x = self.rng.randint(margin, self.width - margin - 1)
            y = self.rng.randint(margin, self.height - margin - 1)
            if self.is_walkable((x, y)):
                return (x, y)
        # Fallback to sequential search if random selection fails
        for y in range(margin, self.height - margin):
            for x in range(margin, self.width - margin):
                if self.is_walkable((x, y)):
                    return (x, y)
        raise RuntimeError("Could not find a walkable tile on the map")

    def force_clear_area(self, center: Tuple[int, int], radius: int) -> None:
        """Force a circular area around ``center`` to be grass for safe spawning."""

        cx, cy = center
        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                if math.hypot(x - cx, y - cy) <= radius:
                    tile = Tile(TileType.GRASS, elevation=0.5, movement_cost=1.0)
                    self.tiles[y][x] = tile

    def to_world(self, tile_pos: Tuple[int, int]) -> Tuple[float, float]:
        x, y = tile_pos
        return (
            x * config.TILE_SIZE + config.TILE_SIZE / 2,
            y * config.TILE_SIZE + config.TILE_SIZE / 2,
        )

    def clamp_to_map(self, px: float, py: float) -> Tuple[float, float]:
        max_x = self.width * config.TILE_SIZE
        max_y = self.height * config.TILE_SIZE
        return max(0.0, min(px, max_x - 1)), max(0.0, min(py, max_y - 1))


__all__ = ["Tile", "TileType", "GameMap"]
