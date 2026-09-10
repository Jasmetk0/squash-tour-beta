"""Real FastAPI routing and SQLite inspection, with persisted candidate fixtures."""

import sqlite3
from types import SimpleNamespace

import pytest
from test_saved_revision_history_api import ApiServer, _request

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.infrastructure.db.models import (
    OfficialRankingCandidateModel,
    OfficialRankingCommandModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)


class HttpClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get(self, path):
        status, body = _request("GET", self.base_url + path)
        return SimpleNamespace(status_code=status, json=lambda: body)

    def post(self, path, *, json):
        status, body = _request("POST", self.base_url + path, json)
        return SimpleNamespace(status_code=status, json=lambda: body)


@pytest.fixture
def api(tmp_path):
    path = tmp_path / "api.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        client = HttpClient(server.base_url)
        factory = server.app.state.runtime.repository._session_factory
        with factory.begin() as session:
            session.add(
                RunContainerModel(
                    run_id="run", timeline_start_season=2000, timeline_end_season=2049
                )
            )
            session.add(
                RunContainerModel(
                    run_id="other-run",
                    timeline_start_season=2000,
                    timeline_end_season=2049,
                )
            )
            session.add(
                RunBranchModel(
                    run_id="run", branch_id="branch", display_name="Timeline 1"
                )
            )
            session.add(
                RunBranchModel(
                    run_id="run", branch_id="empty", display_name="Timeline 2"
                )
            )
        with factory.begin() as session:
            store = OfficialRankingCandidateStore(session)
            players = (
                OfficialRankingPlayer(
                    player_id="p",
                    tie_break_token="token",
                    tour_entry_week=RankingWeek(season_index=0, week=1),
                ),
            )
            results = (
                OfficialRankingResult(
                    player_id="p",
                    edition_id="edition",
                    source_fingerprint="award",
                    completed_week=RankingWeek(season_index=0, week=60),
                    first_publication_week=RankingWeek(season_index=0, week=61),
                    main_points=120,
                ),
            )
            first = calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=0, week=61),
                policy=OfficialRankingPolicy(policy_id="policy"),
                players=players,
                results=results,
            )
            second = calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=RankingWeek(season_index=1, week=1),
                policy=first.policy,
                players=players,
                results=results,
                previous=first,
            )
            store.append(first, bootstrap=True)
            store.append(second)
            session.add(
                OfficialRankingCommandModel(
                    run_id="run",
                    branch_id="branch",
                    command_id="command",
                    request_fingerprint="1" * 64,
                    target_ordinal=61,
                    snapshot_fingerprint=second.fingerprint,
                )
            )
        yield client, factory, path, first, second


def dump(path):
    with sqlite3.connect(path) as connection:
        return tuple(connection.iterdump())


PREFIX = "/admin/runs/run/branches/branch/ranking-candidates"


def test_history_detail_and_readonly_nonmutation(api):
    client, factory, path, first, second = api
    with factory.begin() as session:
        session.get(RunContainerModel, "run").read_only = 1
        session.get(RunBranchModel, "branch").read_only = 1
    before = dump(path)
    response = client.get(PREFIX)
    assert response.status_code == 200
    body = response.json()
    assert body["publication_status"] == "candidate_only"
    assert [c["fingerprint"] for c in body["candidates"]] == [
        first.fingerprint,
        second.fingerprint,
    ]
    assert body["candidates"][0]["command_ids"] == []
    assert body["candidates"][1]["command_ids"] == ["command"]
    detail = client.get(PREFIX + "/1/1")
    assert detail.json() == body["candidates"][1]
    assert detail.json()["snapshot"]["rows"][0]["points"] == 120
    assert (
        detail.json()["snapshot"]["rows"][0]["counted_results"][0]["edition_id"]
        == "edition"
    )
    assert dump(path) == before


def test_missing_scope_empty_history_and_invalid_week(api):
    client = api[0]
    assert client.get(PREFIX.replace("/run/", "/other-run/")).status_code == 404
    empty = client.get(PREFIX.replace("/branch/", "/empty/"))
    assert empty.status_code == 200 and empty.json()["candidates"] == []
    assert client.get(PREFIX + "/0/1").status_code == 404
    assert client.get(PREFIX + "/50/1").status_code == 422
    assert client.get(PREFIX + "/0/62").status_code == 422
    assert client.post(PREFIX, json={}).status_code == 405
    assert client.get(PREFIX.replace("/admin", "/viewer")).status_code == 404


@pytest.mark.parametrize("damage", ["payload", "receipt", "tail", "fork"])
def test_corruption_or_unsupported_ancestry_returns_conflict(api, damage):
    client, factory, path, _, _ = api
    with factory.begin() as session:
        row = session.get(OfficialRankingCandidateModel, ("run", "branch", 61))
        if damage == "payload":
            row.payload_json = "{}"
        elif damage == "receipt":
            session.get(
                OfficialRankingCommandModel, ("run", "branch", "command")
            ).snapshot_fingerprint = "0" * 64
        elif damage == "tail":
            session.delete(row)
        else:
            session.get(RunBranchModel, "branch").forked_from_branch_id = "empty"
    before = dump(path)
    for suffix in ("", "/0/61"):
        response = client.get(PREFIX + suffix)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ranking_history_unavailable"
    assert dump(path) == before


