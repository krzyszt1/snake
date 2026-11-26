"""Optional tkinter renderer: ``python3 main.py --renderer tk``.

Standard library only, but it needs a desktop/display; without one tkinter
raises :exc:`tkinter.TclError`, which ``main.py`` reports as a hint to use the
terminal renderer instead.
"""
from __future__ import annotations

from tkinter import Canvas, Frame, Tk

from game_logic import Direction, GameStatus, SnakeGame
from renderers import GameOutcome
from scores import load_high_score
from settings import BODY_CHAR, FOOD_CHAR, HEAD_CHAR

CELL_SIZE = 18
PADDING = 12
HEADER = 28

LETTER_TURNS = {
    "w": Direction.UP,
    "k": Direction.UP,
    "a": Direction.LEFT,
    "h": Direction.LEFT,
    "s": Direction.DOWN,
    "j": Direction.DOWN,
    "d": Direction.RIGHT,
    "l": Direction.RIGHT,
}
ARROW_TURNS = {"<Up>": Direction.UP, "<Down>": Direction.DOWN, "<Left>": Direction.LEFT}
ARROW_TURNS["<Right>"] = Direction.RIGHT


def play(game: SnakeGame, *, cell_size: int = CELL_SIZE) -> GameOutcome:
    """Open a tkinter window and play one round of ``game`` inside it."""
    board_width, board_height = game.width, game.height
    canvas_width = 2 * PADDING + board_width * cell_size
    canvas_height = 3 * PADDING + HEADER + board_height * cell_size
    origin_x = PADDING
    origin_y = PADDING + HEADER

    root = Tk()
    root.title("Snake")
    frame = Frame(root)
    frame.pack(fill="both", expand=True)
    canvas = Canvas(frame, width=canvas_width, height=canvas_height, bg="#101010")
    canvas.pack(fill="both", expand=True)
    state = {"replay": False, "quit": False, "paused": False}

    def on_character(event):
        char = (event.char or "").lower()
        turn = LETTER_TURNS.get(char)
        if turn is not None:
            game.request_turn(turn)
            return
        if char in {"q", "!"}:
            state["quit"] = True
        elif char == "p":
            state["paused"] = not state["paused"]
        elif game.is_over() and char in {"r", "\r"}:
            state["replay"] = True

    def on_arrow(event):
        turn = ARROW_TURNS.get(event.key)
        if turn is not None:
            game.request_turn(turn)

    def on_enter(event):
        if game.is_over():
            state["replay"] = True

    root.bind_all("<Key>", on_character)
    root.bind_all("<Return>", on_enter)
    for key_name in ARROW_TURNS:
        root.bind_all(key_name, on_arrow)

    def draw_board():
        canvas.delete("board")
        canvas.create_rectangle(
            origin_x,
            origin_y,
            origin_x + board_width * cell_size,
            origin_y + board_height * cell_size,
            outline="#888888",
            tags="board",
        )
        for x, y in game.occupied():
            is_head = (x, y) == game.head
            _draw_cell(x, y, HEAD_CHAR if is_head else BODY_CHAR)
        if game.food is not None:
            _draw_cell(*game.food, FOOD_CHAR)

    def _draw_cell(x, y, char):
        left = origin_x + x * cell_size
        top = origin_y + y * cell_size
        colour = "#66ff66" if char in (HEAD_CHAR, BODY_CHAR) else "#ff6666"
        canvas.create_rectangle(
            left + 1, top + 1, left + cell_size - 1, top + cell_size - 1,
            fill=colour, outline=colour, tags="board",
        )

    def draw_status(verdict):
        canvas.delete("status")
        canvas.create_text(
            origin_x,
            origin_y - HEADER // 2,
            anchor="w",
            fill="#dddddd",
            font="TkFixedFont",
            text=f"score {game.score}   best {load_high_score()}   {verdict}",
            tags="status",
        )

    def tick():
        if state["quit"] or state["replay"]:
            root.quit()
            return
        if state["paused"]:
            draw_status("PAUSED - p resumes")
            root.after(120, tick)
            return
        if game.is_over():
            draw_board()
            verdict = "GAME OVER" if game.status is GameStatus.GAME_OVER else "BOARD FULL"
            draw_status(f"{verdict} - r plays again, q quits")
            root.after(100, wait_for_choice)
            return
        game.advance()
        draw_board()
        draw_status("r replay once the round ends")
        root.after(int(1000 / game.current_speed()), tick)

    def wait_for_choice():
        if state["quit"] or state["replay"]:
            root.quit()
            return
        root.after(100, wait_for_choice)

    draw_board()
    draw_status("wasd/hjkl/arrows move, p pauses, q quits")
    root.after(250, tick)
    root.mainloop()
    root.destroy()
    return GameOutcome(game.score, game.status, state["replay"])