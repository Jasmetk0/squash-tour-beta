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


@pytest.fixture
def input_api(api):
    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.application.ranking_week_command import RankingWeekCommand
    from beta_engine.application.official_ranking_transition import RankingTransitionContext
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner

    client, factory, path, _, _ = api
    runner = RankingWeekCommandRunner(factory)
    player = OfficialRankingPlayer(player_id="nr-player", tie_break_token="frozen-token", tour_entry_week=RankingWeek(season_index=0, week=1))
    first = runner.execute(RankingBootstrapCommand(
        command_id="bootstrap", run_id="run", branch_id="empty", policy=OfficialRankingPolicy(policy_id="policy"), players=(player,), discipline="none",
    ))
    runner.execute(RankingWeekCommand(
        command_id="later", tournaments=(), context=RankingTransitionContext(
            run_id="run", branch_id="empty", completed_week=first.week, target_week=RankingWeek(season_index=0, week=2),
            policy=first.policy, players=(player.model_copy(update={"retired": True}),), discipline="none",
        ),
    ))
    return client, factory, path, first


@pytest.mark.smoke
def test_inputs_return_frozen_nr_roster_without_later_lifecycle_changes(input_api):
    client, factory, path, first = input_api
    with factory.begin() as session:
        session.get(RunBranchModel, "empty").read_only = True
    before = dump(path)
    prefix = PREFIX.replace("/branches/branch/", "/branches/empty/")
    data = client.get(prefix + "/0/1/inputs")
    assert data.status_code == 200
    data = data.json()
    assert data["verification_status"] == "complete_manifest"
    assert data["candidate_fingerprint"] == first.fingerprint
    assert first.rows == ()
    assert data["manifest"]["players"][0]["player_id"] == "nr-player"
    assert data["manifest"]["players"][0]["tie_break_token"] == "frozen-token"
    assert data["manifest"]["players"][0]["retired"] is False
    assert client.get(prefix + "/0/2/inputs").json()["manifest"]["players"][0]["retired"] is True
    assert client.get(prefix + "/0/3/inputs").status_code == 404
    assert client.get(prefix.replace("/runs/run/", "/runs/other-run/") + "/0/1/inputs").status_code == 404
    assert client.get(prefix + "/50/1/inputs").status_code == 422
    assert dump(path) == before


@pytest.mark.smoke
def test_legacy_inputs_are_explicitly_unavailable_without_fabrication(api):
    client, _, path, _, _ = api
    before = dump(path)
    response = client.get(PREFIX + "/1/1/inputs")
    assert response.status_code == 200
    assert response.json()["verification_status"] == "legacy_without_manifest"
    assert response.json()["manifest"] is None
    assert dump(path) == before


@pytest.mark.smoke
def test_damaged_inputs_fail_closed_without_returning_payload(input_api):
    client, factory, path, _ = input_api
    with factory.begin() as session:
        session.get(OfficialRankingCommandModel, ("run", "empty", "bootstrap")).input_manifest_json = '{"secret": "hidden-input"}'
    before = dump(path)
    response = client.get(PREFIX.replace("/branches/branch/", "/branches/empty/") + "/0/1/inputs")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ranking_inputs_unavailable"
    assert "hidden-input" not in str(response.json())
    assert dump(path) == before


@pytest.mark.smoke
def test_tie_explanation_uses_verified_historical_tokens_without_writes(api):
    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.application.ranking_week_command import RankingWeekCommand
    from beta_engine.application.official_ranking_transition import RankingTransitionContext
    from beta_engine.domain.rankings.official import OfficialRankingPlayer, OfficialRankingPolicy, RankingWeek
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
    client, factory, path, _, _ = api
    players = tuple(OfficialRankingPlayer(player_id=p, tie_break_token=t, tour_entry_week=RankingWeek(season_index=0, week=1)) for p,t in [('a','second'),('b','first')])
    runner = RankingWeekCommandRunner(factory)
    first = runner.execute(RankingBootstrapCommand(command_id='ties-bootstrap',run_id='run',branch_id='empty',policy=OfficialRankingPolicy(policy_id='ties-policy'),players=players,discipline='none'))
    second = runner.execute(RankingWeekCommand(command_id='ties-week2',tournaments=(),context=RankingTransitionContext(
        run_id='run',branch_id='empty',completed_week=first.week,target_week=RankingWeek(season_index=0,week=2),policy=first.policy,players=players,discipline='none',
    )))
    before = dump(path)
    response = client.get(PREFIX.replace('/branches/branch/','/branches/empty/')+'/0/2/inputs')
    assert response.status_code == 200
    data=response.json()
    assert data['candidate_fingerprint']==second.fingerprint
    assert data['tie_explanations']==[dict(higher_player_id='b',lower_player_id='a',higher_rank=1,lower_rank=2,points=0,reason='stored_token',result_slot=None,higher_value='first',lower_value='second')]
    assert dump(path)==before


