"""Actual W52/W80 later-week knockout: replay, persistence, recovery and rollback."""
import copy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    load_saved_calendar_match,
)
from tests.api.test_calendar_continuation_flow import root, save_continuation
from tests.api.test_calendar_population_sporting_checkpoint import (
    play, prepare, restore, save,
)
from tests.api.test_calendar_sporting_week_flow import (
    advance, weekly_command,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def tournament_url(server):
    return root(server) + "/knockouts/simulate"


def command(view, *, tournament_id="later-four", command_id="later-command", seed=813):
    return {
        "command_id": command_id,
        "tournament_id": tournament_id,
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "entrant_ids": view["player_ids"][:4],
        "seed": seed,
        "operator_label": "Admin",
        "audit_reason": "Run actual later-week four-player sporting knockout",
    }


@pytest.mark.parametrize("clock", [
    RunCalendar(52, 52, 2030, 3),
    RunCalendar(80, 80, 2100, 3),
])
def test_later_week_knockout_is_atomic_saved_replayable_and_recoverable(tmp_path, clock, monkeypatch):
    path = tmp_path / "native-knockout.db"
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, clock)
        played, _ = play(server, head)
        initial_saved = save(server, played)
        _, starting = _request("GET", root(server))
        week, _ = advance(server, weekly_command(starting))
        week_saved = save_continuation(server, week)
        _, view = _request("GET", root(server))
        assert view["sporting_week"]["week"] == 2 and view["saved"]
        source = command(view)
        before = _dump(path)
        assert _request("POST", tournament_url(server), {
            **source, "expected_checkpoint_fingerprint": "f" * 64,
        })[0] == 409
        assert _dump(path) == before

        from beta_engine.application import calendar_followup_knockout_service as svc
        original = svc.replace_checkpoint

        def failure(*args, **kwargs):
            original(*args, **kwargs)
            raise ValueError("Injected after tournament sporting row replacement")

        monkeypatch.setattr(svc, "replace_checkpoint", failure)
        assert _request("POST", tournament_url(server), source)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(svc, "replace_checkpoint", original)

        code, result = _request("POST", tournament_url(server), source)
        assert code == 201, result
        assert result["scope"] == "sporting_exhibition_knockout_not_official"
        assert not result["official_ranking_published"]
        matches = result["tournament"]["matches"]
        assert len(matches) == 3
        assert [m["sequence"] for m in matches] == [1, 2, 3]
        assert matches[0]["result"]["player_a_id"] == source["entrant_ids"][0]
        assert matches[1]["result"]["player_a_id"] == source["entrant_ids"][2]
        assert (
            matches[2]["result"]["player_a_id"],
            matches[2]["result"]["player_b_id"],
        ) == (
            matches[0]["result"]["winner_player_id"],
            matches[1]["result"]["winner_player_id"],
        )
        assert result["winner_player_id"] == matches[-1]["result"]["winner_player_id"]
        assert _request("POST", tournament_url(server), source) == (201, result)
        _, unsaved = _request("GET", root(server))
        assert not unsaved["saved"] and not unsaved["can_play"]
        assert len(unsaved["tournaments"]) == 1
        assert len(unsaved["matches"]) == 3
        assert _request("POST", tournament_url(server), command(unsaved, tournament_id="blocked"))[0] == 409

        saved = save_continuation(server, result)
        checkpoint = saved["payload"]["content"][COMPONENT_KEY]
        assert checkpoint["state"]["schema_version"] == "calendar_sporting_checkpoint.v4"
        assert checkpoint["state"]["week_events"][-1]["tournament_id"] == "later-four"
        assert saved["payload"]["content"]["calendar_standalone_match"] == initial_saved["payload"]["content"]["calendar_standalone_match"]
        assert _request("POST", tournament_url(server), source) == (201, result)
        for match in matches:
            code, replay = _request("GET", root(server) + f"/{match['match_id']}/replay")
            assert code == 200 and replay["exact_replay"], replay
        assert repo.verify_branch_saved_revision_hash(revision_id=week_saved["revision_id"])

        # A rehashed but fabricated semifinal winner must not pass full
        # canonical population, playoff, and successor reconstruction.
        for damage in ("winner", "player", "missing", "downgrade"):
            corrupted = copy.deepcopy(saved["payload"])
            component = corrupted["content"][COMPONENT_KEY]
            data = component["state"]
            event = data["week_events"][-1]
            if damage == "winner":
                match = event["matches"][0]["result"]
                match["winner_player_id"] = match["loser_player_id"]
            elif damage == "player":
                data["players"][0]["long_term_fatigue"] = 999
            elif damage == "missing":
                event["matches"].pop()
            elif damage == "downgrade":
                data["schema_version"] = "calendar_sporting_checkpoint.v3"
            component["fingerprint"] = canonical_hash(data)
            with pytest.raises(ValueError):
                load_saved_calendar_match(corrupted, run_id="run", branch_id="branch")

        _, current = _request("GET", root(server))
        week3, _ = advance(server, weekly_command(current, name="after-tournament"))
        assert sum(n for _, n in week3["advance"]["played_counts"]) == 6
        final_saved = save_continuation(server, week3)
        assert _request("POST", tournament_url(server), source) == (201, result)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])

    with ApiServer(database_url=db) as restarted:
        _, state = _request("GET", root(restarted))
        assert state["sporting_week"]["week"] == 3 and state["saved"]
        assert len(state["tournaments"]) == 1 and len(state["matches"]) == 3
        for match in matches:
            assert _request("GET", root(restarted) + f"/{match['match_id']}/replay")[1]["exact_replay"]
        assert _request("POST", tournament_url(restarted), source) == (201, result)
        restore(restarted, week_saved["revision_id"])
        _, older = _request("GET", root(restarted))
        assert not older["tournaments"] and older["sporting_week"]["week"] == 2
        restore(restarted, final_saved["revision_id"])
        _, forward = _request("GET", root(restarted))
        assert len(forward["tournaments"]) == 1
        assert forward["saved"] and forward["sporting_week"]["week"] == 3
