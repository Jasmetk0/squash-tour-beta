"""Actual production Run creation helpers; no fabricated hashes or validation caches."""
import sqlite3
from contextlib import closing


def create(client, name):
    response = client.post("/run-containers", json={"display_name": name})
    assert response.status_code == 201, response.text
    run = response.json()
    branches = client.get("/run-branches", params={"run_id": run["run_id"]}).json()["run_branches"]
    return run["run_id"], run["viewer_branch_id"], branches[0]["saved_head_revision_id"]


def params(a, b):
    return dict(zip(("run_a_id", "branch_a_id", "revision_a_id", "run_b_id", "branch_b_id", "revision_b_id"), (*a, *b), strict=True))


def snapshot(path):
    with closing(sqlite3.connect(path)) as connection:
        return tuple(connection.iterdump())
