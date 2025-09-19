"""Global configuration values for the RTS game."""

from __future__ import annotations

import pygame

# Screen / camera configuration
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FRAME_RATE = 60

# Map configuration
TILE_SIZE = 16
MAP_WIDTH = 128
MAP_HEIGHT = 128

# Gameplay configuration
INITIAL_RESOURCES = 600
RESOURCE_TICK_INTERVAL = 1.0  # seconds
MAX_UNITS = 140
MAX_STRUCTURES = 24
MAX_TECH_LEVEL = 3

# Economy configuration
RESOURCE_NODE_COUNT = 26
RESOURCE_NODE_MIN_DISTANCE = 8
RESOURCE_NODE_AMOUNT_RANGE = (450, 900)
WORKER_CAPACITY = 120
WORKER_GATHER_TIME = 2.2
WORKER_DEPOSIT_TIME = 1.0

# Combat pacing
BATTLE_RETARGET_TIME = (3.0, 5.5)
SCOUT_RETARGET_TIME = (6.0, 9.0)

# Camera configuration
CAMERA_SCROLL_SPEED = 400  # pixels per second

# UI configuration
UI_BAR_HEIGHT = 70
UI_FONT_NAME = "freesansbold.ttf"
BUTTON_SIZE = (140, 36)
BUTTON_PADDING = 10

# Colour palette inspired by classic pixel art RTS games
COLORS = {
    "background": pygame.Color(8, 24, 32),
    "grass": pygame.Color(54, 99, 45),
    "forest": pygame.Color(28, 66, 38),
    "mountain": pygame.Color(92, 80, 68),
    "water": pygame.Color(14, 41, 75),
    "grid_shadow": pygame.Color(0, 0, 0, 80),
    "ui_panel": pygame.Color(20, 30, 42),
    "ui_panel_border": pygame.Color(86, 115, 145),
    "text": pygame.Color(212, 227, 241),
    "button_idle": pygame.Color(52, 89, 132),
    "button_hover": pygame.Color(74, 118, 168),
    "button_pressed": pygame.Color(20, 54, 92),
    "health_back": pygame.Color(70, 20, 20),
    "health_front": pygame.Color(209, 58, 65),
}

PLAYER_COLORS = [
    (pygame.Color(214, 69, 65), pygame.Color(178, 34, 34)),
    (pygame.Color(66, 135, 245), pygame.Color(21, 101, 192)),
]

__all__ = [
    "SCREEN_WIDTH",
    "SCREEN_HEIGHT",
    "FRAME_RATE",
    "TILE_SIZE",
    "MAP_WIDTH",
    "MAP_HEIGHT",
    "INITIAL_RESOURCES",
    "RESOURCE_TICK_INTERVAL",
    "MAX_UNITS",
    "MAX_STRUCTURES",
    "MAX_TECH_LEVEL",
    "RESOURCE_NODE_COUNT",
    "RESOURCE_NODE_MIN_DISTANCE",
    "RESOURCE_NODE_AMOUNT_RANGE",
    "WORKER_CAPACITY",
    "WORKER_GATHER_TIME",
    "WORKER_DEPOSIT_TIME",
    "BATTLE_RETARGET_TIME",
    "SCOUT_RETARGET_TIME",
    "CAMERA_SCROLL_SPEED",
    "UI_BAR_HEIGHT",
    "UI_FONT_NAME",
    "BUTTON_SIZE",
    "BUTTON_PADDING",
    "COLORS",
    "PLAYER_COLORS",
]
