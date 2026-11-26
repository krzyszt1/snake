"""The computer player behind ``main.py --simulate``, checked without a terminal.

Run with::

    python3 -m unittest discover -s tests
"""
from __future__ import annotations

import unittest

from game_logic import Direction, GameStatus, OPPOSITE_DIRECTION, SnakeGame
from simulator import choose_turn, play
from settings import MIN_BOARD_HEIGHT, MIN_BOARD_WIDTH, POINTS_PER_FOOD

WIDTH = MIN_BOARD_WIDTH + 2
HEIGHT = MIN_BOARD_HEIGHT + 2


def cornered(game: SnakeGame) -> SnakeGame:
    """Hand-set a body that traps its own head in the top-left corner.

    White-box by design: the only free cell is the head's own tail, which is
    the cell the step vacates, so nothing the snake could do survives.
    """
    game.body.clear()
    game.body.extend([(0, 0), (1, 0), (1, 1), (0, 1), (0, 2)])
    game.direction = Direction.RIGHT
    return game


class ChooseTurnTests(unittest.TestCase):
    """One heading, chosen from the board alone."""

    def test_a_fresh_round_gets_a_heading(self) -> None:
        self.assertIsNotNone(choose_turn(SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=1)))

    def test_a_finished_round_gets_no_heading(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=1)
        game.status = GameStatus.GAME_OVER
        self.assertIsNone(choose_turn(game))

    def test_the_same_board_always_gets_the_same_heading(self) -> None:
        first = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=4)
        second = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=4)
        self.assertEqual(choose_turn(first), choose_turn(second))

    def test_a_turn_around_is_never_offered(self) -> None:
        for seed in range(1, 13):
            game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=seed)
            turn = choose_turn(game)
            self.assertIsNot(turn, OPPOSITE_DIRECTION[game.direction])

    def test_the_offered_heading_lands_on_a_cell_the_snake_can_move_into(self) -> None:
        for seed in range(1, 13):
            game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=seed)
            turn = choose_turn(game)
            self.assertIsNotNone(turn)
            delta_x, delta_y = turn.value
            head_x, head_y = game.head
            landing = (head_x + delta_x, head_y + delta_y)
            self.assertTrue(game.is_walkable(landing))
            self.assertNotIn(landing, set(list(game.body)[:-1]))

    def test_a_cornered_snake_gets_no_heading(self) -> None:
        self.assertIsNone(choose_turn(cornered(SnakeGame(width=WIDTH, height=HEIGHT))))

    def test_food_straight_ahead_keeps_the_snake_on_its_course(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=5)
        self.assertIs(choose_turn(game), game.direction)

    def test_a_heading_towards_the_food_beats_a_heading_away_from_it(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=1)
        turn = choose_turn(game)
        self.assertIsNotNone(turn)
        delta_x, delta_y = turn.value
        head_x, head_y = game.head
        food_x, food_y = game.food
        straight_to_food = abs(head_x - food_x) + abs(head_y - food_y)
        after_turn = abs(head_x + delta_x - food_x) + abs(head_y + delta_y - food_y)
        self.assertLessEqual(after_turn, straight_to_food)


class PlayTests(unittest.TestCase):
    """Driving a whole round with no keyboard at all."""

    def test_the_computer_ate_something(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        play(game)
        self.assertGreater(game.score, 0)

    def test_the_computer_ends_the_round_it_was_handed(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        self.assertIs(play(game), game.status)

    def test_the_computer_fills_a_small_board(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        self.assertIs(play(game), GameStatus.WON)
        self.assertEqual(len(game.body), WIDTH * HEIGHT)
        self.assertEqual(game.score, (WIDTH * HEIGHT - game.start_length) * POINTS_PER_FOOD)

    def test_the_computer_fills_a_wrapped_small_board_too(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, wrap=True, rng_seed=11)
        self.assertIs(play(game), GameStatus.WON)
        self.assertEqual(len(game.body), WIDTH * HEIGHT)

    def test_a_wrapped_round_can_still_crash_into_itself(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, wrap=True, rng_seed=1)
        self.assertIs(play(game), GameStatus.GAME_OVER)

    def test_the_round_is_untouched_without_any_ticks(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        self.assertIs(play(game, max_ticks=0), GameStatus.PLAYING)
        self.assertEqual(game.score, 0)

    def test_the_tick_limit_bounds_the_work_done(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        steps_taken: list[int] = []
        play(game, max_ticks=3, on_tick=lambda _: steps_taken.append(1))
        self.assertLessEqual(len(steps_taken), 3)
        self.assertGreater(len(steps_taken), 0)

    def test_each_tick_reports_the_state_back_to_the_caller(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        lengths: list[int] = []
        play(game, max_ticks=3, on_tick=lambda running: lengths.append(len(running.body)))
        self.assertEqual(len(lengths), 3)
        self.assertEqual(lengths[0], game.start_length)
        self.assertEqual(sorted(lengths), lengths)

    def test_the_snake_grows_only_on_the_ticks_it_eats(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=2)
        lengths: list[int] = []
        play(game, max_ticks=5, on_tick=lambda running: lengths.append(len(running.body)))
        self.assertEqual(len(lengths), 5)
        self.assertEqual(lengths[0], game.start_length)
        self.assertEqual(max(lengths), game.start_length + game.food_eaten)

    def test_simulating_a_finished_round_does_nothing(self) -> None:
        game = SnakeGame(width=WIDTH, height=HEIGHT, rng_seed=7)
        play(game)
        self.assertIs(play(game), game.status)
        self.assertEqual(game.score, (WIDTH * HEIGHT - game.start_length) * POINTS_PER_FOOD)