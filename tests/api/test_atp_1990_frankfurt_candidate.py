"""Saved test-only ATP candidate -> real native HTTP/SQLite execution.

Never publish the candidate or import historical player identities/results.
Only the source document provider is substituted while copying the fixture.
"""
import json

import pytest

from beta_engine.application.atp_historical_calendar_adapter import ATPHistoricalCalendarAdapter
from beta_engine.application.atp_sporting_package_adapter import (
    build_atp_sporting_package,
    parse_sporting_profile,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
from tests.api.test_atp_next_gen_edition import _preview_request, _save_atp_source
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_atp_1990_historical_evidence_batch import ROOT

pytestmark = pytest.mark.pr_critical


def test_frankfurt_candidate_saved_source_matches_ranking_and_cold_reopen(tmp_path, monkeypatch):
    batch = json.loads((ROOT / "historical_evidence" / "1990_batch_01.json").read_text(encoding="utf-8"))
    row = next(r for r in batch["occurrences"] if r["series_id"] == "atp_finals")
    evidence = row["historical_evidence"]["targeted_import_research"]
    proposed = evidence["proposed_adaptation"]
    probe = evidence["saved_source_execution_probe"]
    assert evidence["points_evidence"]["primary_exact_table_verified"] is False
    assert probe["points_certified"] is False
    assert row["profile_status"] == "not_in_published_sporting_source"

    catalog = build_atp_sporting_package()
    assert row["occurrence_id"] not in {e.source_entity_id for e in catalog.entities}
    modern = next(e for e in catalog.entities if e.source_entity_id == "atp_2025_atp_finals")
    candidate = parse_sporting_profile({
        **modern.payload,
        "occurrence_id": row["occurrence_id"],
        "category_id": row["category_id"],
        "name": row["historical_evidence"]["historical_name"],
        "source_start_date": proposed["source_start_date"],
        "source_end_date": proposed["source_end_date"],
        "source_urls": proposed["source_urls"],
        "played_group_win_points": proposed["played_group_win_points"],
        "knockout_stage_points": proposed["knockout_stage_points"],
    })
    # Offset 43 compresses the setup to two real transitions while preserving
    # the actual civil 1990/W46. Existing application tests cover offsets 1/37.
    clock = RunCalendar(**probe["calendar"])
    pos = clock.calendar_to_season(1990, 46)
    assert pos is not None
    assert (pos.season_index, pos.season_week) == (0, 4)
    assert probe["play_position"] == {
        "season_index": pos.season_index, "season_week": pos.season_week,
        "calendar_year": pos.calendar_year, "year_week": pos.year_week,
    }
    edition_id = row["occurrence_id"]
    assert edition_id == probe["occurrence_id"]
    # Produce a canonical child using the real adapter against a temporary
    # source file. Existing published profiles stay byte-for-byte unchanged.
    raw = json.loads((ROOT / "squash_sporting_profiles_v1.json").read_text(encoding="utf-8"))
    raw["source_version"] += 1
    raw["profiles"].append(candidate.model_dump(mode="json"))
    (tmp_path / "squash_sporting_profiles_v1.json").write_text(
        json.dumps(raw), encoding="utf-8")
    sporting = build_atp_sporting_package(tmp_path)
    assert {e.source_entity_id for e in sporting.entities} == {
        *(e.source_entity_id for e in catalog.entities), edition_id}
    assert {e.source_entity_id: e.payload for e in sporting.entities
            if e.source_entity_id != edition_id} == {
                e.source_entity_id: e.payload for e in catalog.entities}
    original = ATPHistoricalCalendarAdapter().build_document()
    assert original.children[-1].source_fingerprint == catalog.source_fingerprint
    document = original.model_copy(update={
        "source_version": original.source_version + 1,
        "children": (*original.children[:-1], sporting),
    })

    db = f"sqlite:///{tmp_path / 'frankfurt-candidate.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, count=8)
        url = tour_url(server) + f"/atp-source-editions/{edition_id}/preview"
        before_copy = _preview_request(inspect(server))
        before_copy["command_id"] = "import-historical-candidate"
        before_copy["audit_reason"] = "Test-only uncertified Frankfurt candidate"
        code, error = _request("POST", url, before_copy)
        assert code == 409, error
        assert "ATP sporting profiles Package" in error["detail"]["message"]
        with monkeypatch.context() as copying:
            copying.setattr(ATPHistoricalCalendarAdapter, "build_document", lambda self: document)
            _save_atp_source(server)
        # Real production default restored immediately after copy.
        assert ATPHistoricalCalendarAdapter().build_document().source_fingerprint == original.source_fingerprint
        code, error = _request("POST", url, before_copy)
        assert code == 409, error
        assert "source changed" in error["detail"]["message"]
        code, saved_catalog = _request("GET", tour_url(server) + "/atp-source-editions")
        assert code == 200, saved_catalog
        entry = next(e for e in saved_catalog["entries"] if e["profile"]["occurrence_id"] == edition_id)
        assert entry["profile"] == candidate.model_dump(mode="json")
        assert entry["execution_supported"] is True and not entry["execution_blockers"]
        assert entry["calendar_projection"]["run_weeks"][0]["season_week"] == 4
        before = inspect(server)
        request = {**_preview_request(before), "command_id": before_copy["command_id"],
                   "audit_reason": before_copy["audit_reason"]}
        code, review = _request("POST", url, request)
        assert code == 200, review
        assert inspect(server) == before
        edition = review["command"]["data"]
        assert edition["edition_id"] == edition_id
        assert edition["week"]["week"] == 4 and edition["announcement_week"]["week"] == 3
        assert edition["main_entrant_count"] == 8
        assert edition["ranked"] is True
        assert edition["point_table"] == candidate.knockout_stage_points
        assert edition["group_configuration"]["played_group_win_points"] == candidate.played_group_win_points
        assert f"ATP profile {edition_id} {entry['profile_fingerprint']}" in review["command"]["audit_reason"]
        code, result = _request("POST", tour_url(server) + "/execute", {
            "command": review["command"],
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert code == 201, result
        assert not inspect(server)["saved"]
        save_tour(server)
        for target in (3, 4):
            execute(server, command(inspect(server), "transition", name=f"frankfurt-week-{target}"))
            save_tour(server)
        current = inspect(server)
        entrants = [p["player_id"] for p in current["players"]]
        assert len(entrants) == len(set(entrants)) == 8
        execute(server, command(current, "submit", edition_id=edition_id,
                                data={"player_ids": entrants}))
        for action in ("approve", "draw"):
            execute(server, command(inspect(server), action, edition_id=edition_id))
        save_tour(server)

        for slot in range(5):
            execute(server, command(inspect(server), "next-slot", name=f"frankfurt-slot-{slot}"))
            save_tour(server)
        current = inspect(server)
        assert current["next_slot"] is None, current.get("groups")
        assert len(current["edition_evidence"][edition_id]["matches"]) == probe["expected_match_counts"]["total"]
        groups = current["groups"][edition_id]
        assert [len(g["rows"]) for g in groups["standings"]["groups"]] == [4, 4]
        assert len(groups["bracket"]["matches"]) == probe["expected_match_counts"]["knockout"]
        with repo._session_factory() as session:
            cp = load_checkpoint(session, run_id="run", branch_id="branch")
        tournament = next(t for t in cp.tournaments if t.tournament_id == edition_id)
        assert len(tournament.matches) == 15
        assert all(m.result.rally_log.events for m in tournament.matches)
        assert all(m.input_context.best_of == 5 for m in tournament.matches)
        assert tournament.winner_player_id == tournament.matches[-1].result.winner_player_id
        # Independent per-player oracle: each played group win pays 50,
        # each semifinal winner reaches the 100-point finalist floor, and
        # the final winner receives only the extra 150 (250 total component).
        expected = dict.fromkeys(entrants, 0)
        group_reward = candidate.played_group_win_points
        finalist = candidate.knockout_stage_points["finalist"]
        champion = candidate.knockout_stage_points["champion"]
        assert candidate.knockout_stage_points["semifinal"] == 0
        for match, award in zip(tournament.matches,
                [group_reward] * 12 + [finalist, finalist, champion - finalist], strict=True):
            expected[match.result.winner_player_id] += award
        assert sum(expected.values()) == probe["expected_total_candidate_points"] == 950
        assert max(expected.values()) <= probe["expected_max_individual_candidate_points"] == 400

        execute(server, command(current, "confirm-result", edition_id=edition_id))
        save_tour(server)
        execute(server, command(inspect(server), "transition", name="frankfurt-publish"))
        save_tour(server)
        finished = inspect(server)
        assert finished["saved"]
        assert finished["state"]["week"]["week"] == 5
        ranking = finished["state"]["rankings"][-1]
        assert {r["player_id"]: r["points"] for r in ranking["rows"]} == expected
        assert all(len(r["counted_results"]) <= 1 for r in ranking["rows"])
        saved_evidence = finished["edition_evidence"][edition_id]
        saved_head = finished["saved_head_revision_id"]
    def unavailable(*args, **kwargs):
        raise AssertionError("Saved source must not consult current defaults")

    with monkeypatch.context() as isolated:
        isolated.setattr(ATPHistoricalCalendarAdapter, "build_document", unavailable)
        with ApiServer(database_url=db) as restarted:
            reopened = inspect(restarted)
            code, restored_catalog = _request("GET", tour_url(restarted) + "/atp-source-editions")
            assert code == 200, restored_catalog
            assert restored_catalog["entries"] == saved_catalog["entries"]
            assert reopened["saved"] and reopened["saved_head_revision_id"] == saved_head
            assert reopened["edition_evidence"][edition_id] == saved_evidence
            assert reopened["state"]["rankings"][-1] == ranking
    # The immutable source catalog is still exactly the original source.
    assert build_atp_sporting_package().source_fingerprint == catalog.source_fingerprint
