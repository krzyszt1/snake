"""High-score file behaviour, exercised in a scratch directory."""
from __future__ import annotations

import unittest

from scores import load_high_score, record_score
from settings import HIGH_SCORE_FILE

import tempfile


class HighScoreTests(unittest.TestCase):
    """One number on disk: missing files read as zero, only better scores stick."""

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.path = f"{self.scratch.name}/best.txt"

    def tearDown(self) -> None:
        self.scratch.cleanup()

    def test_a_missing_file_reads_as_zero(self) -> None:
        self.assertEqual(load_high_score(self.path), 0)

    def test_an_unreadable_file_reads_as_zero(self) -> None:
        self.assertEqual(load_high_score("/definitely/not/a/file"), 0)

    def test_a_score_beating_the_record_is_written(self) -> None:
        self.assertEqual(record_score(30, self.path), (30, True))
        self.assertEqual(load_high_score(self.path), 30)

    def test_a_worse_score_leaves_the_record_alone(self) -> None:
        record_score(80, self.path)
        self.assertEqual(record_score(20, self.path), (80, False))
        self.assertEqual(load_high_score(self.path), 80)

    def test_an_equal_score_is_not_rewritten(self) -> None:
        record_score(80, self.path)
        self.assertEqual(record_score(80, self.path), (80, False))

    def test_zero_does_not_create_a_record(self) -> None:
        self.assertEqual(record_score(0, self.path), (0, False))
        self.assertEqual(load_high_score(self.path), 0)

    def test_garbage_in_the_file_is_replaced_by_a_real_score(self) -> None:
        with open(self.path, "w") as handle:
            handle.write("best score so far!")
        self.assertEqual(load_high_score(self.path), 0)
        self.assertEqual(record_score(10, self.path), (10, True))
        self.assertEqual(load_high_score(self.path), 10)

    def test_the_default_record_is_a_single_named_file(self) -> None:
        self.assertEqual(HIGH_SCORE_FILE.name, "highscore.txt")
        self.assertEqual(load_high_score(HIGH_SCORE_FILE), load_high_score())


    def test_the_record_never_grows_into_a_tall_list(self) -> None:
        for score in (10, 5, 20, 1, 20):
            record_score(score, self.path)
        with open(self.path) as handle:
            self.assertEqual(len(handle.read().splitlines()), 1)