"""Utility helpers for the RTS game."""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from .map import GameMap

TilePos = Tuple[int, int]


def heuristic(a: TilePos, b: TilePos) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from: Dict[TilePos, TilePos], current: TilePos) -> List[TilePos]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def a_star(game_map: GameMap, start: TilePos, goal: TilePos, max_iterations: int = 6000) -> Optional[List[TilePos]]:
    """A* pathfinding on the map grid."""

    if start == goal:
        return [start]

    open_set: List[Tuple[float, TilePos]] = []
    heapq.heappush(open_set, (0.0, start))

    came_from: Dict[TilePos, TilePos] = {}
    g_score: Dict[TilePos, float] = {start: 0.0}
    f_score: Dict[TilePos, float] = {start: heuristic(start, goal)}

    visited = 0
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            return reconstruct_path(came_from, current)

        visited += 1
        if visited > max_iterations:
            break

        for neighbor in game_map.neighbors(current):
            tentative_g = g_score[current] + 0.5 * (
                game_map.movement_cost(neighbor) + game_map.movement_cost(current)
            )
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                score = tentative_g + heuristic(neighbor, goal)
                f_score[neighbor] = score
                heapq.heappush(open_set, (score, neighbor))

    return None


__all__ = ["TilePos", "a_star"]
