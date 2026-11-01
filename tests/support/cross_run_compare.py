"""Actual production Run creation helpers; no fabricated hashes or validation caches."""
import sqlite3
from contextlib import closing


def params(a, b):
    return dict(zip(("run_a_id", "branch_a_id", "revision_a_id", "run_b_id", "branch_b_id", "revision_b_id"), (*a, *b), strict=True))


def snapshot(path):
    with closing(sqlite3.connect(path)) as connection:
        return tuple(connection.iterdump())
