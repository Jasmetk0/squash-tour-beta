"""Canonical per-player Country standings: aggregate ALL verified published rows."""
from types import SimpleNamespace as NS
import pytest

from beta_engine.application import country_player_standings as model

pytestmark=pytest.mark.pr_critical


def finish(champion,finalist,champion_name=None,finalist_name=None):
    return NS(champion_player_id=champion,finalist_player_id=finalist,
        champion_name=champion_name or champion,finalist_name=finalist_name or finalist,
        champion_country="CZE",finalist_country="CZE")


def match(winner,loser,walkover=False):
    return NS(winner_player_id=winner,winner_name=winner,winner_country="CZE",
              loser_player_id=loser,loser_name=loser,loser_country="CZE",
              completion="walkover" if walkover else "played")


def attach(monkeypatch,finishes,matches,published=3,conflict=False):
    events=NS(
        run_id="run",branch_id="fork",revision_branch_id="origin",
        saved_revision_id="rev",calendar_status="ready",
        published_result_count=published,player_results=tuple(finishes),
        country_titles=len(finishes),country_finalists=len(finishes),
    )
    played_wins=sum(x.completion=="played" for x in matches)
    walkover_wins=sum(x.completion=="walkover" for x in matches)
    evidence=NS(
        published_event_count=published-1 if conflict else published,
        calendar_status="ready",revision_branch_id="origin",
        country_match_count=len(matches),
        country_played_wins=played_wins,country_played_losses=played_wins,
        country_walkover_wins=walkover_wins,country_walkover_losses=walkover_wins,
    )
    monkeypatch.setattr(model,"resolve_run_country_records",lambda **_:events)
    monkeypatch.setattr(model,"collect_country_saved_match_records",
        lambda **_:(evidence,tuple(matches)))


def read(**kw):
    return model.resolve_country_player_standings(
        run_id="run",selected_branch_id="fork",revision_branch_id="origin",
        saved_revision_id="rev",country_code="CZE",
        packages=None,ranking=None,initial_world=None,prospect_source=None,**kw)


def test_national_derby_each_side_counts_one_win_and_one_loss(monkeypatch):
    attach(monkeypatch,[finish("A","B"),finish("A","B"),finish("C","A")],[
        match("A","B"),match("B","A"),match("C","B"),match("B","C",True)
    ])
    result=read(limit=2)
    assert result.schema_version=="country_player_standings.v1"
    assert (result.branch_id,result.revision_branch_id,result.saved_revision_id)==("fork","origin","rev")
    assert result.total_players==3 and result.has_more
    assert [x.player_id for x in result.players]==["A","C"]
    a=result.players[0]
    assert (a.titles,a.runner_up_finishes,a.final_appearances)==(2,1,3)
    assert (a.played_wins,a.played_losses,a.walkover_wins)==(1,1,0)
    second=read(offset=2,limit=2)
    assert [x.player_id for x in second.players]==["B"]
    assert second.players[0].position==3
    b=second.players[0]
    assert (b.titles,b.runner_up_finishes,b.played_wins,b.played_losses)==(0,2,1,2)
    assert b.walkover_wins==1 and b.walkover_losses==0
    assert not second.has_more


def test_entire_saved_career_not_only_first_25_matches(monkeypatch):
    # 36 matches, 30 distinct players, all tied without title/finishes.
    matches=[match(f"P{i:02d}", f"P{(i+1)%30:02d}") for i in range(36)]
    attach(monkeypatch,[],matches,published=1)
    first=read(limit=25)
    assert first.total_players==30 and first.has_more
    assert len(first.players)==25
    last=read(offset=25,limit=25)
    assert len(last.players)==5 and not last.has_more
    assert len({x.player_id for x in first.players+last.players})==30
    all_rows=first.players+last.players
    assert sum(x.played_wins for x in all_rows)==36
    assert sum(x.played_losses for x in all_rows)==36
    assert all(x.position==i+1 for i,x in enumerate(all_rows))


def test_source_disagreement_and_identity_mismatch_fail_closed(monkeypatch):
    attach(monkeypatch,[finish("A","B")],[match("A","B")],published=1,conflict=True)
    with pytest.raises(ValueError,match="contradict"):
        read()
    attach(monkeypatch,[finish("A","B")],[match("A","B")],published=1)
    original=model.collect_country_saved_match_records
    def tampered(**kw):
        evidence,rows=original(**kw)
        return NS(**{**vars(evidence),"country_played_wins":99}),rows
    monkeypatch.setattr(model,"collect_country_saved_match_records",tampered)
    with pytest.raises(ValueError,match="totals contradict"):
        read()
    attach(monkeypatch,[finish("A","B")],[match("A","B")],published=1)
    attach(monkeypatch,[finish("A","B","Different name")],[match("A","B")],published=1)
    # Publication and match reconciliation disagree on canonical name.
    with pytest.raises(ValueError,match="name differs"):
        read()
    with pytest.raises(ValueError,match="page"):
        read(offset=-1)
