"""Authoritative Saved Revision weekly ranking comparison: no fabricated movement."""
from types import SimpleNamespace

import pytest

from beta_engine.application import run_home_ranking_changes as model


def _row(player: str, rank: int, points: int):
    return SimpleNamespace(player_id=player, rank=rank, points=points)


def _ranking_view(*, run="run", branch="branch", ordinal=1, rows=()):
    return SimpleNamespace(product_run_id=run, viewer_branch_id=branch,
                           week_ordinal=ordinal, row_count=len(rows), rows=tuple(rows))


def _state(*, run="run", branch="branch", ordinals=(0, 1), head=1):
    return SimpleNamespace(
        run_id=run, branch_id=branch,
        authoritative_transition_state={
            "world": {"current_ordinal": head},
            "publications": [{"week_ordinal": n} for n in ordinals],
        },
    )


@pytest.mark.pr_critical
def test_saved_week_delta_categorizes_moves_new_exits_and_points_only(monkeypatch):
    previous = _ranking_view(ordinal=0, rows=[
        _row("A", 1, 100), _row("B", 2, 90),
        _row("C", 3, 70), _row("D", 4, 40),
    ])
    current = _ranking_view(rows=[
        _row("B", 1, 115), _row("A", 2, 100),
        _row("C", 3, 80), _row("E", 4, 35),
    ])
    monkeypatch.setattr(model, "resolve_viewer_official_ranking", lambda _: current)
    monkeypatch.setattr(model, "resolve_viewer_official_ranking_at",
                        lambda _, *, week_ordinal: previous if week_ordinal == 0 else None)
    result = model.resolve_run_home_ranking_changes(
        run_id="run", branch_id="branch", saved_revision_id="saved-a", ranking=_state(),
    )
    assert result.status == "ready"
    assert (result.previous_week_ordinal, result.current_week_ordinal) == (0, 1)
    assert (result.moved_count, result.entered_count, result.exited_count,
            result.points_only_count, result.total_change_count) == (2, 1, 1, 1, 5)
    found = {change.player_id: change for change in result.changes}
    assert found["B"].movement == "up" and found["B"].rank_delta == 1
    assert found["B"].points_delta == 25
    assert found["A"].movement == "down" and found["A"].rank_delta == -1
    assert found["C"].movement == "points_only" and found["C"].points_delta == 10
    assert found["D"].movement == "exited" and found["D"].previous_rank == 4
    assert found["D"].current_rank is None and found["D"].rank_delta is None
    assert found["E"].movement == "entered" and found["E"].previous_rank is None
    assert found["E"].points_delta is None
    assert list(found)[0] == "B"


@pytest.mark.pr_critical
def test_unpublished_initial_no_motion_and_inconsistent_week_boundaries(monkeypatch):
    unpub = model.resolve_run_home_ranking_changes(
        run_id="run", branch_id="branch", saved_revision_id="rev-0", ranking=None,
    )
    assert unpub.status == "unpublished" and unpub.current_row_count is None
    assert unpub.changes == () and unpub.total_change_count == 0
    first = _ranking_view(ordinal=42, rows=[_row("A", 1, 0)])
    monkeypatch.setattr(model, "resolve_viewer_official_ranking", lambda _: first)
    initial = model.resolve_run_home_ranking_changes(
        run_id="run", branch_id="branch", saved_revision_id="rev-1",
        ranking=_state(ordinals=(42,), head=42),
    )
    assert initial.status == "first_publication" and initial.previous_week_ordinal is None
    assert initial.current_week_ordinal == 42
    monkeypatch.setattr(model, "resolve_viewer_official_ranking_at",
                        lambda _, *, week_ordinal: _ranking_view(ordinal=41, rows=[_row("A", 1, 0)]))
    same = model.resolve_run_home_ranking_changes(
        run_id="run", branch_id="branch", saved_revision_id="rev-2",
        ranking=_state(ordinals=(41, 42), head=42),
    )
    assert same.status == "ready" and same.total_change_count == 0
    with pytest.raises(ValueError, match="nonconsecutive"):
        model.resolve_run_home_ranking_changes(
            run_id="run", branch_id="branch", saved_revision_id="rev-2",
            ranking=_state(ordinals=(40, 42), head=42),
        )


@pytest.mark.pr_critical
def test_ranking_read_refuses_foreign_branch_duplicate_players_and_future(monkeypatch):
    previous = _ranking_view(ordinal=0, rows=[_row("A", 1, 1)])
    current = _ranking_view(rows=[_row("A", 1, 2), _row("A", 2, 3)])
    monkeypatch.setattr(model, "resolve_viewer_official_ranking", lambda _: current)
    monkeypatch.setattr(model, "resolve_viewer_official_ranking_at", lambda _, *, week_ordinal: previous)
    with pytest.raises(ValueError, match="duplicate"):
        model.resolve_run_home_ranking_changes(
            run_id="run", branch_id="branch", saved_revision_id="saved",
            ranking=_state(),
        )
    with pytest.raises(ValueError, match="another Run / Branch"):
        model.resolve_run_home_ranking_changes(
            run_id="run", branch_id="foreign", saved_revision_id="saved",
            ranking=_state(),
        )
    # A future live publication cannot replace the saved world head.
    monkeypatch.setattr(model, "resolve_viewer_official_ranking",
                        lambda _: _ranking_view(ordinal=0, rows=[_row("A", 1, 1)]))
    before = model.resolve_run_home_ranking_changes(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        ranking=_state(ordinals=(0, 1), head=0),
    )
    assert before.status == "first_publication" and before.current_week_ordinal == 0
