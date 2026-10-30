"""Real HTTP/SQLite preparation with explicitly constructed Calendar/ranking inputs.

Publication fixtures use the production calculator; this does not claim that
Week Transition, sporting eligibility or a whole season ran in these scenarios.
"""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text

from beta_engine.application.calendar_package_run_adapter import (
    CALENDAR_EVENT_ENTITY_KIND, CALENDAR_METADATA_ENTITY_KIND, CALENDAR_SCOPE,
)
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy, RankingWeek, calculate_official_ranking,
)
from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageEntity, PackageType
from beta_engine.domain.tournaments.edition_entry_timing import EditionEntryTiming
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
    TournamentRankingSnapshotAuthorityModel, RunPackageApplicationReceiptModel,
    BranchSavedRevisionModel, RunBranchModel,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import TournamentRankingSnapshotAuthorityStore
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical
PACKAGE = "calendar-2000-2001"
EVENT = "edition-a"


def document():
    event = CalendarEvent(event_id=EVENT, season="2000/2001", season_week=20,
        template_id="template-a", host_country="CZE", region="Europe", main_draw_size=4,
        event_level_overrides={"unrelated_setting": "retain"})
    return CanonicalPackageDocument(package_type=PackageType.CALENDAR, package_id=PACKAGE,
        source_version=1, explicit_scope=(CALENDAR_SCOPE,), entities=(
            PackageEntity(source_entity_id="calendar.metadata", entity_kind=CALENDAR_METADATA_ENTITY_KIND,
                scope=CALENDAR_SCOPE, payload={"season":"2000/2001", "metadata":None}),
            PackageEntity(source_entity_id=EVENT, entity_kind=CALENDAR_EVENT_ENTITY_KIND,
                scope=CALENDAR_SCOPE, payload=event.model_dump(mode="json")),
        )).model_dump(mode="json")


def timing(clock=None, **updates):
    clock = clock or RunCalendar.fax_default()
    body = EditionEntryTiming(main_open=RunWeekPosition(calendar=clock, season_index=0, week=13)).model_dump(mode="json")
    return body | updates


def setup(server, *, clock=None):
    if clock is None:
        rid, bid, _ = _create_run(server, display_name="Edition Entry")
    else:
        code, run = _request("POST", server.base_url + "/run-containers", {
            "display_name":"Edition Entry", "calendar":{
                "weeks_per_year":clock.weeks_per_year, "season_start_year_week":clock.season_start_year_week,
                "start_year":clock.start_year, "season_count":clock.season_count}})
        assert code == 201, run
        rid, bid = run["run_id"], run["viewer_branch_id"]
    root = f"{server.base_url}/admin/runs/{rid}/branches/{bid}/packages"
    doc = document()
    code, preview = _request("POST", root + "/preview", {"document":doc})
    assert code == 200, preview
    code, result = _request("POST", root + "/confirm", {
        "document":doc, "command_id":"calendar", "expected_head_revision_id":preview["saved_head_revision_id"],
        "expected_draft_version":preview["draft_version"], "expected_state_fingerprint":preview["current_state_fingerprint"],
        "expected_preview_fingerprint":preview["preview_fingerprint"]})
    assert code == 200, result
    entry = root + f"/calendar/{PACKAGE}/editions/{EVENT}/entry-timing"
    save = f"{server.base_url}/run-containers/{rid}/branches/{bid}/working-draft/save"
    return rid, bid, root, entry, save


def reviewed(server, entry, config, command="timing"):
    code, preview = _request("POST", entry + "/preview", {"timing":config})
    assert code == 200, preview
    request = {"timing":config, "command_id":command,
        "expected_preview_fingerprint":preview["preview_fingerprint"],
        "operator_label":"Operator", "audit_reason":"Review explicit Entry timing and ranking"}
    return preview, request


