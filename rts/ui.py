"""UI widgets for controlling the observer interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

import pygame

from . import config


ButtonCallback = Callable[[], None]


@dataclass
class UIButton:
    label: str
    rect: pygame.Rect
    callback: ButtonCallback
    is_hovered: bool = False
    is_pressed: bool = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if self.is_pressed:
            color = config.COLORS["button_pressed"]
        elif self.is_hovered:
            color = config.COLORS["button_hover"]
        else:
            color = config.COLORS["button_idle"]

        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, config.COLORS["ui_panel_border"], self.rect, width=2, border_radius=6)
        text_surface = font.render(self.label, True, config.COLORS["text"])
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


@dataclass
class UIManager:
    buttons: List[UIButton] = field(default_factory=list)

    def add_button(self, label: str, position: tuple[int, int], callback: ButtonCallback) -> UIButton:
        rect = pygame.Rect(position, config.BUTTON_SIZE)
        button = UIButton(label=label, rect=rect, callback=callback)
        self.buttons.append(button)
        return button

    def handle_event(self, event: pygame.event.Event) -> bool:
        handled = False
        for button in self.buttons:
            if button.handle_event(event):
                handled = True
        return handled

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for button in self.buttons:
            button.draw(surface, font)


__all__ = ["UIButton", "UIManager"]
