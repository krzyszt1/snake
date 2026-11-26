"""Terminal renderer - the default way to play Snake (``python3 main.py``).

Only the standard library ``curses`` front-end is used, so there is nothing to
install.  It needs a real terminal; over ssh or inside an editor output panel,
use ``main.py --renderer text`` instead, which never touches curses.
"""
from __future__ import annotations

import time

import curses

from game_logic import Direction, GameStatus, SnakeGame
from renderers import GameOutcome
from scores import load_high_score
from settings import BODY_CHAR, FOOD_CHAR, HEAD_CHAR

CONTROLS_LINE = "arrows/wasd/hjkl move | p pause | q quit | enter replay"

TURN_KEYS: dict[int, Direction] = {
    curses.KEY_UP: Direction.UP,
    ord("k"): Direction.UP,
    ord("w"): Direction.UP,
    curses.KEY_DOWN: Direction.DOWN,
    ord("j"): Direction.DOWN,
    ord("s"): Direction.DOWN,
    curses.KEY_LEFT: Direction.LEFT,
    ord("h"): Direction.LEFT,
    ord("a"): Direction.LEFT,
    curses.KEY_RIGHT: Direction.RIGHT,
    ord("l"): Direction.RIGHT,
    ord("d"): Direction.RIGHT,
}
QUIT_KEYS = frozenset({ord("q"), ord("Q")})
PAUSE_KEYS = frozenset({ord("p"), ord("P")})
REPLAY_KEYS = frozenset({curses.KEY_ENTER, 10, 13, ord("r"), ord("R")})

# Colour pairs are filled in once curses knows the terminal.  Terminals without
# colour support simply keep every attribute at 0, which means plain text.
COLOUR_FOREGROUND = {"snake": curses.COLOR_GREEN, "food": curses.COLOR_RED}
COLOUR_PAIRS: dict[str, int] = {}


def _colour_attribute(pair: int) -> int:
    """Attribute flag for a colour pair, whatever this curses version offers."""
    if pair == 0:
        return 0
    for lookup_name in ("newpyattr", "colorbar", "color_pair"):
        lookup = getattr(curses, lookup_name, None)
        if lookup is None:
            continue
        try:
            return int(lookup(pair))
        except (curses.error, TypeError, ValueError):
            continue
    return 0


def _initialise_colours() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    for index, name in enumerate(COLOUR_FOREGROUND, start=1):
        try:
            curses.init_pair(index, COLOUR_FOREGROUND[name], -1)
        except curses.error:
            continue
        COLOUR_PAIRS[name] = index


def play(game: SnakeGame) -> GameOutcome:
    """Play one round in the terminal and report the outcome to ``main.py``.

    Raises :exc:`curses.error` when no terminal can be allocated; main.py turns
    that into a hint about ``--renderer text``.
    """
    return curses.wrapper(_play_round, game)


def _play_round(stdscr, game: SnakeGame) -> GameOutcome:
    """Frame loop: draw, soak up key presses for one frame, then step once."""
    _initialise_colours()
    paused = False
    while True:
        _draw_board(stdscr, game, paused=paused)
        if game.is_over():
            break
        if paused:
            key, alive = _blocking_key(stdscr)
            if not alive or key in QUIT_KEYS:
                return GameOutcome(game.score, game.status, False)
            if key in PAUSE_KEYS:
                paused = False
            elif key in TURN_KEYS:
                game.request_turn(TURN_KEYS[key])
            continue
        frame_deadline = time.monotonic() + 1.0 / game.current_speed()
        while time.monotonic() < frame_deadline:
            stdscr.timeout(max(1, int((frame_deadline - time.monotonic()) * 1000)))
            key = stdscr.getch()
            if key == -1:
                continue
            if key in QUIT_KEYS:
                return GameOutcome(game.score, game.status, False)
            if key in PAUSE_KEYS:
                paused = True
                break
            if key in TURN_KEYS:
                game.request_turn(TURN_KEYS[key])
        game.advance()
    _draw_endgame(stdscr, game)
    return _await_replay(stdscr, game)


def _blocking_key(stdscr) -> tuple[int, bool]:
    """Wait until a key arrives; ``False`` means stdin will not answer again."""
    stdscr.timeout(-1)
    key = stdscr.getch()
    if key == -1:  # piped or exhausted stdin: treat it as "no more input"
        return -1, False
    return key, True