def seed_publications(server, rid, bid, *, current=15):
    factory = server.app.state.runtime.repository._session_factory
    snapshots = {}
    with factory.begin() as session:
        for week in (13,14,15):
            snapshot = calculate_official_ranking(run_id=rid, branch_id=bid,
                week=RankingWeek(season_index=0, week=week), policy=OfficialRankingPolicy(policy_id="fixture-policy"),
                players=(), results=())
            snapshots[week] = snapshot
            session.add(PublishedOfficialRankingModel(run_id=rid, branch_id=bid, week_ordinal=week-1,
                snapshot_fingerprint=snapshot.fingerprint, payload_json=snapshot.model_dump_json()))
        session.add(AuthoritativeWorldStateModel(run_id=rid, branch_id=bid, current_ordinal=current-1,
            ranking_fingerprint=snapshots[current].fingerprint))
    return snapshots


def stage_plan(server, entry, config):
    preview, request = reviewed(server, entry, config)
    assert preview["can_confirm_configuration"] is True
    assert preview["ranking_binding_status"] == "missing_prerequisite"
    code, result = _request("POST", entry + "/confirm", request)
    assert code == 200, result
    return result


def test_plan_and_exact_historical_ranking_save_reopen_retry(tmp_path):
    db = f"sqlite:///{tmp_path / 'entry.db'}"
    with ApiServer(database_url=db) as server:
        rid, bid, root, entry, save = setup(server)
        before = _request("GET", root)
        assert _request("GET", entry)[1]["blockers"][0]["code"] == "entry_timing_missing"
        preview, _ = reviewed(server, entry, timing())
        assert preview["preflight_status"] == "missing_content"
        assert preview["resolved"]["default_ranking_completed_week"]["week"] == 13
        assert preview["resolved"]["ranking_publication_week"]["week"] == 14
        assert preview["automatic_eligibility_status"] == "not_implemented"
        assert _request("GET", root) == before
        staged = stage_plan(server, entry, timing())
        assert staged["ranking_authority_fingerprint"] is None
        payload = next(e["payload"] for e in staged["state"]["entities"] if e["source_entity_id"] == EVENT)
        assert payload["event_level_overrides"]["unrelated_setting"] == "retain"
        assert "entry_timing" not in document()["entities"][1]["payload"]["event_level_overrides"]
        assert _request("POST", save, {"expected_draft_version":staged["draft_version"]})[0] == 201

        snapshots = seed_publications(server, rid, bid)
        candidate, bind_request = reviewed(server, entry, timing(), command="bind")
        assert candidate["ranking_binding_status"] == "ready_for_explicit_confirmation"
        assert candidate["timing_and_ranking_ready"] is False
        assert candidate["ranking_snapshot_fingerprint"] == snapshots[14].fingerprint
        assert candidate["current_window"] == "qualification"
        code, bound = _request("POST", entry + "/confirm", bind_request)
        assert code == 200, bound
        assert bound["ranking_authority_fingerprint"]
        assert _request("GET", entry)[1]["timing_and_ranking_ready"] is True
        code, saved = _request("POST", save, {"expected_draft_version":bound["draft_version"]})
        assert code == 201, saved
        # Both owners are captured by ordinary Save; neither requires a new Save implementation.
        revision_id = saved["saved_revision"]["revision_id"]
        code, revision = _request("GET", f"{server.base_url}/run-containers/{rid}/branches/{bid}/saved-revisions/{revision_id}")
        assert code == 200, revision
        content = revision["payload"]["content"]
        assert content["run_package_state"]["fingerprint"] == bound["state_fingerprint"]
        saved_ranking = load_saved_ranking_component(revision["payload"], run_id=rid, branch_id=bid)
        assert saved_ranking is not None
        assert len(saved_ranking.tournament_ranking_snapshot_authorities) == 1
        saved_authority = saved_ranking.tournament_ranking_snapshot_authorities[0]
        assert saved_authority.fingerprint == bound["ranking_authority_fingerprint"]
        assert saved_authority.ranking_snapshot == snapshots[14]
        view = _request("GET", entry)

    with ApiServer(database_url=db) as reopened:
        entry = entry.replace(server.base_url, reopened.base_url)
        assert _request("GET", entry) == view
        code, retry = _request("POST", entry + "/confirm", bind_request)
        assert code == 200 and retry == bound | {"already_applied":True}
        assert _request("POST", entry + "/confirm", bind_request | {"audit_reason":"Different command"})[0] == 409
        assert _request("GET", entry) == view
        with reopened.app.state.runtime.repository._session_factory() as session:
            actual = TournamentRankingSnapshotAuthorityStore(session).get(run_id=rid, branch_id=bid, event_id=EVENT)
            assert actual.ranking_week.week == 14
            assert actual.ranking_snapshot_fingerprint == snapshots[14].fingerprint


