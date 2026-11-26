"""Entry point - ``python3 main.py`` starts Snake in the terminal.

``main.py`` owns the loop a round lives in (build a board, play it, store the
score, offer a replay) and hands the :class:`SnakeGame` to whichever renderer
was asked for.  Run ``python3 main.py --help`` for the flags.
"""
from __future__ import annotations

import argparse
import curses
import sys

from game_logic import GameStatus, SnakeGame
from renderers import GameOutcome
from settings import BOARD_HEIGHT, BOARD_WIDTH

from renderers.curses_ui import play as play_in_terminal
from renderers.text_ui import play as play_as_text
from simulator import play as simulate
from scores import record_score

try:
    from renderers.tk_ui import play as play_in_window
except ImportError:  # this machine has no tkinter
    play_in_window = None

RENDERERS = ("curses", "text", "tk")


def _board_options(args: argparse.Namespace) -> SnakeGame:
    """Build the round described by the command-line flags."""
    try:
        return SnakeGame(
            width=args.width,
            height=args.height,
            wrap=args.wrap,
            rng_seed=args.seed,
        )
    except ValueError as error:
        raise SystemExit(f"invalid board: {error}") from error


def _report(outcome: GameOutcome) -> None:
    """Print the verdict of a finished round and keep the best score."""
    verdict = outcome.status.value if outcome.status is not GameStatus.PLAYING else "stopped"
    print(f"{verdict} at score {outcome.score}")
    best, updated = record_score(outcome.score)
    print(f"best {best}{'' if updated else ' (unchanged)'}")


def _play_with_curses(game: SnakeGame) -> GameOutcome:
    """Run the terminal renderer, explaining a missing tty to the player."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit(
            "this is not an interactive terminal - rerun with --renderer text "
            "or --simulate"
        )
    try:
        return play_in_terminal(game)
    except curses.error as error:
        raise SystemExit(
            f"curses could not take over this terminal ({error}) - "
            "rerun with --renderer text"
        ) from error


def _play_graphically(game: SnakeGame) -> int:
    """Run the tkinter renderer, explaining a missing display to the player."""
    if play_in_window is None:
        raise SystemExit("tkinter is unavailable here - use --renderer text")
    try:
        outcome = play_in_window(game)
    except Exception as error:  # tkinter reports Tcl failures opaquely
        raise SystemExit(f"no window available ({error}) - use --renderer text") from error
    _report(outcome)
    return 0


def _play_rounds(game: SnakeGame, play_round, args: argparse.Namespace) -> int:
    """Play rounds until the player quits or until ``args.rounds`` are done."""
    rounds_left = max(1, args.rounds)
    while True:
        outcome = play_round(game)
        _report(outcome)
        rounds_left -= 1
        if not outcome.replay or rounds_left == 0:
            return 0
        game.restart()


def main(argv: list[str] | None = None) -> int:
    """Parse the flags, then hand the game to the chosen renderer."""
    parser = argparse.ArgumentParser(description="Play Snake from the terminal.")
    parser.add_argument(
        "--renderer",
        choices=RENDERERS,
        default="curses",
        help="front-end to use (default: curses; text works anywhere, tk needs a display)",
    )
    parser.add_argument("--width", type=int, default=BOARD_WIDTH, help="board columns")
    parser.add_argument("--height", type=int, default=BOARD_HEIGHT, help="board rows")
    parser.add_argument(
        "--wrap", action="store_true", help="leave one edge and reappear on the other"
    )
    parser.add_argument("--seed", type=int, default=None, help="fix food placement")
    parser.add_argument(
        "--simulate", action="store_true", help="let the computer play the round"
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=4000,
        help="how many steps --simulate may take before it gives up",
    )
    parser.add_argument(
        "--rounds", type=int, default=1, help="play again automatically up to this many times"
    )
    args = parser.parse_args(argv)
    game = _board_options(args)

    if args.simulate:
        status = simulate(game, max_ticks=args.max_ticks)
        tempo = game.current_speed()
        print(f"the computer played unattended (final tempo {tempo:.0f} steps/second):")
        _report(GameOutcome(game.score, status, False))
        return 0

    if args.renderer == "tk":
        return _play_graphically(game)
    if args.renderer == "text":
        return _play_rounds(game, play_as_text, args)
    return _play_rounds(game, _play_with_curses, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))