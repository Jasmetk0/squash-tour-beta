import pytest

from scripts.audit_atp_2019_sackmann import audit_matches

pytestmark = pytest.mark.pr_critical

HEADER = "tourney_id,tourney_name,tourney_level,tourney_date,draw_size,match_num,round,winner_rank_points,loser_rank_points\n"


def test_scope_excludes_team_and_majors_without_interpreting_ranking_points():
    data = HEADER + (
        "2019-1,A,A,20190101,32,1,F,5000,2000\n"
        "2019-2,B,F,20190101,8,1,RR,100,200\n"
        "2019-9210,Team,A,20190101,12,1,RR,10,20\n"
        "2019-3,Major,G,20190101,128,1,F,400,500\n"
        "2019-4,Team,D,20190101,4,1,RR,1,2\n")
    assert audit_matches(data.encode()) == dict(all_rows=5, all_groups=5,
                                                scope_groups=2, scope_rows=2)


def test_duplicate_source_match_fails_closed():
    row = "2019-1,A,A,20190101,32,1,F,5000,2000\n"
    with pytest.raises(ValueError, match="Duplicate source match identity"):
        audit_matches((HEADER + row + row).encode())
