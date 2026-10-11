"""Saved canonical match detail never borrows live/foreign replay evidence."""
from types import SimpleNamespace

import pytest

from beta_engine.application import saved_player_match_detail as detail
from beta_engine.application.run_home_player_identity import (
    SavedHomePlayerIdentity, SavedHomePlayerIdentities,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.infrastructure.db.authoritative_group_state import AuthoritativeGroupResult
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_viewer_tournament_result_read_model import _source

pytestmark = pytest.mark.pr_critical


def identities(player_id="A"):
    return SavedHomePlayerIdentities(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        status="ready", requested_ids=(player_id,), unresolved_ids=(),
        players=(SavedHomePlayerIdentity(
            player_id=player_id, display_name="Saved Name",
            country_code="CZE", identity_source="initial_world",
        ),),
    )


def ranking():
    return RankingRevisionState(
        run_id="run", branch_id="branch", entries=(), sources=(),
        tournament_sources=(_source(),),
    )


def get(*, player_id="A", event_id="event", match_id="final", slots=None,
        offset=0, limit=25, rank=None, packages=None, ids=None, revision="saved"):
    return detail.resolve_saved_player_match_detail(
        run_id="run", branch_id="branch", saved_revision_id=revision,
        player_id=player_id, event_id=event_id, match_id=match_id,
        identities=ids or identities(player_id),
        ranking=rank if rank is not None else ranking(),
        packages=packages if packages is not None else _state(),
        saved_slots=slots, offset=offset, limit=limit,
    )


def test_published_match_detail_without_archived_replay_is_explicit():
    value = get()
    assert value.match.event_name == "Current Open"
    assert (value.match.season_index, value.match.week) == (2, 17)
    assert (value.winner_player_id, value.loser_player_id) == ("A", "B")
    assert value.replay_status == "unavailable"
    assert value.total_rallies == 0 and value.rallies == ()
    assert "result_fingerprint" not in value.model_dump_json()


def test_missing_player_match_and_foreign_revision_fail_closed():
    with pytest.raises(KeyError, match="did not participate"):
        get(player_id="D")
    with pytest.raises(KeyError, match="no published"):
        get(event_id="EVENT-OLD")
    with pytest.raises(KeyError, match="does not exist"):
        get(match_id="missing")
    with pytest.raises(ValueError, match="Branch HEAD"):
        get(revision="other")
    foreign = _state(run_id="run", branch_id="foreign")
    with pytest.raises(ValueError, match="foreign Branch"):
        get(packages=foreign)
    for kwargs in ({"offset": -1}, {"limit": 26}):
        with pytest.raises(ValueError):
            get(**kwargs)


def _fake_competitive_match(*, winner="A", event_id="event", count=3):
    before = lambda n: SimpleNamespace(points_a=n, points_b=0)
    after = lambda n: SimpleNamespace(points_a=n + 1, points_b=0, sets_a=0, sets_b=0)
    events = tuple(SimpleNamespace(
        rally_index=n + 1, set_number=1, serving_player_id="A",
        winner_player_id="A", score_before=before(n), score_after=after(n),
        post_rally_state=SimpleNamespace(set_complete=False, match_complete=False),
    ) for n in range(count))
    return AuthoritativeGroupResult(
        authoritative_input=SimpleNamespace(
            run_id="run", branch_id="branch", week=RankingWeek(season_index=2, week=17),
            event_id=event_id, match_id="final",
        ),
        result=SimpleNamespace(
            match_id="final", winner_player_id=winner, loser_player_id="B",
            player_a_id="A", player_b_id="B",
            rally_log=SimpleNamespace(match_id="final", total_rallies=count, events=events),
        ),
        result_fingerprint="validated", effects=(), terminal_checkpoint=None,
    )


def test_saved_verified_rally_frames_use_bounded_cursor(monkeypatch):
    fake = _fake_competitive_match()
    monkeypatch.setattr(detail, "load_authoritative_group", lambda row: fake)
    slots = {"groups": [{"match_id": "final", "week_ordinal": 2 * 61 + 16}]}
    first = get(slots=slots, limit=2)
    assert first.replay_status == "available"
    assert first.total_rallies == 3 and first.has_more
    assert first.player_a_id == "A" and first.player_b_id == "B"
    assert [(r.rally_index, r.score_a_after, r.score_b_after) for r in first.rallies] == [
        (1, 1, 0), (2, 2, 0),
    ]
    last = get(slots=slots, offset=2, limit=2)
    assert len(last.rallies) == 1 and last.rallies[0].rally_index == 3
    assert not last.has_more
    assert "rally_seed" not in last.model_dump_json()
    assert "event_hash" not in last.model_dump_json()


def test_replay_wrong_winner_duplicate_or_foreign_event_is_rejected(monkeypatch):
    slots = {"groups": [{"match_id": "final", "week_ordinal": 2 * 61 + 16}]}
    monkeypatch.setattr(detail, "load_authoritative_group",
                        lambda row: _fake_competitive_match(winner="B"))
    with pytest.raises(ValueError, match="contradicts canonical"):
        get(slots=slots)
    monkeypatch.setattr(detail, "load_authoritative_group",
                        lambda row: _fake_competitive_match(event_id="different"))
    assert get(slots=slots).replay_status == "unavailable"
    monkeypatch.setattr(detail, "load_authoritative_group",
                        lambda row: _fake_competitive_match())
    with pytest.raises(ValueError, match="Multiple saved"):
        get(slots={"groups": slots["groups"] * 2})

def test_saved_replay_rejects_unremapped_group_from_source_branch(monkeypatch):
    """A future materialized fork must not borrow its parent's raw slot group."""
    slots = {"groups": [{"match_id": "final", "week_ordinal": 2 * 61 + 16}]}
    foreign = _fake_competitive_match()
    foreign.authoritative_input.branch_id = "source-branch"
    monkeypatch.setattr(detail, "load_authoritative_group", lambda row: foreign)
    with pytest.raises(ValueError, match="contradicts canonical"):
        get(slots=slots)


