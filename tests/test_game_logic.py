"""Rules of the game, checked without any terminal or graphics.

Run with::

    python3 -m unittest discover -s tests
"""
from __future__ import annotations

import unittest

from game_logic import Direction, GameStatus, OPPOSITE_DIRECTION, SnakeGame
from settings import BASE_SPEED, MAX_SPEED, MIN_BOARD_HEIGHT, MIN_BOARD_WIDTH
from settings import POINTS_PER_FOOD, SPEED_PER_FOOD, START_LENGTH

WIDTH = 6
HEIGHT = 4


def new_game(**kwargs) -> SnakeGame:
    """A small deterministic round every test can start from."""
    kwargs.setdefault("width", WIDTH)
    kwargs.setdefault("height", HEIGHT)
    kwargs.setdefault("start_length", START_LENGTH)
    return SnakeGame(**kwargs)


def place_snake(game: SnakeGame, cells: list[tuple[int, int]]) -> None:
    """Hand-set the body (head first) so collisions can be tested exactly.

    ``cells`` must be a contiguous path; only white-box collision tests use this.
    """
    game.body.clear()
    game.body.extend(cells)


def no_food(game: SnakeGame) -> SnakeGame:
    """Take food out of the picture so a movement test sees only movement."""
    game.food = None
    return game


class BoardSizeTests(unittest.TestCase):
    """The logic refuses boards and snakes that cannot fit."""

    def test_rejects_a_too_narrow_board(self) -> None:
        with self.assertRaises(ValueError):
            SnakeGame(width=MIN_BOARD_WIDTH - 1, height=MIN_BOARD_HEIGHT)

    def test_rejects_a_too_short_board(self) -> None:
        with self.assertRaises(ValueError):
            SnakeGame(width=MIN_BOARD_WIDTH, height=MIN_BOARD_HEIGHT - 1)

    def test_accepts_the_smallest_legal_board(self) -> None:
        game = SnakeGame(width=MIN_BOARD_WIDTH, height=MIN_BOARD_HEIGHT, start_length=1)
        self.assertEqual(game.status, GameStatus.PLAYING)
        self.assertEqual(len(game.body), 1)

    def test_rejects_a_start_length_below_one(self) -> None:
        with self.assertRaises(ValueError):
            SnakeGame(width=8, height=4, start_length=0)

    def test_rejects_a_start_length_that_cannot_turn(self) -> None:
        with self.assertRaises(ValueError):
            SnakeGame(width=8, height=4, start_length=8)

    def test_starting_cells_are_all_on_the_board(self) -> None:
        game = new_game()
        for cell in game.body:
            self.assertTrue(game.is_walkable(cell))

    def test_head_starts_to_the_right_of_its_neck(self) -> None:
        game = new_game()
        neck_x, neck_y = game.body[1]
        self.assertEqual(game.head, (neck_x + 1, neck_y))
        self.assertEqual(game.direction, Direction.RIGHT)

    def test_head_and_body_never_overlap_at_the_start(self) -> None:
        game = new_game()
        self.assertEqual(len(game.body), len(set(game.body)))

    def test_food_starts_on_an_empty_cell(self) -> None:
        game = new_game()
        self.assertIsNotNone(game.food)
        self.assertTrue(game.is_walkable(game.food))
        self.assertNotIn(game.food, game.occupied())

    def test_seed_makes_the_first_food_reproducible(self) -> None:
        self.assertEqual(new_game(rng_seed=7).food, new_game(rng_seed=7).food)

    def test_seed_does_not_decide_the_starting_position(self) -> None:
        self.assertEqual(new_game(rng_seed=7).head, new_game(rng_seed=99).head)


