"""Autonomous commander logic for running RTS matches."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from . import config
from .entities import STRUCTURE_DEFS, UNIT_DEFS

if TYPE_CHECKING:  # pragma: no cover - only used for type hints
    from .game import PlayerState, RTSGame
    from .entities import Structure


@dataclass
class AIController:
    name: str
    aggression: float = 1.0
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self._retarget_timer = 0.0
        self._build_timer = 0.0
        self._train_timer = 0.0
        self._combat_pointer = 0
        self._structure_targets: List[tuple[str, int]] = [
            ("refinery", 1),
            ("barracks", 1),
            ("refinery", 2),
            ("factory", 1),
            ("barracks", 2),
            ("lab", 1),
        ]
        self._combat_cycle = ["infantry", "infantry", "ranger", "tank", "infantry", "artillery"]

    def update(self, dt: float, game: "RTSGame", player: "PlayerState") -> None:
        if player.defeated:
            return

        self._build_timer -= dt
        self._train_timer -= dt
        self._retarget_timer -= dt

        if self._build_timer <= 0.0:
            self._build_timer = self.rng.uniform(4.0, 6.5)
            self._attempt_construction(game, player)

        if self._train_timer <= 0.0:
            self._train_timer = self.rng.uniform(1.8, 2.6)
            self._attempt_training(game, player)

        if self._retarget_timer <= 0.0:
            self._retarget_timer = self.rng.uniform(*config.BATTLE_RETARGET_TIME) / max(0.5, self.aggression)
            target = game.choose_attack_target(player)
            if target is not None:
                for unit in player.units:
                    if unit.definition.role != "worker" and unit.alive:
                        game.order_unit_to_tile(unit, target)

    # ------------------------------------------------------------------
    # Construction and production helpers
    # ------------------------------------------------------------------
    def _attempt_construction(self, game: "RTSGame", player: "PlayerState") -> None:
        for structure_key, desired_count in self._structure_targets:
            current = player.count_structures(structure_key)
            if current >= desired_count:
                continue
            definition = STRUCTURE_DEFS.get(structure_key)
            if definition is None:
                continue
            if player.tech_level < definition.required_tech:
                continue
            if player.resources < definition.cost:
                continue
            result = game.start_structure_construction(player, structure_key)
            if result is not None:
                return

    def _attempt_training(self, game: "RTSGame", player: "PlayerState") -> None:
        worker_goal = 8
        worker_count = sum(1 for unit in player.units if unit.definition.role == "worker")
        if worker_count < worker_goal:
            self._queue_unit(game, player, "worker")
            return

        combat_unit = self._choose_combat_unit(player)
        if combat_unit is None:
            return
        self._queue_unit(game, player, combat_unit)

    def _queue_unit(self, game: "RTSGame", player: "PlayerState", unit_key: str) -> None:
        producers = player.available_producers(unit_key)
        if not producers:
            return
        producers.sort(key=lambda structure: len(structure.production_queue))
        for structure in producers:
            if len(structure.production_queue) >= 3:
                continue
            if game.queue_unit_production(player, structure, unit_key):
                return

    def _choose_combat_unit(self, player: "PlayerState") -> Optional[str]:
        for _ in range(len(self._combat_cycle)):
            unit_key = self._combat_cycle[self._combat_pointer % len(self._combat_cycle)]
            self._combat_pointer += 1
            definition = UNIT_DEFS.get(unit_key)
            if definition is None:
                continue
            if player.tech_level < definition.tech_level:
                continue
            if not player.available_producers(unit_key):
                continue
            if player.resources < definition.cost:
                continue
            return unit_key
        return None


__all__ = ["AIController"]

