"""Game-wide configuration for Snake.

Every other module imports its defaults from here, so the whole look and feel of
the game can be re-tuned by editing this one file.
"""
from __future__ import annotations

from pathlib import Path

# --- board ---------------------------------------------------------------------
BOARD_WIDTH = 40  # playable columns
BOARD_HEIGHT = 18  # playable rows
MIN_BOARD_WIDTH = 4  # smallest board the logic accepts
MIN_BOARD_HEIGHT = 4

# --- snake ---------------------------------------------------------------------
START_LENGTH = 3  # segments the snake starts with
POINTS_PER_FOOD = 10  # score gained for every food eaten

# --- speed (snake steps per second) --------------------------------------------
BASE_SPEED = 8.0  # starting tempo
SPEED_PER_FOOD = 0.35  # tempo gained after each food
MAX_SPEED = 20.0  # tempo ceiling

# --- characters used by the text/terminal renderers ---------------------------
FOOD_CHAR = "*"
HEAD_CHAR = "@"
BODY_CHAR = "O"

# --- where the best score is stored -------------------------------------------
HIGH_SCORE_FILE = Path(__file__).resolve().with_name("highscore.txt")