class TurningTests(unittest.TestCase):
    """Heading changes: legal sideways turns, refused reversals and buffering."""

    def test_every_allowed_heading_moves_the_snake_that_way(self) -> None:
        for direction in Direction:
            if direction is OPPOSITE_DIRECTION[Direction.RIGHT]:
                continue  # reversing is refused, and that has its own test
            game = no_food(new_game())
            game.request_turn(direction)
            game.advance()
            neck_x, neck_y = game.body[1]
            delta_x, delta_y = direction.value
            self.assertEqual(game.head, (neck_x + delta_x, neck_y + delta_y))
            self.assertEqual(game.direction, direction)

    def test_turning_up_moves_to_a_smaller_row_number(self) -> None:
        game = no_food(new_game())
        start_y = game.head[1]
        game.request_turn(Direction.UP)
        game.advance()
        self.assertEqual(game.head[1], start_y - 1)

    def test_turning_down_moves_to_a_larger_row_number(self) -> None:
        game = no_food(new_game())
        start_y = game.head[1]
        game.request_turn(Direction.DOWN)
        game.advance()
        self.assertEqual(game.head[1], start_y + 1)

    def test_turning_around_while_moving_is_refused(self) -> None:
        game = no_food(new_game())
        self.assertFalse(game.request_turn(OPPOSITE_DIRECTION[game.direction]))
        game.advance()
        self.assertEqual(game.direction, Direction.RIGHT)

    def test_the_same_heading_twice_is_refused(self) -> None:
        game = no_food(new_game())
        self.assertTrue(game.request_turn(Direction.UP))
        self.assertFalse(game.request_turn(Direction.UP))

    def test_only_two_pending_turns_are_buffered(self) -> None:
        game = no_food(new_game())
        self.assertTrue(game.request_turn(Direction.UP))
        self.assertTrue(game.request_turn(Direction.LEFT))
        self.assertFalse(game.request_turn(Direction.DOWN))
        self.assertEqual(list(game.queued_turns), [Direction.UP, Direction.LEFT])

    def test_buffered_turns_are_applied_one_step_apart(self) -> None:
        game = no_food(new_game())
        game.request_turn(Direction.UP)
        game.request_turn(Direction.LEFT)
        game.advance()
        self.assertEqual(game.direction, Direction.UP)
        game.advance()
        self.assertEqual(game.direction, Direction.LEFT)
        self.assertEqual(list(game.queued_turns), [])

    def test_reversal_is_checked_against_the_pending_heading(self) -> None:
        game = no_food(new_game())
        game.request_turn(Direction.UP)
        self.assertFalse(game.request_turn(Direction.DOWN))
        game.advance()
        self.assertEqual(game.direction, Direction.UP)

    def test_turning_up_first_lets_the_snake_head_left_afterwards(self) -> None:
        game = no_food(new_game())
        game.request_turn(Direction.UP)
        game.advance()
        game.request_turn(Direction.LEFT)
        game.advance()
        self.assertEqual(game.direction, Direction.LEFT)
        self.assertEqual(len(game.body), START_LENGTH)

    def test_turning_is_refused_once_the_round_is_lost(self) -> None:
        game = no_food(new_game())
        while not game.is_over():
            game.advance()
        self.assertFalse(game.request_turn(Direction.UP))

    def test_turn_rejects_values_that_are_not_directions(self) -> None:
        game = new_game()
        with self.assertRaises(TypeError):
            game.request_turn("up")


class MovementTests(unittest.TestCase):
    """One step at a time: grow, starve, crash, wrap and fill the board."""

    def test_a_plain_step_keeps_length_and_score(self) -> None:
        game = no_food(new_game())
        length_before = len(game.body)
        self.assertTrue(game.advance())
        self.assertEqual(len(game.body), length_before)
        self.assertEqual(game.score, 0)
        self.assertEqual(game.food_eaten, 0)

    def test_the_head_enters_the_cell_directly_ahead_of_it(self) -> None:
        game = no_food(new_game())
        head_x, head_y = game.head
        self.assertTrue(game.advance())
        self.assertEqual(game.head, (head_x + 1, head_y))

    def test_repeated_steps_never_grow_the_snake_without_food(self) -> None:
        game = no_food(new_game(wrap=True))
        length_before = len(game.body)
        for _ in range(6):
            self.assertTrue(game.advance())
        self.assertEqual(len(game.body), length_before)

    def test_eating_the_food_grows_scores_and_replaces_it(self) -> None:
        game = new_game()
        game.food = (game.head[0] + 1, game.head[1])
        length_before = len(game.body)
        self.assertTrue(game.advance())
        self.assertEqual(len(game.body), length_before + 1)
        self.assertEqual(game.score, POINTS_PER_FOOD)


