"""Simple AI logic that manages base production and attack orders."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:  # pragma: no cover - only used for type hints
    from .game import PlayerState, RTSGame


@dataclass
class AIController:
    name: str
    aggression: float = 1.0
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self._retarget_timer = 0.0

    def update(self, dt: float, game: "RTSGame", player: "PlayerState") -> None:
        if player.defeated:
            return

        # Economic management
        player.resources += config.RESOURCE_INCOME_PER_SECOND * dt

        if player.production_timer > 0.0:
            player.production_timer = max(0.0, player.production_timer - dt)
            if player.production_timer == 0.0 and player.pending_unit_ready:
                spawn_tile = game.find_spawn_tile(player)
                if spawn_tile is not None:
                    game.spawn_unit(player, spawn_tile)
                player.pending_unit_ready = False
        else:
            can_afford = player.resources >= config.UNIT_COST
            below_cap = len(player.units) < config.MAX_UNITS
            if can_afford and below_cap:
                player.resources -= config.UNIT_COST
                player.production_timer = config.UNIT_BUILD_TIME
                player.pending_unit_ready = True

        # Retarget periodically to adapt to enemy locations
        self._retarget_timer -= dt
        if self._retarget_timer <= 0.0:
            self._retarget_timer = self.rng.uniform(3.0, 5.5) / max(0.5, self.aggression)
            target = game.choose_attack_target(player)
            if target is not None:
                for unit in player.units:
                    if unit.alive:
                        game.order_unit_to_tile(unit, target)


__all__ = ["AIController"]