@pytest.fixture
def source_api(api):
    from beta_engine.domain.rankings.result_history import RankingResultVersion
    from beta_engine.infrastructure.db.models import OfficialRankingResultVersionModel

    client, factory, path, first, second = api
    result = first.rows[0].counted_results[0]
    initial = RankingResultVersion(
        run_id="run", branch_id="branch", effective_week=first.week,
        previous_fingerprint=None, result=result,
    )
    # An unranked result is available input but is never counted.
    uncounted = initial.model_copy(update={"result": result.model_copy(update={
        "edition_id": "unranked", "ranked": False,
    })})
    future = initial.model_copy(update={
        "effective_week": RankingWeek(season_index=1, week=2),
        "previous_fingerprint": initial.fingerprint,
        "result": result.model_copy(update={"main_points": 999, "source_fingerprint": "future-only"}),
    })
    with factory.begin() as session:
        for v in (initial, uncounted, future):
            session.add(OfficialRankingResultVersionModel(
                run_id=v.run_id, branch_id=v.branch_id, edition_id=v.result.edition_id,
                player_id=v.result.player_id, effective_ordinal=v.effective_week.ordinal,
                fingerprint=v.fingerprint, payload_json=v.model_dump_json(),
            ))
    return api, initial, uncounted


@pytest.mark.smoke
def test_sources_are_historical_scoped_and_read_only(source_api):
    (client, factory, path, first, second), initial, uncounted = source_api
    before = dump(path)
    response = client.get(PREFIX + "/1/1/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_fingerprint"] == second.fingerprint
    assert [(s["fingerprint"], s["counted"]) for s in data["sources"]] == [
        (initial.fingerprint, True), (uncounted.fingerprint, False),
    ]
    assert "future-only" not in str(data)
    assert client.get(PREFIX + "/1/2/sources").status_code == 404
    assert client.get(PREFIX.replace("/runs/run/", "/runs/other-run/") + "/1/1/sources").status_code == 404
    assert client.get(PREFIX + "/50/1/sources").status_code == 422
    assert dump(path) == before


@pytest.mark.smoke
def test_sources_reject_missing_counted_history(api):
    client, _, path, _, _ = api
    before = dump(path)
    response = client.get(PREFIX + "/1/1/sources")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ranking_sources_unavailable"
    assert dump(path) == before


def test_sources_reject_corrupt_history(source_api):
    from beta_engine.infrastructure.db.models import OfficialRankingResultVersionModel

    (client, factory, path, _, _), initial, _ = source_api
    with factory.begin() as session:
        session.get(OfficialRankingResultVersionModel, (
            "run", "branch", initial.result.edition_id, initial.result.player_id, initial.effective_week.ordinal,
        )).fingerprint = "0" * 64
    before = dump(path)
    assert client.get(PREFIX + "/1/1/sources").status_code == 409
    assert dump(path) == before


def test_sources_select_correction_at_its_effective_boundary(source_api):
    (client, factory, _, _, second), initial, _ = source_api
    corrected = initial.result.model_copy(update={"main_points": 999, "source_fingerprint": "future-only"})
    with factory.begin() as session:
        third = calculate_official_ranking(
            run_id="run", branch_id="branch", week=RankingWeek(season_index=1, week=2),
            policy=second.policy,
            players=(OfficialRankingPlayer(player_id="p", tie_break_token="token", tour_entry_week=RankingWeek(season_index=0, week=1)),),
            results=(corrected,), previous=second,
        )
        OfficialRankingCandidateStore(session).append(third)
    newer = client.get(PREFIX + "/1/2/sources")
    assert newer.status_code == 200
    source = newer.json()["sources"][0]
    assert source["version"]["previous_fingerprint"] == initial.fingerprint
    assert source["version"]["result"]["main_points"] == 999
    assert source["counted"] is True
    older = client.get(PREFIX + "/1/1/sources")
    assert older.json()["sources"][0]["version"]["result"]["main_points"] == 120


@pytest.mark.smoke
def test_corrupt_future_source_error_does_not_expose_future_payload(source_api):
    from beta_engine.infrastructure.db.models import OfficialRankingResultVersionModel

    (client, factory, _, _, _), initial, _ = source_api
    with factory.begin() as session:
        session.get(OfficialRankingResultVersionModel, (
            "run", "branch", initial.result.edition_id, initial.result.player_id, 62,
        )).payload_json = '{"future_secret": "not-yet-known"}'
    response = client.get(PREFIX + "/1/1/sources")
    assert response.status_code == 409
    assert response.json()["detail"]["message"] == "Stored ranking sources could not be verified."
    assert "not-yet-known" not in str(response.json())
