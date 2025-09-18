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
INITIAL_RESOURCES = 250
RESOURCE_INCOME_PER_SECOND = 30
UNIT_COST = 75
UNIT_BUILD_TIME = 3.0  # seconds
MAX_UNITS = 80

# Unit parameters
UNIT_SPEED = 90  # pixels per second
UNIT_VISION_RADIUS = 9 * TILE_SIZE
UNIT_ATTACK_RANGE = 2.5 * TILE_SIZE
UNIT_ATTACK_DAMAGE = 8
UNIT_ATTACK_COOLDOWN = 0.8
UNIT_MAX_HEALTH = 60

# Structure parameters
BASE_MAX_HEALTH = 800

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
    "RESOURCE_INCOME_PER_SECOND",
    "UNIT_COST",
    "UNIT_BUILD_TIME",
    "MAX_UNITS",
    "UNIT_SPEED",
    "UNIT_VISION_RADIUS",
    "UNIT_ATTACK_RANGE",
    "UNIT_ATTACK_DAMAGE",
    "UNIT_ATTACK_COOLDOWN",
    "UNIT_MAX_HEALTH",
    "BASE_MAX_HEALTH",
    "CAMERA_SCROLL_SPEED",
    "UI_BAR_HEIGHT",
    "UI_FONT_NAME",
    "BUTTON_SIZE",
    "BUTTON_PADDING",
    "COLORS",
    "PLAYER_COLORS",
]
