"""The rules of Snake, with no rendering and no input handling.

A round of the game is completely described by :class:`SnakeGame`: the snake
body (head first), the food, the score and the status.  Because this module
never touches a terminal or a GUI it can be unit tested and played headless,
which is exactly what ``tests/`` and ``main.py --simulate`` rely on.

Typical use from a renderer::

    game = SnakeGame(width=30, height=15)
    while not game.is_over():
        game.request_turn(Direction.UP)  # queue a heading change
        game.advance()                   # move the snake one cell
"""
from __future__ import annotations

import random
from collections import deque
from enum import Enum

from settings import (
    BASE_SPEED,
    BOARD_HEIGHT,
    BOARD_WIDTH,
    MAX_SPEED,
    MIN_BOARD_HEIGHT,
    MIN_BOARD_WIDTH,
    POINTS_PER_FOOD,
    SPEED_PER_FOOD,
    START_LENGTH,
)

Point = tuple[int, int]


class Direction(Enum):
    """The four headings the snake may travel in (y grows downwards)."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


OPPOSITE_DIRECTION = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


class GameStatus(Enum):
    """State of a round: still running, crashed into itself, or board filled."""

    PLAYING = "playing"
    GAME_OVER = "game over"
    WON = "board filled"


class SnakeGame:
    """State of one round: snake body, food, score, status.

    The body is a deque with the head at the left end, so a step is a pair of
    cheap append/pop operations.  ``request_turn`` only queues a heading change
    (refusing reversals), and ``advance`` is the single step a renderer calls
    once per frame.
    """

    def __init__(
        self,
        *,
        width: int = BOARD_WIDTH,
        height: int = BOARD_HEIGHT,
        start_length: int = START_LENGTH,
        wrap: bool = False,
        rng_seed: int | None = None,
    ) -> None:
        if width < MIN_BOARD_WIDTH or height < MIN_BOARD_HEIGHT:
            msg = f"board must be at least {MIN_BOARD_WIDTH}x{MIN_BOARD_HEIGHT}"
            raise ValueError(msg)
        if start_length < 1 or start_length > width // 2 + 1:
            msg = f"start length must be between 1 and {width // 2 + 1}"
            raise ValueError(msg)
        self.width = width
        self.height = height
        self.wrap = wrap
        self.start_length = start_length
        self.rng = random.Random(rng_seed)
        self._reset()

    def _reset(self) -> None:
        """Place a brand new round on the board."""
        head_x, head_y = self.width // 2, self.height // 2
        self.body = deque((head_x - offset, head_y) for offset in range(self.start_length))
        self.direction = Direction.RIGHT
        self.queued_turns: deque[Direction] = deque()
        self.score = 0
        self.food_eaten = 0
        self.status = GameStatus.PLAYING
        self.food: Point | None = None
        self._spawn_food()

    def restart(self) -> None:
        """Start a fresh round on the same board (keeps drawing new food)."""
        self._reset()

    # -- state queries ---------------------------------------------------------
    @property
    def head(self) -> Point:
        return self.body[0]

    def is_walkable(self, cell: Point) -> bool:
        """Is ``cell`` somewhere on the board?"""
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def occupied(self) -> set[Point]:
        """Every cell the snake currently covers."""
        return set(self.body)

    def cells(self) -> list[Point]:
        return [(x, y) for y in range(self.height) for x in range(self.width)]

    def free_cells(self) -> list[Point]:
        taken = self.occupied()
        return [cell for cell in self.cells() if cell not in taken]

    def current_speed(self) -> float:
        """Steps per second the snake moves at (grows with every food)."""
        return min(MAX_SPEED, BASE_SPEED + self.food_eaten * SPEED_PER_FOOD)

    def is_over(self) -> bool:
        return self.status is not GameStatus.PLAYING

    # -- input -----------------------------------------------------------------
    def request_turn(self, direction: Direction) -> bool:
        """Queue a heading change; refuse reversals, repeats and over-buffering.

        Returning False lets the caller ignore a key press instead of letting
        the snake fold back on itself, which is the classic snake bug.
        """
        if self.status is not GameStatus.PLAYING:
            return False
        if not isinstance(direction, Direction):
            msg = f"direction must be a Direction member, got {direction!r}"
            raise TypeError(msg)
        last = self.queued_turns[-1] if self.queued_turns else self.direction
        if direction is last or direction is OPPOSITE_DIRECTION[last]:
            return False
        if len(self.queued_turns) >= 2:
            return False
        self.queued_turns.append(direction)
        return True

    # -- the one step that matters ---------------------------------------------
    def advance(self) -> bool:
        """Move the snake one cell; return whether the round keeps going."""
        if self.status is not GameStatus.PLAYING:
            return False
        if self.queued_turns:
            self.direction = self.queued_turns.popleft()
        head_x, head_y = self.body[0]
        delta_x, delta_y = self.direction.value
        new_head = (head_x + delta_x, head_y + delta_y)
        if self.wrap:
            new_head = (new_head[0] % self.width, new_head[1] % self.height)
        elif not self.is_walkable(new_head):
            self.status = GameStatus.GAME_OVER
            return False

        if new_head == self.food:
            self._grow_at(new_head)
            return True

        # The tail cell is vacated by this very step, so moving into it is legal.
        blocking = self.occupied()
        blocking.discard(self.body[-1])
        if new_head in blocking:
            self.status = GameStatus.GAME_OVER
            return False
        self.body.appendleft(new_head)
        self.body.pop()
        return True

    def _grow_at(self, new_head: Point) -> None:
        """Eat the food: grow, score, then put the next food down."""
        self.body.appendleft(new_head)
        self.score += POINTS_PER_FOOD
        self.food_eaten += 1
        self._spawn_food()

    def _spawn_food(self) -> None:
        """Put food on a random free cell, or declare the board filled."""
        free = self.free_cells()
        if not free:
            self.status = GameStatus.WON
            self.food = None
            return
        self.food = self.rng.choice(free)


__all__ = ["Direction", "GameStatus", "OPPOSITE_DIRECTION", "Point", "SnakeGame"]