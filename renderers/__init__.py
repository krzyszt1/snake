"""Renderers turn the pure game state into something you can see and play.

Each renderer owns its input handling and drawing, and reports the same small
result back to ``main.py`` through :class:`GameOutcome`.
"""
from __future__ import annotations

from typing import NamedTuple

from game_logic import GameStatus


class GameOutcome(NamedTuple):
    """What a renderer tells ``main.py`` when a round finishes."""

    score: int
    status: GameStatus
    replay: bool


__all__ = ["GameOutcome"]