@pytest.fixture
def zero_input_api(api):
    from sqlalchemy import text
    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.application.ranking_week_command import RankingWeekCommand
    from beta_engine.application.official_ranking_transition import RankingTransitionContext
    from beta_engine.domain.rankings.official import DisciplinaryZero
    from beta_engine.domain.rankings.zero_history import RankingZeroVersion
    from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner

    client, factory, path, _, _ = api
    week = lambda n: RankingWeek(season_index=0, week=n)
    initial = RankingZeroVersion(effective_week=week(1), previous_fingerprint=None,
        zero=DisciplinaryZero(zero_id='zero', run_id='run', branch_id='empty', player_id='p',
            source_fingerprint='initial-decision', effective_week=week(1), duration_weeks=4))
    correction = RankingZeroVersion(effective_week=week(2), previous_fingerprint=initial.fingerprint,
        zero=initial.zero.model_copy(update={'duration_weeks': 1, 'source_fingerprint': 'shortening'}))
    future = RankingZeroVersion(effective_week=week(3), previous_fingerprint=correction.fingerprint,
        zero=initial.zero.model_copy(update={'source_fingerprint': 'future-secret'}))
    active = RankingZeroVersion(effective_week=week(2), previous_fingerprint=None,
        zero=initial.zero.model_copy(update={'zero_id': 'active', 'effective_week': week(2)}))
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        for version in (initial, correction, future, active):
            OfficialRankingZeroStore(session).append(version)
    player = OfficialRankingPlayer(player_id='p', tie_break_token='token', tour_entry_week=week(1))
    runner = RankingWeekCommandRunner(factory)
    first = runner.execute(RankingBootstrapCommand(command_id='zero-first', run_id='run', branch_id='empty',
        policy=OfficialRankingPolicy(policy_id='policy'), players=(player,), discipline='stored_zeros'))
    runner.execute(RankingWeekCommand(command_id='zero-second', tournaments=(), context=RankingTransitionContext(
        run_id='run', branch_id='empty', completed_week=week(1), target_week=week(2), policy=first.policy,
        players=(player,), discipline='stored_zeros')))
    return client, factory, path, initial, correction, future


@pytest.mark.smoke
def test_zero_history_inspection_uses_candidate_boundary_without_writes(zero_input_api):
    client, factory, path, initial, correction, future = zero_input_api
    prefix = PREFIX.replace('/branches/branch/', '/branches/empty/')
    with factory.begin() as session:
        session.get(RunBranchModel, 'empty').read_only = True
    before = dump(path)
    earlier = client.get(prefix + '/0/1/inputs')
    assert earlier.status_code == 200
    assert earlier.json()['zero_history_status'] == 'verified_stored_history'
    assert earlier.json()['zero_sources'] == [dict(version=initial.model_dump(mode='json'),
        fingerprint=initial.fingerprint, impact='player_not_classified')]
    later = client.get(prefix + '/0/2/inputs')
    assert later.status_code == 200
    sources = later.json()['zero_sources']
    assert [s['impact'] for s in sources] == ['reserves_slot', 'superseded', 'expired']
    assert sources[-1]['fingerprint'] == correction.fingerprint
    assert sources[-1]['version']['previous_fingerprint'] == initial.fingerprint
    assert future.fingerprint not in str(later.json())
    assert 'future-secret' not in str(later.json())
    assert 'shortening' not in str(earlier.json())
    assert client.get(prefix.replace('/runs/run/', '/runs/other-run/') + '/0/2/inputs').status_code == 404
    assert dump(path) == before


@pytest.mark.smoke
@pytest.mark.parametrize('damage', ['missing', 'hash', 'future_payload'])
def test_zero_history_damage_fails_closed_without_leaking_payload(zero_input_api, damage):
    from sqlalchemy import delete
    from beta_engine.infrastructure.db.models import OfficialRankingZeroVersionModel
    client, factory, path, _, _, _ = zero_input_api
    with factory.begin() as session:
        if damage == 'missing':
            session.execute(delete(OfficialRankingZeroVersionModel))
        elif damage == 'hash':
            session.get(OfficialRankingZeroVersionModel, ('run', 'empty', 'zero', 0)).fingerprint = '0' * 64
        else:
            session.get(OfficialRankingZeroVersionModel, ('run', 'empty', 'zero', 2)).payload_json = '{"future_secret": "do-not-expose"}'
    before = dump(path)
    response = client.get(PREFIX.replace('/branches/branch/', '/branches/empty/') + '/0/2/inputs')
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'ranking_inputs_unavailable'
    assert 'do-not-expose' not in str(response.json())
    assert dump(path) == before


def test_caller_and_legacy_inputs_do_not_claim_zero_source_verification(input_api):
    client, _, _, _ = input_api
    response = client.get(PREFIX.replace('/branches/branch/', '/branches/empty/') + '/0/1/inputs').json()
    assert response['zero_history_status'] == 'caller_resolved'
    assert response['zero_sources'] == []
    legacy = client.get(PREFIX + '/1/1/inputs').json()
    assert legacy['zero_history_status'] == 'legacy_without_manifest'
    assert legacy['zero_sources'] == []
