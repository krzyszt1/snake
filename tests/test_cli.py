"""The command-line entry point, driven as a subprocess.

These smoke tests never need a terminal: they use the turn-based renderer, the
built-in simulator, and main.py's own complaint when curses is asked for.  Run
them from the project folder with::

    python3 -m unittest discover -s tests
"""
from __future__ import annotations

import re
import subprocess
import sys

import unittest


def run(*arguments: str, stdin: str = "") -> subprocess.CompletedProcess:
    """Run ``python3 main.py`` from the project folder and collect its output."""
    return subprocess.run(
        [sys.executable, "main.py", *arguments],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=120,
    )


def score_of(output: str) -> int:
    """The score the game reported ("stopped at score 0", "game over at score 40")."""
    scores = re.findall(r"at score (\d+)", output)
    if not scores:
        raise AssertionError(f"no score line in output: {output!r}")
    return int(scores[-1])


# The text renderer starts the snake mid-board heading right, so this many
# commands lands it exactly on the right-hand wall.
STRAIGHT_INTO_WALL = "\n".join(["d"] * 20) + "\n"


class SimulatorTests(unittest.TestCase):
    """--simulate plays a round with no keyboard involved."""

    def test_a_simulated_round_needs_no_input(self) -> None:
        result = run("--simulate", "--seed", "5")
        self.assertEqual(result.returncode, 0)
        self.assertIn("unattended", result.stdout)
        self.assertIn("best", result.stdout)

    def test_the_simulator_ate_food(self) -> None:
        self.assertGreater(score_of(run("--simulate", "--seed", "5").stdout), 0)

    def test_the_same_seed_scores_the_same(self) -> None:
        first = score_of(run("--simulate", "--seed", "13").stdout)
        second = score_of(run("--simulate", "--seed", "13").stdout)
        self.assertEqual(first, second)

    def test_a_wrapped_board_is_accepted(self) -> None:
        result = run("--simulate", "--wrap", "--seed", "5")
        self.assertEqual(result.returncode, 0)
        self.assertIn("at score", result.stdout)

    def test_a_big_board_is_accepted(self) -> None:
        result = run("--simulate", "--width", "30", "--height", "20", "--seed", "2")
        self.assertEqual(result.returncode, 0)
        self.assertGreater(score_of(result.stdout), 0)

    def test_an_undersized_board_is_rejected_cleanly(self) -> None:
        result = run("--simulate", "--width", "2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid board", result.stderr)

    def test_the_tick_limit_stops_a_runaway_simulation(self) -> None:
        result = run("--simulate", "--seed", "5", "--max-ticks", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("stopped at score", result.stdout)


class TextRendererTests(unittest.TestCase):
    """The turn-based renderer answers piped input, so it is testable."""

    def test_a_round_draws_a_board_and_shows_its_controls(self) -> None:
        result = run("--renderer", "text")
        self.assertEqual(result.returncode, 0)
        self.assertIn("turn", result.stdout)
        self.assertIn("+", result.stdout)

    def test_turn_commands_move_the_snake_around(self) -> None:
        result = run("--renderer", "text", "--seed", "3", stdin="w\nd\ns\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("@", result.stdout)
        self.assertEqual(score_of(result.stdout), 0)

    def test_a_reversal_command_is_ignored_not_fatal(self) -> None:
        result = run("--renderer", "text", stdin="a\nq\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("@", result.stdout)

    def test_help_repeats_the_controls_without_moving_the_snake(self) -> None:
        result = run("--renderer", "text", stdin="?\nq\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(score_of(result.stdout), 0)

    def test_quitting_early_reports_a_stopped_round(self) -> None:
        result = run("--renderer", "text", stdin="q\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("stopped at score", result.stdout)

    def test_running_into_the_wall_is_reported(self) -> None:
        result = run("--renderer", "text", stdin=STRAIGHT_INTO_WALL)
        self.assertEqual(result.returncode, 0)
        self.assertIn("game over at score", result.stdout)

    def test_a_replay_starts_a_fresh_round_on_the_same_board(self) -> None:
        on_small_board = run(
            "--renderer",
            "text",
            "--width",
            "6",
            "--height",
            "4",
            "--rounds",
            "2",
            stdin="d\nd\nd\nr\n",
        )
        self.assertEqual(on_small_board.returncode, 0)
        self.assertIn("game over at score", on_small_board.stdout)
        self.assertIn("stopped at score 0", on_small_board.stdout)
        self.assertEqual(on_small_board.stdout.count("at score"), 2)

    def test_replaying_asks_for_a_fresh_round(self) -> None:
        straight = "\n".join(["d"] * 40) + "\n"
        result = run(
            "--renderer",
            "text",
            "--rounds",
            "2",
            stdin=STRAIGHT_INTO_WALL + "r\n" + STRAIGHT_INTO_WALL + "q\n",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("game over at score"), 2)


class TerminalRendererTests(unittest.TestCase):
    """The default renderer only works in front of a real terminal."""

    def test_a_non_terminal_session_is_explained(self) -> None:
        result = run()
        self.assertIn("not an interactive terminal", result.stderr)
        self.assertNotEqual(result.returncode, 0)

    def test_the_hint_names_the_renderer_that_works_anywhere(self) -> None:
        result = run()
        self.assertIn("--renderer text", result.stderr)

    def test_the_window_renderer_is_reported_when_unavailable(self) -> None:
        result = run("--renderer", "tk")
        self.assertIn("use --renderer text", result.stderr)


class HelpTests(unittest.TestCase):
    """The flags a player needs are discoverable from --help."""

    def test_help_documents_the_renderers_and_the_simulator(self) -> None:
        result = run("--help")
        self.assertEqual(result.returncode, 0)
        for flag in ("--renderer", "--simulate", "--wrap", "--seed", "--rounds"):
            self.assertIn(flag, result.stdout)

    def test_an_unknown_renderer_is_rejected(self) -> None:
        result = run("--renderer", "graphics")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)