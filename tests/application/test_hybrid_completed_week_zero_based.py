"""Zero-based actual Run receipt week ordinals in hybrid ranking closure."""
import pytest
from beta_engine.application.hybrid_tournament_closure import hybrid_completed_week_from_ordinal
from beta_engine.domain.rankings.official import RankingWeek

pytestmark=pytest.mark.pr_critical

@pytest.mark.parametrize("ordinal,season,week",[
    (0,0,1),(1,0,2),(60,0,61),(61,1,1),
    (610,10,1),(3048,49,60),(3049,49,61),
])
def test_real_hybrid_knockout_receipt_zero_based_week_roundtrip(ordinal,season,week):
    resolved=hybrid_completed_week_from_ordinal(ordinal)
    assert resolved==RankingWeek(season_index=season,week=week)
    assert resolved.ordinal==ordinal

@pytest.mark.parametrize("ordinal",[-2,-1,3050,3100,True,0.5])
def test_real_hybrid_receipt_cannot_escape_fifty_season_span(ordinal):
    with pytest.raises(ValueError,match="outside Run range"):
        hybrid_completed_week_from_ordinal(ordinal)