class SpeedTests(unittest.TestCase):
    """Tempo only ever grows with food and stops at the ceiling."""

    def test_a_fresh_round_starts_at_the_base_tempo(self) -> None:
        self.assertEqual(new_game().current_speed(), BASE_SPEED)

    def test_one_food_raises_the_tempo_by_the_configured_step(self) -> None:
        game = new_game()
        game.food = (game.head[0] + 1, game.head[1])
        game.advance()
        self.assertAlmostEqual(game.current_speed(), BASE_SPEED + SPEED_PER_FOOD)

    def test_the_tempo_never_passes_the_ceiling(self) -> None:
        game = new_game()
        game.food_eaten = 10_000
        self.assertEqual(game.current_speed(), MAX_SPEED)

    def test_the_snake_gets_faster_the_more_it_eats(self) -> None:
        game = new_game()
        speeds = [game.current_speed()]
        for _ in range(5):
            game.food = (game.head[0] + 1, game.head[1])
            game.advance()
            speeds.append(game.current_speed())
        self.assertEqual(speeds, sorted(speeds))
        self.assertGreater(speeds[-1], speeds[0])


class RestartTests(unittest.TestCase):
    """Replaying gives a clean slate on the same board."""

    def test_restart_clears_score_growth_and_pending_turns(self) -> None:
        game = new_game()
        game.request_turn(Direction.UP)
        game.food = (game.head[0] + 1, game.head[1])
        game.advance()
        game.restart()
        self.assertEqual(game.score, 0)
        self.assertEqual(game.food_eaten, 0)
        self.assertEqual(game.status, GameStatus.PLAYING)
        self.assertEqual(len(game.body), START_LENGTH)
        self.assertEqual(game.direction, Direction.RIGHT)
        self.assertEqual(list(game.queued_turns), [])

    def test_restart_keeps_the_board_it_was_played_on(self) -> None:
        game = new_game(width=9, height=6, wrap=True, rng_seed=3)
        for _ in range(12):  # a straight snake on a wrapping board never dies
            game.advance()
        final_cells = game.cells()
        final_wrap = game.wrap
        game.restart()
        self.assertEqual(game.cells(), final_cells)
        self.assertEqual(game.wrap, final_wrap)
        self.assertEqual((game.width, game.height), (9, 6))

    def test_restart_makes_a_lost_round_playable_again(self) -> None:
        game = no_food(new_game())
        while not game.is_over():
            game.advance()
        game.restart()
        self.assertEqual(game.status, GameStatus.PLAYING)
        self.assertEqual((game.score, game.food_eaten), (0, 0))
        self.assertEqual(len(game.body), START_LENGTH)
        self.assertIsNotNone(game.food)
        self.assertNotIn(game.food, game.occupied())
        self.assertTrue(game.advance())

    def test_eating_does_not_change_the_heading(self) -> None:
        game = new_game()
        game.food = (game.head[0] + 1, game.head[1])
        game.advance()
        self.assertEqual(game.direction, Direction.RIGHT)

    def test_walking_off_the_board_ends_the_round(self) -> None:
        game = no_food(new_game())
        self.assertTrue(game.advance())
        self.assertEqual(game.head, (WIDTH - 2, HEIGHT // 2))
        self.assertTrue(game.advance())
        self.assertEqual(game.head, (WIDTH - 1, HEIGHT // 2))
        self.assertFalse(game.advance())
        self.assertEqual(game.status, GameStatus.GAME_OVER)
        self.assertEqual(len(game.body), START_LENGTH)

    def test_losing_at_the_edge_stops_before_moving(self) -> None:
        game = no_food(new_game())
        for _ in range(6):
            game.advance()
        self.assertEqual(game.head, (WIDTH - 1, HEIGHT // 2))

    def test_a_normal_turning_loop_kills_a_long_snake(self) -> None:
        game = no_food(new_game(width=8, start_length=5))
        game.request_turn(Direction.UP)
        game.advance()
        game.request_turn(Direction.LEFT)
        game.advance()
        game.request_turn(Direction.DOWN)
        self.assertFalse(game.advance())
        self.assertEqual(game.status, GameStatus.GAME_OVER)

    def test_head_entering_a_body_cell_midway_ends_the_round(self) -> None:
        game = no_food(new_game())
        place_snake(
            game,
            [(3, 2), (2, 2), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2), (5, 2)],
        )
        self.assertFalse(game.advance())
        self.assertEqual(game.status, GameStatus.GAME_OVER)
        self.assertEqual(len(game.body), 9)

    def test_head_entering_the_tail_cell_is_allowed(self) -> None:
        game = no_food(new_game())
        place_snake(game, [(3, 2), (2, 2), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2)])
        self.assertTrue(game.advance())
        self.assertEqual(game.status, GameStatus.PLAYING)
        self.assertEqual(game.head, (4, 2))
        self.assertEqual(len(game.body), 8)
        self.assertEqual(len(set(game.body)), 8)

    def test_a_step_after_the_round_is_lost_changes_nothing(self) -> None:
        game = no_food(new_game())
        while not game.is_over():
            game.advance()
        score_when_lost = game.score
        self.assertFalse(game.advance())
        self.assertEqual(game.score, score_when_lost)
        self.assertEqual(len(game.body), START_LENGTH)
        self.assertEqual(game.status, GameStatus.GAME_OVER)

    def test_wrapping_reenters_on_the_other_edge(self) -> None:
        game = no_food(new_game(wrap=True))
        for _ in range(WIDTH - 1 - WIDTH // 2):  # right up to the last column
            self.assertTrue(game.advance())
        self.assertEqual(game.head, (WIDTH - 1, HEIGHT // 2))
        self.assertTrue(game.advance())
        self.assertEqual(game.head, (0, HEIGHT // 2))

    def test_wrapping_the_rows_works_too(self) -> None:
        game = no_food(new_game(wrap=True))
        game.request_turn(Direction.DOWN)
        for _ in range(HEIGHT - HEIGHT // 2 - 1):  # right up to the last row
            self.assertTrue(game.advance())
        self.assertEqual(game.head, (WIDTH // 2, HEIGHT - 1))
        self.assertTrue(game.advance())
        self.assertEqual(game.head, (WIDTH // 2, 0))

    def test_a_wrapped_snake_survives_without_food(self) -> None:
        game = no_food(new_game(wrap=True))
        for _ in range(40):
            self.assertTrue(game.advance())
        self.assertEqual(game.status, GameStatus.PLAYING)
        self.assertEqual(len(set(game.body)), len(game.body))

    def test_filling_the_board_after_the_last_food_wins(self) -> None:
        game = new_game()
        path = []
        for y in range(HEIGHT):
            row = [(x, y) for x in range(WIDTH)]
            if y % 2:
                row.reverse()
            path.extend(row)
        place_snake(game, list(reversed(path[:-1])))
        game.food = path[-1]
        game.direction = Direction.LEFT  # the head already faces the last free cell
        self.assertTrue(game.advance())
        self.assertEqual(game.status, GameStatus.WON)
        self.assertIsNone(game.food)
        self.assertEqual(len(game.body), WIDTH * HEIGHT)
        self.assertEqual(game.score, POINTS_PER_FOOD)