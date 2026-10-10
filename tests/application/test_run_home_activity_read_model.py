"""Pure read projection tests for canonical week ordering and non-fabrication."""

from types import SimpleNamespace

import pytest

from beta_engine.application.run_home_activity_read_model import (
    resolve_run_home_activity,
)
from beta_engine.domain.run_packages import RunPackageState


def _item(event_id: str, season: str, week: int, published: bool = False):
    return SimpleNamespace(
        event_id=event_id,
        event_name="Real saved event " + event_id,
        season=season,
        season_week=week,
        category="PLATINUM",
        ranking_status="planned",
        result_published=published,
        champion_player_id="champion" if published else None,
        finalist_player_id="finalist" if published else None,
    )


@pytest.mark.pr_critical
def test_home_orders_saved_future_events_and_published_results_without_legacy_state(monkeypatch):
    from beta_engine.application import run_home_activity_read_model as model

    history = SimpleNamespace(
        tournaments=(
            _item("later", "2001/2002", 5),
            _item("past", "2000/2001", 1, published=True),
            _item("current", "2000/2001", 10),
            _item("before", "2000/2001", 9),
        ),
        published_result_count=1,
    )
    monkeypatch.setattr(model, "resolve_viewer_tournament_history", lambda **_kwargs: history)
    data = resolve_run_home_activity(
        run_id="run-a", branch_id="branch-a", saved_revision_id="rev-a",
        packages=RunPackageState(run_id="run-a", branch_id="branch-a"),
        ranking=None, current_season=0, current_week=10,
    )
    assert data.calendar_status == "ready"
    assert [row.event_id for row in data.upcoming] == ["current", "later"]
    assert [row.event_id for row in data.recent_results] == ["past"]
    assert data.recent_results[0].champion_player_id == "champion"
    assert data.saved_revision_id == "rev-a"
    assert data.ranking_changes_status == "unsupported"


@pytest.mark.pr_critical
def test_home_does_not_classify_future_without_position(monkeypatch):
    from beta_engine.application import run_home_activity_read_model as model

    monkeypatch.setattr(
        model, "resolve_viewer_tournament_history",
        lambda **_kwargs: SimpleNamespace(
            tournaments=(_item("event", "2000/2001", 1),),
            published_result_count=0,
        ),
    )
    data = resolve_run_home_activity(
        run_id="r", branch_id="b", saved_revision_id="s",
        packages=RunPackageState(run_id="r", branch_id="b"),
        ranking=None, current_season=None, current_week=None,
    )
    assert data.calendar_status == "unpositioned"
    assert data.total_calendar_events == 1
    assert data.upcoming == ()
    with pytest.raises(ValueError, match="canonical Season Weeks"):
        resolve_run_home_activity(
            run_id="r", branch_id="b", saved_revision_id="s",
            packages=RunPackageState(run_id="r", branch_id="b"),
            ranking=None, current_season=0, current_week=62,
        )


@pytest.mark.pr_critical
def test_home_rejects_cross_branch_package_state_without_masking_as_empty():
    with pytest.raises(ValueError, match="identity"):
        resolve_run_home_activity(
            run_id="r", branch_id="other", saved_revision_id="s",
            packages=RunPackageState(run_id="r", branch_id="b"),
            ranking=None, current_season=0, current_week=1,
        )
