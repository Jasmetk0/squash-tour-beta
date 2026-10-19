"""Tour ranking candidate follows authentic 15yo source + actual first application."""
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_native_ranking_bridge import (
    CalendarNativeRankingAdoptionProof, calculate_native_ranking_from_signed_lifecycle,
)
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingRow, calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_tour import ranking_week
from tests.domain.test_calendar_native_birth_replay import (
    at, history, submission,
)
from tests.domain.test_calendar_prospect_birth_event import birth_row, source

pytestmark = pytest.mark.pr_critical


def prior_ranking(clock, target_lifecycle_week):
    return calculate_calendar_official_ranking(
        run_id="r", branch_id="b", run_calendar=clock,
        week=ranking_week(target_lifecycle_week), policy=OfficialRankingPolicy(
            policy_id="original-saved-ranking", best_n=15,
        ),
        players=(), results=(),
    )


@pytest.mark.parametrize("w,o", [(52, 1), (52, 35), (61, 37), (80, 15), (80, 80)])
def test_birth_is_not_ranked_automatically_but_actual_entry_is_in_next_ranking(w, o):
    clock = RunCalendar(w, o, 2030, 3)
    snapshot = source(birth_row(at(clock, w), "born"))
    evidence = submission(at(clock, w))
    states = history(clock, snapshot, last=w + 1, entries=(evidence,))
    assert states[w].players[0].player_id == "born"
    assert next(p for p in states[w].players if p.player_id == "born").tour_entry_week is None

    before = prior_ranking(clock, states[-2].week)
    approved, proof = calculate_native_ranking_from_signed_lifecycle(
        states=states, source=snapshot, world_package_id="world",
        submissions=(evidence,), previous=before,
        policy=OfficialRankingPolicy(policy_id="following-week", best_n=15),
    )
    assert [row.player_id for row in approved.rows] == ["born"]
    assert approved.rows[0].points == 0 and approved.rows[0].counted_results == ()
    assert proof.eligible_player_ids == ("born",)
    assert proof.classified_player_ids == ("born",)
    assert proof.not_entered_player_ids == ("existing",)
    assert len(proof.lifecycle_replay_fingerprint) == 64
    assert proof.calculated_ranking_fingerprint == approved.fingerprint
    assert proof == CalendarNativeRankingAdoptionProof.model_validate_json(proof.model_dump_json())
    duplicate, same = calculate_native_ranking_from_signed_lifecycle(
        states=states, source=snapshot, world_package_id="world",
        submissions=(evidence,), previous=before,
        policy=OfficialRankingPolicy(policy_id="following-week", best_n=15),
        expected=approved,
    )
    assert duplicate == approved and same == proof


@pytest.mark.parametrize("w,o", [(52, 1), (61, 35), (80, 80)])
def test_pre_entry_15yo_prospect_remains_unclassified(w, o):
    clock = RunCalendar(w, o, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    states = history(clock, snapshot, last=2)
    approved, proof = calculate_native_ranking_from_signed_lifecycle(
        states=states, source=snapshot, world_package_id="world",
        submissions=(), previous=prior_ranking(clock, states[-2].week),
        policy=OfficialRankingPolicy(policy_id="rank-before-first-app", best_n=15),
    )
    assert approved.rows == ()
    assert proof.eligible_player_ids == ()
    assert proof.not_entered_player_ids == ("born", "existing")


def test_forged_published_ranking_and_ineligible_prior_athlete_rejected():
    clock = RunCalendar(52, 35, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    evidence = submission(at(clock, 1))
    states = history(clock, snapshot, last=2, entries=(evidence,))
    prev = prior_ranking(clock, states[-2].week)
    candidate, _ = calculate_native_ranking_from_signed_lifecycle(
        states=states, source=snapshot, world_package_id="world",
        submissions=(evidence,), previous=prev,
        policy=OfficialRankingPolicy(policy_id="ranking", best_n=15),
    )
    forged = candidate.model_copy(update={"input_fingerprint": "0" * 64})
    with pytest.raises(ValueError, match="Published native ranking"):
        calculate_native_ranking_from_signed_lifecycle(
            states=states, source=snapshot, world_package_id="world",
            submissions=(evidence,), previous=prev,
            policy=OfficialRankingPolicy(policy_id="ranking", best_n=15),
            expected=forged,
        )

    invented_prior = prev.model_copy(update={"rows": (
        CalendarRankingRow(
            rank=1, player_id="born", points=0, counted_results=(),
        ),
    )})
    with pytest.raises(ValueError, match="without prior Tour Entry"):
        calculate_native_ranking_from_signed_lifecycle(
            states=states, source=snapshot, world_package_id="world",
            submissions=(evidence,), previous=invented_prior,
            policy=OfficialRankingPolicy(policy_id="ranking", best_n=15),
        )
    with pytest.raises(ValueError, match="exact previous"):
        calculate_native_ranking_from_signed_lifecycle(
            states=states, source=snapshot, world_package_id="world",
            submissions=(evidence,), previous=prev.model_copy(
                update={"run_id": "foreign"},
            ), policy=OfficialRankingPolicy(policy_id="ranking", best_n=15),
        )


def test_changing_signed_source_or_first_entry_receipt_fails_full_ranking_replay():
    clock = RunCalendar(80, 15, 2030, 3)
    snapshot = source(birth_row(at(clock, 1), "born"))
    evidence = submission(at(clock, 1))
    states = history(clock, snapshot, last=2, entries=(evidence,))
    prev = prior_ranking(clock, states[-2].week)
    changed = source(birth_row(at(clock, 1), "born"))
    changed.fingerprint = "a" * 64
    with pytest.raises(ValueError, match="birth event differs"):
        calculate_native_ranking_from_signed_lifecycle(
            states=states, source=changed, world_package_id="world",
            submissions=(evidence,), previous=prev,
            policy=OfficialRankingPolicy(policy_id="signed", best_n=15),
        )
    wrong_token = evidence.model_copy(update={"nr_tie_break_token": "forged"})
    with pytest.raises(ValueError, match="lifecycle differs"):
        calculate_native_ranking_from_signed_lifecycle(
            states=states, source=snapshot, world_package_id="world",
            submissions=(wrong_token,), previous=prev,
            policy=OfficialRankingPolicy(policy_id="signed", best_n=15),
        )
