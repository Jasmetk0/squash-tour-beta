"""Player timeline uses frozen canonical Tournament Result match rows, not live slots."""
from types import SimpleNamespace

import pytest

from beta_engine.application import saved_player_match_history as history
from beta_engine.application.run_home_player_identity import (
    SavedHomePlayerIdentities, SavedHomePlayerIdentity,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from tests.application.test_viewer_tournament_result_read_model import _source

pytestmark = pytest.mark.pr_critical


def ids(player="A"):
    return SavedHomePlayerIdentities(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        status="ready", requested_ids=(player,), unresolved_ids=(),
        players=(SavedHomePlayerIdentity(
            player_id=player, display_name="Saved player",
            country_code="CZE", identity_source="initial_world",
        ),),
    )


def get(*, player="A", ranking=None, packages=None, season_index=None, offset=0, limit=20, identities=None):
    return history.resolve_saved_player_match_history(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        player_id=player, identities=identities or ids(player),
        ranking=ranking, packages=packages, season_index=season_index,
        offset=offset, limit=limit,
    )


def source_context(monkeypatch):
    ranking = RankingRevisionState(
        run_id="run", branch_id="branch", entries=(), sources=(),
        tournament_sources=(_source(),),
    )
    packages = SimpleNamespace(run_id="run", branch_id="branch")
    event = SimpleNamespace(
        event_id="event", event_name="Test Championship", season="2002/03",
        season_week=17, result_published=True,
    )
    monkeypatch.setattr(history, "resolve_viewer_tournament_history",
        lambda **kwargs: SimpleNamespace(
            product_run_id="run", viewer_branch_id="branch", tournaments=(event,),
        ))
    return ranking, packages


def test_pure_saved_match_history_counts_real_canonical_qualification_and_main(monkeypatch):
    ranking, packages = source_context(monkeypatch)
    a = get(ranking=ranking, packages=packages)
    assert a.status == "ready" and a.available_seasons == (2,)
    assert a.career_played_wins == 2 and a.career_played_losses == 0
    assert (a.total_results, a.played_wins, a.played_losses, a.walkovers) == (2, 2, 0, 0)
    assert [(row.match_id, row.opponent_player_id, row.scoreline) for row in a.matches] == [
        ("final", "B", "3-2"), ("semi-a", "Q", "3-0"),
    ]
    assert "result_fingerprint" not in a.model_dump_json()
    assert "potential" not in a.model_dump_json()
    b = get(player="B", ranking=ranking, packages=packages)
    assert (b.played_wins, b.played_losses) == (1, 1)
    assert [row.outcome for row in b.matches] == ["loss", "win"]
    q = get(player="Q", ranking=ranking, packages=packages)
    assert (q.played_wins, q.played_losses) == (1, 1)
    assert {row.draw_type for row in q.matches} == {"qualification", "main"}


def test_season_selection_and_paging_never_fabricate_matches(monkeypatch):
    ranking, packages = source_context(monkeypatch)
    first = get(ranking=ranking, packages=packages, limit=1)
    assert first.has_more and len(first.matches) == 1
    second = get(ranking=ranking, packages=packages, limit=1, offset=1)
    assert not second.has_more and len(second.matches) == 1
    assert second.matches[0].match_id != first.matches[0].match_id
    missing = get(ranking=ranking, packages=packages, season_index=0)
    assert missing.total_results == 0 and missing.available_seasons == (2,)
    assert (missing.career_played_wins, missing.played_wins) == (2, 0)
    for kwargs in ({"limit": 21}, {"offset": -1}, {"season_index": 50}):
        with pytest.raises(ValueError):
            get(ranking=ranking, packages=packages, **kwargs)


def test_unavailable_identity_and_foreign_or_corrupt_sources_fail_closed(monkeypatch):
    empty = SavedHomePlayerIdentities(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        status="unavailable", requested_ids=("MISSING",),
        players=(), unresolved_ids=("MISSING",),
    )
    no_player = get(player="MISSING", identities=empty)
    assert no_player.status == "identity_unavailable"
    assert no_player.matches == () and no_player.total_results == 0
    with pytest.raises(ValueError, match="Saved Branch HEAD"):
        history.resolve_saved_player_match_history(
            run_id="run", branch_id="branch", saved_revision_id="different",
            player_id="A", identities=ids(), ranking=None, packages=None,
        )
    with pytest.raises(ValueError, match="Saved ranking"):
        get(ranking=SimpleNamespace(run_id="run", branch_id="wrong"))
    with pytest.raises(ValueError, match="Saved Calendar"):
        get(packages=SimpleNamespace(run_id="wrong", branch_id="branch"))
    ranking, packages = source_context(monkeypatch)
    monkeypatch.setattr(history, "resolve_viewer_tournament_history",
        lambda **kwargs: SimpleNamespace(
            product_run_id="run", viewer_branch_id="branch",
            tournaments=(SimpleNamespace(
                event_id="event", event_name="Test Championship",
                season="2002/03", season_week=16, result_published=True,
            ),),
        ))
    with pytest.raises(ValueError, match="Calendar timing"):
        get(ranking=ranking, packages=packages)


def test_walkover_not_counted_as_played_and_bye_not_counted(monkeypatch):
    ranking, packages = source_context(monkeypatch)
    real = history.resolve_viewer_tournament_result(
        ranking, run_id="run", branch_id="branch", event_id="event",
    )
    # Isolate the projection behavior without changing real saved result authority.
    fake = real.model_copy(update={"matches": real.matches + (
        real.matches[0].model_copy(update={
            "match_id": "walkover", "winner_player_id": "A",
            "loser_player_id": "B", "scoreline": "W/O",
        }),
        real.matches[0].model_copy(update={
            "match_id": "bye", "winner_player_id": "A",
            "loser_player_id": None, "scoreline": "BYE",
        }),
    )})
    monkeypatch.setattr(history, "resolve_viewer_tournament_result", lambda *args, **kw: fake)
    result = get(ranking=ranking, packages=packages)
    assert (result.played_wins, result.played_losses, result.walkovers) == (2, 0, 1)
    assert result.total_results == 3
    assert any(row.completion == "walkover" for row in result.matches)
    assert all(row.match_id != "bye" for row in result.matches)
