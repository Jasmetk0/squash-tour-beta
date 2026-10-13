"""Country Records: exact source and nationality evidence; no invented winners."""
from types import SimpleNamespace
import pytest

from beta_engine.application import run_country_records_read_model as model
from tests.application.test_viewer_people_read_model import _world

pytestmark = pytest.mark.pr_critical


def edition(event_id, host, winner, finalist, published=True):
    return SimpleNamespace(
        event_id=event_id, event_name="Open "+event_id,
        season="2000/2001", season_week=6, host_country=host,
        result_published=published,
        champion_player_id=winner if published else None,
        finalist_player_id=finalist if published else None,
    )


def test_country_titles_and_hosted_results_are_distinct(monkeypatch):
    # P1 = CZE, P2 = EGY. A Czech host is NOT a Czech champion.
    history=SimpleNamespace(tournaments=(
        edition("away-title","EGY","P1","P2"),
        edition("home-foreign-title","CZE","P2","P1"),
        edition("planned","CZE",None,None,False),
    ))
    monkeypatch.setattr(model,"resolve_viewer_tournament_history",lambda **_kwargs:history)
    from beta_engine.domain.run_packages import RunPackageState
    result=model.resolve_run_country_records(
        run_id="run",selected_branch_id="fork",revision_branch_id="branch",
        saved_revision_id="rev-ancestor",country_code="CZE",
        packages=RunPackageState(run_id="run",branch_id="branch"),
        ranking=None,initial_world=_world(),prospect_source=None,
    )
    assert (result.published_result_count,result.country_titles,
            result.country_finalists,result.hosted_published_results)==(2,1,1,1)
    assert [x.event_id for x in result.hosted_results]==["home-foreign-title"]
    assert [x.event_id for x in result.player_results]==["away-title","home-foreign-title"]
    assert result.player_results[0].champion_name=="Initial One"
    assert result.player_results[0].champion_country=="CZE"
    assert result.revision_branch_id=="branch" and result.branch_id=="fork"
    assert all(x.event_id!="planned" for x in result.hosted_results)


def test_missing_published_participant_nationality_fails_closed(monkeypatch):
    monkeypatch.setattr(model,"resolve_viewer_tournament_history",lambda **_kwargs:
        SimpleNamespace(tournaments=(edition("event","CZE","UNKNOWN","P2"),)))
    from beta_engine.domain.run_packages import RunPackageState
    with pytest.raises(ValueError, match="no saved national identity"):
        model.resolve_run_country_records(
            run_id="run",selected_branch_id="branch",revision_branch_id="branch",
            saved_revision_id="rev",country_code="CZE",
            packages=RunPackageState(run_id="run",branch_id="branch"),
            ranking=None,initial_world=_world(),prospect_source=None,
        )


def test_absent_calendar_is_empty_only_when_no_published_sporting_source():
    empty=model.resolve_run_country_records(
        run_id="run",selected_branch_id="branch",revision_branch_id="branch",
        saved_revision_id="rev",country_code="CZE",
        packages=None,ranking=None,initial_world=None,prospect_source=None,
    )
    assert empty.calendar_status=="empty"
    assert empty.country_titles==0 and empty.hosted_results==()
    with pytest.raises(ValueError,match="country code"):
        model.resolve_run_country_records(
            run_id="run",selected_branch_id="branch",revision_branch_id="branch",
            saved_revision_id="rev",country_code="cze",
            packages=None,ranking=None,initial_world=None,prospect_source=None,
        )


def test_saved_tournament_evidence_is_full_cross_season_source_before_ui_periods(monkeypatch):
    """The v80 UI must be able to aggregate every canonical source row, not 25/page."""
    first=edition("old","EGY","P1","P2")
    first.season="2000/2001"
    first.season_week=61
    second=edition("new","CZE","P1","P2")
    second.season="2001/2002"
    second.season_week=1
    planned=edition("plan","CZE",None,None,False)
    planned.season="2002/2003"
    monkeypatch.setattr(model,"resolve_viewer_tournament_history",lambda **_:
        SimpleNamespace(tournaments=(second,planned,first)))
    from beta_engine.domain.run_packages import RunPackageState
    result=model.resolve_run_country_records(
        run_id="run",selected_branch_id="fork",revision_branch_id="branch",
        saved_revision_id="ancestor",country_code="CZE",
        packages=RunPackageState(run_id="run",branch_id="branch"),
        ranking=None,initial_world=_world(),prospect_source=None,
    )
    assert [(x.event_id,x.season,x.season_week) for x in result.player_results]==[
        ("old","2000/2001",61),("new","2001/2002",1)]
    assert result.country_titles==2 and result.hosted_published_results==1
    assert result.revision_branch_id=="branch" and result.branch_id=="fork"
    assert not any(x.event_id=="plan" for x in result.player_results+result.hosted_results)