def _await_replay(stdscr, game: SnakeGame) -> GameOutcome:
    """Hold the finished round on screen until the player chooses."""
    while True:
        key, alive = _blocking_key(stdscr)
        if not alive or key in QUIT_KEYS:
            return GameOutcome(game.score, game.status, False)
        if key in REPLAY_KEYS:
            return GameOutcome(game.score, game.status, True)


def _layout(game: SnakeGame) -> tuple[int, int, int, int]:
    """Top-left corner plus size of the playfield, centred on the screen."""
    origin_x = max(1, (curses.COLS - game.width - 2) // 2)
    origin_y = max(1, (curses.LINES - game.height - 2) // 2)
    return origin_x, origin_y, game.width, game.height


def _room(origin_x: int) -> int:
    """How many characters fit to the right of ``origin_x`` on this screen."""
    if not curses.COLS:
        return 80
    return max(0, curses.COLS - origin_x - 1)


def _controls_text(room: int) -> str:
    """Longest control hint that still fits the screen."""
    for hint in (CONTROLS_LINE, "p pause  q quit", "q quit", ""):
        if len(hint) <= room:
            return hint
    return ""


def _status_text(game: SnakeGame, *, paused: bool, room: int) -> str:
    """Longest status line that still fits the screen."""
    best = load_high_score()
    if paused:
        options = (
            f"[paused] score {game.score} best {best} speed {game.current_speed():.0f} f/s",
            f"[paused] score {game.score} best {best}",
            "[paused]",
            "",
        )
    else:
        options = (
            f"score {game.score:<5d} best {best:<5d} speed {game.current_speed():.0f} f/s",
            f"score {game.score} best {best}",
            f"score {game.score}",
            "",
        )
    for option in options:
        if len(option) <= room:
            return option
    return options[-1]


def _putstr(stdscr, y: int, x: int, text: str, attr: int = 0) -> None:
    """Draw text, quietly dropping writes that fall outside the screen."""
    if y < 0 or x < 0:
        return
    if curses.COLS and x >= curses.COLS - 1:  # nothing to write on that column
        return
    if curses.COLS:  # keep text inside the screen so it does not wrap
        text = text[: curses.COLS - x - 1]
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _putch(stdscr, y: int, x: int, char: str, attr: int = 0) -> None:
    if y < 0 or x < 0:
        return
    try:
        stdscr.addch(y, x, char, attr)
    except curses.error:
        pass


def _draw_board(stdscr, game: SnakeGame, *, paused: bool = False) -> None:
    """Redraw the whole screen: border, snake, food and the status line."""
    stdscr.erase()
    origin_x, origin_y, width, height = _layout(game)
    room = _room(origin_x)
    _putstr(stdscr, 0, origin_x, _controls_text(room))
    _putstr(stdscr, origin_y - 1, origin_x, _status_text(game, paused=paused, room=room))
    border = "+" + "-" * width + "+"
    _putstr(stdscr, origin_y, origin_x, border)
    _putstr(stdscr, origin_y + height + 1, origin_x, border)
    body = game.occupied()
    head = game.head
    food = game.food
    snake_attr = _colour_attribute(COLOUR_PAIRS.get("snake", 0))
    food_attr = _colour_attribute(COLOUR_PAIRS.get("food", 0))
    for y in range(height):
        for x in range(width):
            cell = (x, y)
            if cell == food:
                _putch(stdscr, origin_y + 1 + y, origin_x + 1 + x, FOOD_CHAR, food_attr)
            elif cell == head:
                _putch(stdscr, origin_y + 1 + y, origin_x + 1 + x, HEAD_CHAR, snake_attr)
            elif cell in body:
                _putch(stdscr, origin_y + 1 + y, origin_x + 1 + x, BODY_CHAR, snake_attr)
    stdscr.refresh()


def _draw_endgame(stdscr, game: SnakeGame) -> None:
    """Write the one-line verdict under the finished board."""
    origin_x, origin_y, _, height = _layout(game)
    if game.status is GameStatus.GAME_OVER:
        message = f"game over - score {game.score}"
    else:
        message = f"you filled the board - score {game.score}"
    _putstr(stdscr, origin_y + height + 2, origin_x, f"{message}   (enter replays, q quits)")
    stdscr.refresh()