def test_stale_review_opened_plan_and_missing_exact_publication_fail_closed(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'stale.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        staged = stage_plan(server, entry, timing())
        snapshots = seed_publications(server, rid, bid)
        factory = server.app.state.runtime.repository._session_factory
        preview, stale = reviewed(server, entry, timing(), command="stale")
        with factory.begin() as session:
            world = session.get(AuthoritativeWorldStateModel, (rid,bid))
            next_ranking = calculate_official_ranking(run_id=rid, branch_id=bid,
                week=RankingWeek(season_index=0,week=16), policy=OfficialRankingPolicy(policy_id="fixture-policy"),
                players=(), results=())
            session.add(PublishedOfficialRankingModel(run_id=rid, branch_id=bid, week_ordinal=15,
                snapshot_fingerprint=next_ranking.fingerprint, payload_json=next_ranking.model_dump_json()))
            world.current_ordinal = 15
            world.ranking_fingerprint = next_ranking.fingerprint
        before = _request("GET", root)
        assert _request("POST", entry + "/confirm", stale)[0] == 409
        assert _request("GET", root) == before
        changed = timing(main_duration_weeks=1)
        preview, change_request = reviewed(server, entry, changed, command="retime")
        assert preview["can_confirm_configuration"] is False
        assert "entry_timing_locked" in {b["code"] for b in preview["blockers"]}
        assert _request("POST", entry + "/confirm", change_request)[0] == 409
        assert _request("GET", entry.replace(EVENT, "unknown-edition"))[0] == 409
        with factory.begin() as session:
            row = session.get(PublishedOfficialRankingModel, (rid,bid,13))
            session.delete(row)
        preview, _ = reviewed(server, entry, timing(), command="missing")
        assert preview["ranking_snapshot_fingerprint"] is None
        assert "ranking_publication_missing" in {b["code"] for b in preview["blockers"]}
        assert preview["timing_and_ranking_ready"] is False


def test_ranking_failure_rolls_back_package_draft_and_receipt(tmp_path, monkeypatch):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'rollback.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        stage_plan(server, entry, timing())
        seed_publications(server, rid, bid)
        _, request = reviewed(server, entry, timing(), command="rollback")
        before = _request("GET", root)
        def fail_after_package_edit(*args, **kwargs):
            raise ValueError("Injected ranking boundary failure")
        monkeypatch.setattr(TournamentRankingSnapshotAuthorityStore, "adopt", fail_after_package_edit)
        assert _request("POST", entry + "/confirm", request)[0] == 409
        assert _request("GET", root) == before
        after, _ = reviewed(server, entry, timing(), command="rollback")
        assert after["preview_fingerprint"] == request["expected_preview_fingerprint"]
        with server.app.state.runtime.repository._session_factory() as session:
            assert session.get(RunPackageApplicationReceiptModel, (rid,bid,"rollback")) is None
            assert session.get(TournamentRankingSnapshotAuthorityModel, (rid,bid,EVENT)) is None


def test_custom_clock_can_save_plan_without_claiming_legacy_ranking_execution(tmp_path):
    clock = RunCalendar(52, 1, 2000, 3)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'earth.db'}") as server:
        rid, bid, root, entry, save = setup(server, clock=clock)
        preview, request = reviewed(server, entry, timing(clock))
        assert preview["preflight_status"] == "unsupported_execution"
        assert preview["can_confirm_configuration"] is True
        assert preview["ranking_will_be_bound"] is False
        assert preview["current_week"] is None
        code, staged = _request("POST", entry + "/confirm", request)
        assert code == 200, staged
        assert _request("POST", save, {"expected_draft_version":staged["draft_version"]})[0] == 201
        assert _request("GET", entry)[1]["preflight_status"] == "unsupported_execution"


