"""Autonomous Snake player, used for headless smoke tests (``main.py --simulate``).

The strategy is deliberately simple and readable rather than unbeatable: try
every non-reversing heading, keep the ones that land on a free cell, prefer the
ones that leave the snake able to reach its own tail (so it never seals itself
into a dead end), and among those pick the one whose head ends closest to the
food.  Going straight wins ties, which is what makes the snake slalom instead of
jittering.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable

from game_logic import Direction, GameStatus, OPPOSITE_DIRECTION, Point, SnakeGame

DIRECTIONS = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)


def _next_cell(game: SnakeGame, cell: Point, direction: Direction) -> Point | None:
    """Cell reached from ``cell``; None when the step leaves the board."""
    x, y = cell
    delta_x, delta_y = direction.value
    x += delta_x
    y += delta_y
    if game.wrap:
        x %= game.width
        y %= game.height
    if not game.is_walkable((x, y)):
        return None
    return (x, y)


def _distance(game: SnakeGame, first: Point, second: Point) -> int:
    x_one, y_one = first
    x_two, y_two = second
    dx = abs(x_one - x_two)
    dy = abs(y_one - y_two)
    if game.wrap:
        dx = min(dx, game.width - dx)
        dy = min(dy, game.height - dy)
    return dx + dy


def _blocked_cells(game: SnakeGame) -> set[Point]:
    """Cells that block a step; the tail cell moves away, so it is free."""
    body = list(game.body)
    return set(body[:-1])


def _survivable(game: SnakeGame, new_head: Point) -> bool:
    """Can the snake still reach its own tail after moving to ``new_head``?

    Short snakes cannot trap themselves, so they are always survivable.
    """
    body = list(game.body)
    new_body = [new_head, *body[:-1]]
    if len(new_body) <= 2:
        return True
    blocked = set(new_body[1:-1])
    tail_cell = new_body[-1]
    seen = {new_head}
    queue = deque([new_head])
    while queue:
        cell = queue.popleft()
        if cell == tail_cell:
            return True
        for direction in DIRECTIONS:
            neighbour = _next_cell(game, cell, direction)
            if neighbour is None or neighbour in blocked or neighbour in seen:
                continue
            seen.add(neighbour)
            queue.append(neighbour)
    return tail_cell in seen


def choose_turn(game: SnakeGame) -> Direction | None:
    """Best heading for the snake, or None when every heading is fatal."""
    if game.status is not GameStatus.PLAYING:
        return None
    blocked = _blocked_cells(game)
    options: list[tuple[tuple[bool, int, bool], Direction]] = []
    for direction in DIRECTIONS:
        if direction is OPPOSITE_DIRECTION[game.direction]:
            continue
        new_head = _next_cell(game, game.head, direction)
        if new_head is None or new_head in blocked:
            continue
        ranking = (
            not _survivable(game, new_head),  # surviving moves first
            _distance(game, new_head, game.food) if game.food else 0,
            direction is not game.direction,  # going straight wins ties
        )
        options.append((ranking, direction))
    if not options:
        return None
    return min(options, key=lambda entry: entry[0])[1]


def play(
    game: SnakeGame,
    *,
    max_ticks: int = 4000,
    on_tick: Callable[[SnakeGame], None] | None = None,
) -> GameStatus:
    """Let the snake drive itself until the round ends or ``max_ticks`` is hit."""
    ticks = 0
    while game.status is GameStatus.PLAYING and ticks < max_ticks:
        turn = choose_turn(game)
        if turn is not None:
            game.request_turn(turn)
        game.advance()
        ticks += 1
        if on_tick is not None:
            on_tick(game)
    return game.status