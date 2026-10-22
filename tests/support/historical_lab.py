"""Real HTTP/SQLite source fixture shared by Lab API and browser acceptance."""

import json
import sqlite3
from pathlib import Path

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_saved_revision_history_api import ApiServer


def non_lab_rows(path):
    with sqlite3.connect(path) as db:
        return {
            name: sorted(
                db.execute(
                    'SELECT * FROM "' + name.replace('"', '""') + '"'
                ).fetchall(),
                key=repr,
            )
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            if name
            not in {
                "player_lab_sessions",
                "match_lab_sessions",
                "tournament_lab_sessions",
            }
        }


def prepare_history(path):
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        clock = RunCalendar(52, 35, 2030, 3)
        repo, _ = setup(server, clock, 4)
        prebirth = sign_prospects(server, repo, clock)
        created = fork(server, prebirth["revision_id"], name="Historical Lab native")
        branch = created["branch_id"]
        target = Tour(server, branch)
        born = target.advance("lab-birth")["revision_id"]
        target.configure("lab-edition")
        drawn = target.view()["saved_head_revision_id"]
        target.execute("play", "lab-play", edition_id="lab-edition")
        target.save()
        target.execute("confirm-result", "lab-confirm", edition_id="lab-edition")
        latest = target.save()["revision_id"]
        original = Tour(server, "branch")
        original.advance("original-later-birth")
        ids = [p["player_id"] for p in target.view()["players"]]
        return {
            "run": "run",
            "branch": branch,
            "prebirth": prebirth["revision_id"],
            "born": born,
            "drawn": drawn,
            "latest": latest,
            "player": "born-native-15",
            "opponent": next(pid for pid in ids if pid != "born-native-15"),
            "event": "lab-edition",
        }


def cached_history(root):
    """Opt-in local immutable fixture reuse. Every import still revalidates all rows."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path, meta = root / "source.sqlite", root / "source.json"
    if not meta.exists():
        if path.exists():
            raise ValueError("Incomplete source fixture; use a fresh directory")
        result = prepare_history(path)
        meta.write_text(json.dumps(result))
    return path, json.loads(meta.read_text())
