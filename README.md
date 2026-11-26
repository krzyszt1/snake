# Snake

Play Snake in your terminal.  The game is written with the Python standard
library only - nothing to install, no package manager, and no display required.

## Play it

```bash
python3 main.py                 # play in the terminal (needs a real terminal)
python3 main.py --renderer text # turn-based fallback that works anywhere
python3 main.py --renderer tk   # tkinter window, only if you have a display
python3 main.py --simulate      # watch the computer play a round by itself
```

Run the commands from this folder, which is where ``main.py`` lives.

A round ends when the snake runs into a wall or into itself, or when it has
filled the whole board.  Your best score is kept in ``highscore.txt`` next to
the game, and that file is ignored by git.

## Controls

| key                        | effect                                    |
| -------------------------- | ----------------------------------------- |
| arrows, ``wasd`` or ``hjkl`` | turn the snake                          |
| ``p``                      | pause, so the board stays on screen       |
| ``q``                      | stop playing and report the score         |
| ``enter`` or ``r``         | play another round once the round is over |

A snake never turns back on itself, so a reversal key press is ignored instead
of losing the round.  At most two pending turns are buffered, which keeps a fast
``wa`` sequence honest.

## Flags

```text
--renderer {curses,text,tk}  front-end to use (default: curses)
--width COLUMNS              board width   (default 40)
--height ROWS                board height  (default 18)
--wrap                       edges are portals instead of walls
--seed N                     fix food placement so a round can be repeated
--rounds N                   replay automatically up to N times
--simulate                   let the computer player drive a round
--max-ticks N                how many steps --simulate may think for
```

Worth trying:

```bash
python3 main.py --width 20 --height 10   # a board you can actually finish
python3 main.py --wrap                   # edges are portals, not walls
printf 'd\nd\nw\nq\n' | python3 main.py --renderer text
```

## Layout

| file                     | what lives in it                                            |
| ------------------------ | ----------------------------------------------------------- |
| ``settings.py``          | every tunable number and character - re-tune the game here  |
| ``game_logic.py``        | the rules: body, food, collisions, scoring, speed           |
| ``renderers/curses_ui.py`` | the terminal front-end (default)                          |
| ``renderers/text_ui.py`` | turn-based front-end that works without a terminal          |
| ``renderers/tk_ui.py``   | optional tkinter front-end                                  |
| ``simulator.py``         | computer player that drives a round unattended              |
| ``scores.py``            | reading and writing the best score                          |
| ``main.py``              | command line, round loop, verdict                           |

The rules never draw anything and the front-ends never decide what is legal, so
either half can be changed without touching the other.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite covers the rules, the computer player, the best-score file and the
command line, and none of it needs a terminal or a display.