"""Saved player profile boundaries: verified identity, publication and ownership."""
from types import SimpleNamespace

import pytest

from beta_engine.application.run_home_player_identity import resolve_saved_home_player_identities
from beta_engine.application import saved_player_profile as profile
from tests.application.test_viewer_people_read_model import _world


def identities(player_id="P1"):
    return resolve_saved_home_player_identities(
        run_id="run", branch_id="branch", saved_revision_id="revision",
        requested_ids=(player_id,), initial_world=_world(), prospect_source=None,
    )


def resolve(*, player_id="P1", ranking=None, packages=None, saved_revision_id="revision"):
    return profile.resolve_saved_player_profile(
        run_id="run", branch_id="branch", saved_revision_id=saved_revision_id,
        player_id=player_id, identities=identities(player_id),
        ranking=ranking, packages=packages,
    )


@pytest.mark.pr_critical
def test_empty_profile_and_unresolved_player_never_invent_history():
    first = resolve()
    assert first.identity.display_name == "Initial One"
    assert first.ranking_status == "unpublished"
    assert (first.rank, first.points, first.final_appearances) == (None, None, 0)
    assert first.tournament_results == ()
    unknown = resolve(player_id="NO-ONE")
    assert unknown.identity is None
    assert unknown.ranking_status == "identity_unavailable"
    assert unknown.rank is None and unknown.tournament_results == ()


@pytest.mark.pr_critical
def test_current_published_rank_and_real_tournament_finishes_are_bounded(monkeypatch):
    ranking = SimpleNamespace(
        run_id="run", branch_id="branch", tournament_sources=(),
        authoritative_transition_state={"world": {"current_ordinal": 7}, "publications": []},
    )
    packages = SimpleNamespace(run_id="run", branch_id="branch")
    monkeypatch.setattr(profile, "resolve_viewer_official_ranking", lambda _: SimpleNamespace(
        product_run_id="run", viewer_branch_id="branch", week_ordinal=7,
        rows=(SimpleNamespace(player_id="P1", rank=2, points=130),
              SimpleNamespace(player_id="P2", rank=1, points=200)),
    ))
    tournament = lambda event, week, champ, runner, published=True: SimpleNamespace(
        event_id=event, event_name=event, season="2000/01", season_week=week,
        result_published=published, champion_player_id=champ, finalist_player_id=runner,
    )
    monkeypatch.setattr(profile, "resolve_viewer_tournament_history", lambda **kwargs: SimpleNamespace(
        product_run_id="run", viewer_branch_id="branch", tournaments=(
            tournament("A", 1, "P1", "P2"), tournament("B", 2, "P2", "P1"),
            tournament("C", 3, "P1", "P2", False),
        ),
    ))
    result = resolve(ranking=ranking, packages=packages)
    assert result.ranking_status == "ranked"
    assert (result.rank, result.points, result.ranking_week_ordinal) == (2, 130, 7)
    assert (result.titles, result.final_appearances, result.total_tournament_results) == (1, 2, 2)
    assert [(row.event_id, row.finish) for row in result.tournament_results] == [
        ("B", "runner_up"), ("A", "champion"),
    ]
    assert "potential" not in result.model_dump_json()


@pytest.mark.pr_critical
def test_rejects_cross_branch_ranking_packages_and_stale_identity():
    foreign_rank = SimpleNamespace(run_id="run", branch_id="foreign")
    with pytest.raises(ValueError, match="another Run/Branch"):
        resolve(ranking=foreign_rank)
    foreign_calendar = SimpleNamespace(run_id="foreign", branch_id="branch")
    with pytest.raises(ValueError, match="another Run/Branch"):
        resolve(packages=foreign_calendar)
    with pytest.raises(ValueError, match="selected Branch HEAD"):
        resolve(saved_revision_id="stale")
