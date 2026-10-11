"""Canonical Players read projection: saved-only, paged, no fabricated sporting fields."""
from types import SimpleNamespace

import pytest

from beta_engine.application.saved_players_inventory import resolve_saved_players_inventory
import beta_engine.application.saved_players_inventory as inventory


pytestmark = pytest.mark.pr_critical


def _source(run="run-a", rows=()):
    return SimpleNamespace(run_id=run, records=tuple(rows))


def _world(run="run-a", branch="branch-a", rows=()):
    return SimpleNamespace(run_id=run, branch_id=branch, players=tuple(rows))


def _player(pid, name, country="CZE", status="active"):
    return SimpleNamespace(player_id=pid, name=name, country_code=country, active_status=status)


def _query(**kwargs):
    return resolve_saved_players_inventory(
        run_id="run-a", branch_id="branch-a", saved_revision_id="revision-a",
        **kwargs,
    )


def test_large_saved_roster_paginates_with_exact_total():
    players = [_player(f"p-{i:04d}", f"Player {i:04d}") for i in range(1050)]
    response = _query(initial_world=_world(rows=players), prospect_source=None,
                      ranking=None, offset=1000, limit=100)
    assert response.total == 1050
    assert len(response.players) == 50
    assert response.has_more is False
    assert response.players[0].player_id == "p-1000"
    assert response.saved_revision_id == "revision-a"
    assert all(p.age is None and p.ovr is None and p.potential_ovr is None for p in response.players)
    assert all(p.rank is None and p.ranking_status == "unpublished" for p in response.players)


def test_filters_and_shared_source_are_restricted_to_saved_records():
    rows = [
        {"prospect_id": "future1", "display_name": "Cyril Prospect", "country_code": "SVK", "status": "prepared"},
        {"prospect_id": "future2", "display_name": "Alex Prospect", "country_code": "CZE", "status": "active"},
    ]
    result = _query(
        initial_world=_world(rows=[_player("first", "Adam Current"), _player("second", "Adam Retired", status="retired")]),
        prospect_source=_source(rows=rows), ranking=None,
        search="Prospect", country_code="SVK", status_filter="prepared",
    )
    assert [p.player_id for p in result.players] == ["future1"]
    assert result.players[0].identity_source == "run_prospect"
    assert result.players[0].status == "prepared"
    assert result.total == 1


def test_duplicate_identity_and_cross_branch_fail_closed():
    rows=[{"prospect_id":"p1","display_name":"Conflict","country_code":"CZE","status":"prepared"}]
    with pytest.raises(ValueError, match="Duplicate"):
        _query(initial_world=_world(rows=[_player("p1","Existing")]), prospect_source=_source(rows=rows), ranking=None)
    with pytest.raises(ValueError, match="another Branch"):
        _query(initial_world=_world(branch="foreign"), prospect_source=None, ranking=None)
    with pytest.raises(ValueError, match="another Run"):
        _query(initial_world=None, prospect_source=_source(run="foreign"), ranking=None)


def test_ranked_only_after_verifiable_published_head(monkeypatch):
    ranking = SimpleNamespace(run_id="run-a", branch_id="branch-a",
                              authoritative_transition_state={"world":{"current_ordinal":11}})
    monkeypatch.setattr(inventory, "resolve_viewer_official_ranking", lambda _state: SimpleNamespace(
        product_run_id="run-a", viewer_branch_id="branch-a", week_ordinal=11,
        rows=[SimpleNamespace(player_id="p1", rank=7)]
    ))
    result = _query(
        initial_world=_world(rows=[_player("p1","Published"),_player("p2","Not ranked")]),
        prospect_source=None, ranking=ranking,
    )
    assert result.ranking_week_ordinal == 11
    assert [(p.player_id, p.rank, p.ranking_status) for p in result.players] == [
        ("p2", None, "unranked"), ("p1", 7, "ranked")
    ]
    monkeypatch.setattr(inventory, "resolve_viewer_official_ranking", lambda _state: SimpleNamespace(
        product_run_id="run-a", viewer_branch_id="foreign", week_ordinal=11, rows=[]
    ))
    with pytest.raises(ValueError, match="another Branch"):
        _query(initial_world=_world(), prospect_source=None, ranking=ranking)


def test_empty_saved_revision_does_not_fall_back_to_legacy_or_future_state():
    data = _query(initial_world=None, prospect_source=None, ranking=None)
    assert data.total == 0 and data.players == () and not data.has_more
    with pytest.raises(ValueError, match="page"):
        _query(initial_world=None, prospect_source=None, ranking=None, offset=-1)
