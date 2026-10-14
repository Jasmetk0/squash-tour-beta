"""Critical Country match-record aggregate tests: ties, genuine play, period, evidence."""
from types import SimpleNamespace
import pytest

from beta_engine.application import country_match_record_highlights as model
from beta_engine.application.country_saved_match_records import CountrySavedMatch

pytestmark = pytest.mark.pr_critical


def row(mid, season, week, winner, loser, *, winner_country="CZE",
        loser_country="EGY", completion="played"):
    return CountrySavedMatch(
        event_id="event-"+mid, event_name="Open "+mid,
        season=season, season_week=week, match_id=mid,
        draw_type="main", round_number=1,
        winner_player_id=winner, winner_name=winner,
        winner_country=winner_country, loser_player_id=loser,
        loser_name=loser, loser_country=loser_country,
        host_country="CZE", completion=completion,
        scoreline="11-9, 11-8, 11-5" if completion=="played" else "W/O",
    )


def read(monkeypatch, rows, *, frm=(0, 1), to=(49, 61),
         key=None, offset=0, limit=25):
    def fake_collector(**kwargs):
        assert kwargs["selected_branch_id"]=="fork"
        assert kwargs["revision_branch_id"]=="parent"
        assert kwargs["saved_revision_id"]=="old-rev"
        assert kwargs["offset"]==0 and kwargs["limit"]==1
        return SimpleNamespace(), tuple(rows)
    monkeypatch.setattr(model, "collect_country_saved_match_records", fake_collector)
    return model.resolve_country_match_record_highlights(
        run_id="run",selected_branch_id="fork",revision_branch_id="parent",
        saved_revision_id="old-rev",country_code="CZE",packages=None,ranking=None,
        initial_world=None,prospect_source=None,
        from_season=frm[0],from_week=frm[1],to_season=to[0],to_week=to[1],
        selected_record=key,offset=offset,limit=limit,
    )


def test_boundary_week_and_ties_derive_from_full_canonical_evidence(monkeypatch):
    rows=[
        row("before","2000/2001",60,"P1","X"),
        row("first","2000/2001",61,"P1","Y"),
        row("second","2001/2002",1,"P2","Z"),
        row("after","2001/2002",2,"P2","Q"),
    ]
    result=read(monkeypatch,rows,frm=(0,61),to=(1,1),
                key="played_wins",limit=1)
    assert result.period_country_matches==result.period_played_matches==2
    assert result.period_walkovers==0
    assert [(r.key,r.value,[h.player_id for h in r.holders]) for r in result.records]==[
        ("played_wins",1,["P1","P2"]),("played_matches",1,["P1","P2"])]
    assert result.evidence_count==2 and result.has_more
    assert [m.match_id for m in result.evidence]==["first"]
    second=read(monkeypatch,rows,frm=(0,61),to=(1,1),
                key="played_wins",offset=1,limit=1)
    assert second.evidence_count==2 and not second.has_more
    assert [m.match_id for m in second.evidence]==["second"]
    assert result.branch_id=="fork" and result.revision_branch_id=="parent"
    assert result.saved_revision_id=="old-rev"


def test_derby_counts_each_player_once_no_bye_or_walkover_as_played(monkeypatch):
    rows=[
        row("derby","2000/2001",4,"P1","P2",loser_country="CZE"),
        row("wo","2000/2001",5,"P2","P1",loser_country="CZE",completion="walkover"),
        row("other","2000/2001",6,"P2","X"),
    ]
    result=read(monkeypatch,rows,frm=(0,1),to=(0,61),key="played_matches")
    assert result.period_country_matches==3
    assert result.period_played_matches==2 and result.period_walkovers==1
    assert result.records[0].value==1
    assert [h.player_id for h in result.records[0].holders]==["P1","P2"]
    assert result.records[1].value==2
    assert [h.player_id for h in result.records[1].holders]==["P2"]
    assert result.evidence_count==2
    assert {m.match_id for m in result.evidence}=={"derby","other"}
    assert all(m.completion=="played" for m in result.evidence)


def test_empty_period_has_no_fake_holders_and_bad_range_fails(monkeypatch):
    empty=read(monkeypatch,[row("later","2001/2002",1,"P1","X")],
               frm=(0,1),to=(0,61),key="played_wins")
    assert empty.period_country_matches==0 and empty.evidence_count==0
    assert all(r.value==0 and not r.holders for r in empty.records)
    with pytest.raises(ValueError,match="interval"):
        read(monkeypatch,[],frm=(1,1),to=(0,61))
    with pytest.raises(ValueError,match="category"):
        read(monkeypatch,[],key="invented")
    with pytest.raises(ValueError,match="page"):
        read(monkeypatch,[],limit=51)


def test_identity_conflicts_fail_not_renamed_or_deduplicated(monkeypatch):
    rows=[row("a","2000/2001",1,"P1","X"),
          row("b","2000/2001",2,"P1","Z")]
    rows[1]=rows[1].model_copy(update={"winner_name":"not P1"})
    with pytest.raises(ValueError,match="Ambiguous"):
        read(monkeypatch,rows)


def test_full_57_match_aggregate_survives_three_evidence_pages(monkeypatch):
    rows=[row(f"m-{i:03d}","2000/2001",1+(i%61),"P1",f"foreign-{i}") for i in range(57)]
    first=read(monkeypatch,rows,key="played_wins",offset=0,limit=25)
    middle=read(monkeypatch,rows,key="played_wins",offset=25,limit=25)
    last=read(monkeypatch,rows,key="played_wins",offset=50,limit=25)
    assert all(x.records[0].value==57 for x in (first,middle,last))
    assert all(x.evidence_count==57 for x in (first,middle,last))
    assert [len(x.evidence) for x in (first,middle,last)]==[25,25,7]
    assert first.has_more and middle.has_more and not last.has_more
    assert len({m.match_id for part in (first,middle,last) for m in part.evidence})==57
