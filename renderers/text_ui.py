"""Plain-text, turn-based renderer: ``python3 main.py --renderer text``.

This renderer never uses curses, so it works over ssh, inside pipelines and in
editor terminals that cannot allocate a screen.  The trade-off is that the game
is turn-based: every line you type moves the snake one cell, which also makes it
handy for scripted smoke tests.
"""
from __future__ import annotations

import sys

from typing import TextIO

from game_logic import Direction, GameStatus, SnakeGame
from renderers import GameOutcome
from scores import load_high_score
from settings import BODY_CHAR, FOOD_CHAR, HEAD_CHAR

TURNS: dict[str, Direction] = {
    "w": Direction.UP,
    "k": Direction.UP,
    "a": Direction.LEFT,
    "h": Direction.LEFT,
    "s": Direction.DOWN,
    "j": Direction.DOWN,
    "d": Direction.RIGHT,
    "l": Direction.RIGHT,
}
QUIT_CHARS = frozenset({"q", "!", "quit", "exit"})
REPLAY_CHARS = frozenset({"r", "again", "enter", "y"})
HELP_CHARS = frozenset({"?", "help"})

CONTROLS_LINE = "one command per line: wasd/hjkl turn, anything else just moves, q quit, ? help"


def board_text(game: SnakeGame) -> str:
    """ASCII picture of the board, ready to be printed as-is."""
    body = game.occupied()
    head = game.head
    food = game.food
    rows = []
    for y in range(game.height):
        cells = []
        for x in range(game.width):
            cell = (x, y)
            if cell == food:
                cells.append(FOOD_CHAR)
            elif cell == head:
                cells.append(HEAD_CHAR)
            elif cell in body:
                cells.append(BODY_CHAR)
            else:
                cells.append(" ")
        rows.append("".join(cells))
    border = "+" + "-" * game.width + "+"
    return "\n".join([border, *rows, border])


def _status_line(game: SnakeGame) -> str:
    return (
        f"score {game.score:<5d} best {load_high_score():<5d} "
        f"length {len(game.body):<3d} status {game.status.value}"
    )


def _read_command(stream: TextIO) -> str | None:
    """Next non-empty command word from ``stream`` (None when input ends)."""
    while True:
        line = stream.readline()
        if not line:
            return None
        word = line.strip().lower()
        if word:
            return word


def play(game: SnakeGame, *, stream: TextIO = sys.stdin) -> GameOutcome:
    """Play a round reading commands from ``stream`` (stdin by default)."""
    print(CONTROLS_LINE)
    print(_status_line(game))
    while True:
        command = _read_command(stream)
        if command is None or command in QUIT_CHARS:
            print(board_text(game))
            print(_status_line(game))
            return GameOutcome(game.score, game.status, False)
        if command in HELP_CHARS:
            print(CONTROLS_LINE)
            continue
        if command in TURNS:
            game.request_turn(TURNS[command])
        game.advance()
        print(board_text(game))
        print(_status_line(game))
        if game.is_over():
            break
    return _await_replay(stream, game)


def _await_replay(stream: TextIO, game: SnakeGame) -> GameOutcome:
    """Ask for another round without touching curses."""
    print("type 'r' to replay - anything else quits")
    command = _read_command(stream)
    replay = command is not None and command in REPLAY_CHARS
    return GameOutcome(game.score, game.status, replay)