def test_explicit_override_is_existing_publication_and_conflicting_binding_is_preserved(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'override.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        override = RunWeekPosition(calendar=RunCalendar.fax_default(), season_index=0, week=13)
        config = timing(ranking_publication_override=override.model_dump(mode="json"))
        stage_plan(server, entry, config)
        snapshots = seed_publications(server, rid, bid)
        preview, request = reviewed(server, entry, config, command="override")
        assert preview["resolved"]["ranking_source"] == "explicit_publication_override"
        assert preview["ranking_snapshot_fingerprint"] == snapshots[13].fingerprint
        assert _request("POST", entry + "/confirm", request)[0] == 200
        original = _request("GET", entry)
        conflict, request = reviewed(server, entry, timing(), command="replace-ranking")
        assert "ranking_binding_conflict" in {b["code"] for b in conflict["blockers"]}
        assert conflict["can_confirm_configuration"] is False
        assert _request("POST", entry + "/confirm", request)[0] == 409
        assert _request("GET", entry) == original
        assert _request("GET", entry.replace(bid, "foreign-branch"))[0] == 404
        # A corrupt publication cannot become a fresh source by rehashing its payload.
        with server.app.state.runtime.repository._session_factory.begin() as session:
            row = session.get(PublishedOfficialRankingModel, (rid,bid,12))
            payload = json.loads(row.payload_json)
            payload["policy"]["best_n"] = 1
            row.payload_json = json.dumps(payload)
        assert _request("GET", entry)[0] == 409


def test_two_reviewers_cannot_apply_the_same_old_preview_twice(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'race.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        stage_plan(server, entry, timing())
        seed_publications(server, rid, bid)
        before, request = reviewed(server, entry, timing(), command="review-a")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_request, "POST", entry + "/confirm", body)
                       for body in (request, request | {"command_id":"review-b"})]
            results = [f.result() for f in futures]
        assert sorted(code for code,_ in results) == [200,409], results
        after = _request("GET", entry)[1]
        assert after["draft_version"] == before["draft_version"] + 1
        assert after["ranking_binding_status"] == "bound"
        with server.app.state.runtime.repository._session_factory() as session:
            rows = session.scalars(select(TournamentRankingSnapshotAuthorityModel).where(
                TournamentRankingSnapshotAuthorityModel.run_id == rid,
                TournamentRankingSnapshotAuthorityModel.branch_id == bid)).all()
            assert len(rows) == 1
            receipt = session.get(RunPackageApplicationReceiptModel, (rid,bid,results[0][1].get("command_id", "review-b")))
            assert receipt is not None
            payload = json.loads(receipt.payload_json)
            payload["request"]["audit_reason"] = "Tampered saved review"
            receipt.payload_json = json.dumps(payload)
            session.commit()
        winning_request = request if results[0][0] == 200 else request | {"command_id":"review-b"}
        assert _request("POST", entry + "/confirm", winning_request)[0] == 409


def test_null_stored_timing_is_corrupt_not_an_absent_plan(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'null.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        preview, _ = reviewed(server, entry, timing())
        state = _request("GET", root)[1]["state"]
        entity = next(e for e in state["entities"] if e["source_entity_id"] == EVENT)
        payload = entity["payload"]
        payload["event_level_overrides"]["entry_timing"] = None
        RunPackageService(server.app.state.runtime.repository).edit_entity(
            run_id=rid, branch_id=bid, run_local_id=entity["run_local_id"], payload=payload,
            expected_draft_version=preview["draft_version"], expected_state_fingerprint=preview["state_fingerprint"])
        before = _request("GET", root)
        assert _request("GET", entry)[0] == 409
        assert _request("POST", entry + "/preview", {"timing":timing()})[0] == 409
        assert _request("GET", root) == before


def test_saved_clock_hash_is_verified_before_timing_or_ranking_reads(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'hash.db'}") as server:
        rid, bid, root, entry, save = setup(server)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, bid)
            head = session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
            payload = json.loads(head.payload_json)
            payload["run"]["run_calendar"]["weeks_per_year"] = 52
            head.payload_json = json.dumps(payload)
        assert _request("GET", entry)[0] == 409
        assert _request("POST", entry + "/preview", {"timing":timing()})[0] == 409
