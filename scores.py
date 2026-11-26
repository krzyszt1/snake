"""High-score bookkeeping: one number in a small text file.

The default file lives next to the project (``settings.HIGH_SCORE_FILE``), so a
round played from any working directory still finds the same best score.  Every
renderer reports its score back to ``main.py``, which calls :func:`record_score`.
"""
from __future__ import annotations

from pathlib import Path

from settings import HIGH_SCORE_FILE


def load_high_score(path: Path | str = HIGH_SCORE_FILE) -> int:
    """Best score ever recorded, or 0 when the file is missing/malformed."""
    try:
        with open(path) as handle:
            return int(handle.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def record_score(score: int, path: Path | str = HIGH_SCORE_FILE) -> tuple[int, bool]:
    """Store ``score`` when it beats the stored best; return (best, updated)."""
    best = load_high_score(path)
    if score <= best:
        return best, False
    with open(path, "w") as handle:
        handle.write(f"{score}\n")
    return score, True