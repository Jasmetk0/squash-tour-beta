"""Country match records count canonical played outcomes only (critical path)."""
from types import SimpleNamespace
import pytest

from beta_engine.application import country_saved_match_records as model
from beta_engine.domain.run_packages import RunPackageState
from tests.application.test_viewer_people_read_model import _world

pytestmark = pytest.mark.pr_critical


def event(id, host, published=True):
    return SimpleNamespace(
        event_id=id, event_name="Edition " + id, season="2000/2001",
        season_week=6 if id == "away" else 7, host_country=host,
        result_published=published,
    )


def match(id, winner, loser, score="11-9, 11-7, 11-5"):
    return SimpleNamespace(
        match_id=id, winner_player_id=winner, loser_player_id=loser,
        draw_type="main", round_number=1, scoreline=score,
    )


def setup(monkeypatch, events, result_matches):
    monkeypatch.setattr(model, "resolve_viewer_tournament_history", lambda **_: SimpleNamespace(
        product_run_id="run", viewer_branch_id="branch", tournaments=tuple(events)
    ))
    def result(*_args, **kwargs):
        e=kwargs["event_id"]
        return SimpleNamespace(
            product_run_id="run", viewer_branch_id="branch", event_id=e,
            completed_season_index=0, completed_week=6 if e=="away" else 7,
            matches=result_matches[e],
        )
    monkeypatch.setattr(model,"resolve_viewer_tournament_result",result)


def read(*, offset=0, limit=25, packages=None, initial=None, ranking=None,
         season_index=None, result_kind="all", outcome="all"):
    return model.resolve_country_saved_match_records(
        run_id="run", selected_branch_id="fork", revision_branch_id="branch",
        saved_revision_id="old-revision", country_code="CZE",
        packages=packages if packages is not None else RunPackageState(run_id="run",branch_id="branch"),
        ranking=ranking, initial_world=initial if initial is not None else _world(),
        prospect_source=None, offset=offset, limit=limit,
        season_index=season_index, result_kind=result_kind, outcome=outcome,
    )


def test_played_vs_walkover_and_host_vs_player_nationality(monkeypatch):
    setup(monkeypatch,
        [event("away","EGY"),event("home","CZE"),event("future","CZE",False)],
        {
            "away":(match("a1","P1","P2"),match("a2","P2","P1","W/O")),
            "home":(match("h1","P2","P1"),match("bye","P2",None)),
        })
    all=read(limit=1)
    assert (all.published_event_count,all.total_played_matches,all.total_walkovers)==(2,2,1)
    assert (all.country_played_wins,all.country_played_losses)==(1,1)
    assert (all.country_walkover_wins,all.country_walkover_losses)==(0,1)
    assert (all.hosted_played_matches,all.hosted_walkovers)==(1,0)
    assert all.country_match_count==3 and all.has_more
    assert all.matches[0].event_id=="home"
    nxt=read(offset=1,limit=2)
    assert not nxt.has_more and {m.match_id for m in nxt.matches}=={"a1","a2"}
    assert all.revision_branch_id=="branch" and all.branch_id=="fork"
    assert all.matches[0].loser_country=="CZE"
    assert all.matches[0].winner_country=="EGY"


def test_invalid_or_ambiguous_match_evidence_never_becomes_zero(monkeypatch):
    setup(monkeypatch,[event("away","CZE")],{
        "away":(match("a1","P1","UNKNOWN"),)
    })
    with pytest.raises(ValueError, match="no verified nationality"):
        read()
    setup(monkeypatch,[event("away","CZE")],{
        "away":(match("dup","P1","P2"),match("dup","P2","P1"))
    })
    with pytest.raises(ValueError,match="Duplicate canonical"):
        read()
    setup(monkeypatch,[event("away","CZE")],{
        "away":(match("a1","P1","P1"),)
    })
    with pytest.raises(ValueError, match="against themselves"):
        read()


def test_empty_source_paging_and_foreign_branch_guard():
    from beta_engine.domain.rankings.revision_state import RankingRevisionState
    empty = model.resolve_country_saved_match_records(
        run_id="run",selected_branch_id="branch",revision_branch_id="branch",
        saved_revision_id="rev",country_code="CZE",
        packages=None,ranking=None,initial_world=None,prospect_source=None,
    )
    assert empty.calendar_status=="empty" and empty.matches==() and empty.total_played_matches==0
    with pytest.raises(ValueError,match="foreign"):
        model.resolve_country_saved_match_records(
            run_id="run",selected_branch_id="branch",revision_branch_id="other",
            saved_revision_id="rev",country_code="CZE",
            packages=RunPackageState(run_id="run",branch_id="branch"),
            ranking=None,initial_world=None,prospect_source=None,
        )
    with pytest.raises(ValueError, match="cursor"):
        model.resolve_country_saved_match_records(
            run_id="run",selected_branch_id="branch",revision_branch_id="branch",
            saved_revision_id="rev",country_code="CZE",
            packages=None,ranking=RankingRevisionState(run_id="run",branch_id="branch",
                entries=(),sources=(),tournament_sources=()),
            initial_world=None,prospect_source=None,limit=0,
        )


def test_filters_apply_to_full_saved_set_before_pagination(monkeypatch):
    setup(monkeypatch, [event("away", "EGY"), event("home", "CZE")], {
        "away": (
            match("a1", "P1", "P2"),
            match("a2", "P2", "P1", "W/O"),
        ),
        "home": (match("h1", "P2", "P1"),),
    })
    all = read(limit=1)
    assert all.filtered_match_count == 3
    assert all.country_match_count == 3
    assert all.available_seasons == (0,)
    assert all.has_more
    # "Played loss" selects the most recent match; global totals stay unchanged.
    played_loss = read(result_kind="played", outcome="loss", limit=1)
    assert played_loss.filtered_match_count == 1
    assert [item.match_id for item in played_loss.matches] == ["h1"]
    assert (played_loss.country_played_wins, played_loss.country_played_losses) == (1, 1)
    assert played_loss.country_match_count == 3
    walkover_loss = read(result_kind="walkover", outcome="loss", limit=1)
    assert walkover_loss.filtered_match_count == 1
    assert walkover_loss.matches[0].match_id == "a2"
    win = read(result_kind="played", outcome="win", limit=1)
    assert win.filtered_match_count == 1 and win.matches[0].match_id == "a1"
    missing_season = read(season_index=1)
    assert missing_season.filtered_match_count == 0
    assert missing_season.available_seasons == (0,)
    assert missing_season.country_match_count == 3
    assert missing_season.matches == () and not missing_season.has_more
    with pytest.raises(ValueError, match="season filter"):
        read(season_index=50)
    with pytest.raises(ValueError, match="result filter"):
        read(result_kind="bye")
