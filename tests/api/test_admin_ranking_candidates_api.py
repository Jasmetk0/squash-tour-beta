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
