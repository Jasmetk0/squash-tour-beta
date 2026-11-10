"""Saved ATP source -> native Next Gen tournament, via real HTTP and SQLite."""

import pytest

from beta_engine.application.atp_next_gen_edition import NEXT_GEN_2025_ID
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _save_atp_source(server):
    packages = server.base_url + "/admin/runs/run/branches/branch/packages/source-atp-reference-calendar"
    code, review = _request("POST", packages + "/preview", {})
    assert code == 200, review
    code, applied = _request("POST", packages + "/confirm", {
        "command_id": "apply-atp-source",
        "expected_head_revision_id": review["saved_head_revision_id"],
        "expected_draft_version": review["draft_version"],
        "expected_state_fingerprint": review["current_state_fingerprint"],
        "expected_preview_fingerprint": review["preview_fingerprint"],
        "conflict_resolutions": {},
    })
    assert code == 200, applied
    code, saved = _request(
        "POST", server.base_url + "/run-containers/run/branches/branch/working-draft/save",
        {"expected_draft_version": applied["draft_version"]},
    )
    assert code == 201, saved


def _preview_request(view):
    return {
        "command_id": "import-next-gen-2025",
        "expected_saved_head": view["saved_head_revision_id"],
        "expected_checkpoint_fingerprint": view["checkpoint_fingerprint"],
        "expected_tour_fingerprint": view["tour_fingerprint"],
        "start_slot": 1,
        "seed": 891,
        "operator_label": "Admin",
        "audit_reason": "Review the Saved ATP Next Gen source",
    }


def test_saved_atp_next_gen_import_plays_fifteen_squash_matches_and_reopens(tmp_path):
    database = f"sqlite:///{tmp_path / 'atp-next-gen.db'}"
    with ApiServer(database_url=database) as server:
        # Civil 2025/W51 maps to Run Season 1/Week 4 without civil-day simulation.
        repo, _ = setup(server, RunCalendar(52, 48, 2025, 2), count=8)
        url = tour_url(server) + "/atp-next-gen-2025/preview"
        missing_source = _preview_request(inspect(server))
        code, error = _request("POST", url, missing_source)
        assert code == 409, error
        assert "Saved ATP Calendar Package" in error["detail"]["message"]

        _save_atp_source(server)
        before = inspect(server)
        code, error = _request("POST", url, missing_source)
        assert code == 409, error
        assert "source changed" in error["detail"]["message"]

        code, review = _request("POST", url, _preview_request(before))
        assert code == 200, review
        assert inspect(server) == before
        edition = review["command"]["data"]
        assert edition["edition_id"] == NEXT_GEN_2025_ID
        assert edition["week"]["week"] == 4
        assert edition["announcement_week"]["week"] == 3
        assert edition["main_entrant_count"] == 8
        assert edition["group_configuration"]["groups"]["group_count"] == 2
        assert edition["group_configuration"]["groups"]["group_size"] == 4
        assert edition["ranked"] is False
        assert edition["point_table"] == {}

        code, result = _request("POST", tour_url(server) + "/execute", {
            "command": review["command"],
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert code == 201, result
        assert not inspect(server)["saved"]
        save_tour(server)
        for week in (3, 4):
            execute(server, command(inspect(server), "transition", name=f"next-gen-week-{week}"))
            save_tour(server)

        current = inspect(server)
        entrants = [player["player_id"] for player in current["players"]]
        assert len(entrants) == 8
        execute(server, command(
            current, "submit", edition_id=NEXT_GEN_2025_ID,
            data={"player_ids": entrants},
        ))
        for action in ("approve", "draw"):
            execute(server, command(inspect(server), action, edition_id=NEXT_GEN_2025_ID))
        save_tour(server)

        for slot in range(5):
            execute(server, command(inspect(server), "next-slot", name=f"next-gen-slot-{slot}"))
            save_tour(server)
        current = inspect(server)
        evidence = current["edition_evidence"][NEXT_GEN_2025_ID]
        assert len(evidence["matches"]) == 15
        groups = current["groups"][NEXT_GEN_2025_ID]
        assert [len(group["rows"]) for group in groups["standings"]["groups"]] == [4, 4]
        assert len(groups["bracket"]["matches"]) == 3
        assert current["next_slot"] is None
        with repo._session_factory() as session:
            checkpoint = load_checkpoint(session, run_id="run", branch_id="branch")
        tournament = next(t for t in checkpoint.tournaments if t.tournament_id == NEXT_GEN_2025_ID)
        assert len(tournament.matches) == 15
        assert all(match.result.rally_log.events for match in tournament.matches)
        assert all(match.input_context.best_of == 5 for match in tournament.matches)
        assert tournament.winner_player_id == tournament.matches[-1].result.winner_player_id
        execute(server, command(inspect(server), "confirm-result", edition_id=NEXT_GEN_2025_ID))
        save_tour(server)
        execute(server, command(inspect(server), "transition", name="next-gen-close-week"))
        save_tour(server)
        finished = inspect(server)
        assert all(
            row["points"] == 0 and not row["counted_results"]
            for row in finished["state"]["rankings"][-1]["rows"]
        )

    with ApiServer(database_url=database) as server:
        restored = inspect(server)
        assert restored["edition_evidence"][NEXT_GEN_2025_ID] == finished["edition_evidence"][NEXT_GEN_2025_ID]
        assert restored["state"]["rankings"][-1] == finished["state"]["rankings"][-1]
