from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsRaceRow,
    WorldTourFinalsRaceSnapshot,
    WorldTourFinalsSelectedPlayer,
    decide_race_replacement,
    initial_effective_participant_state,
    preview_race_replacement,
)
from beta_engine.domain.rankings.official import RankingWeek


H = "a" * 64


def _race() -> WorldTourFinalsRaceSnapshot:
    return WorldTourFinalsRaceSnapshot(
        run_id="run", branch_id="branch", target_season_index=0,
        cutoff_week=RankingWeek(season_index=0, week=60),
        cutoff_official_ranking_fingerprint=H, eligibility_fingerprint=H,
        policy_id="best", best_n=1, input_fingerprint=H, eligible_result_count=0,
        rows=tuple(WorldTourFinalsRaceRow(rank=i, player_id=f"P{i}", race_points=0, counted_results=(), tie_break_token=f"t{i}") for i in range(1, 10)),
    )


def _selection(race: WorldTourFinalsRaceSnapshot) -> WorldTourFinalsParticipantSelectionSnapshot:
    return WorldTourFinalsParticipantSelectionSnapshot(
        run_id="run", branch_id="branch", target_season_index=0, finals_event_id="finals",
        participant_capacity=6, configuration_fingerprint=H,
        race_snapshot_fingerprint=race.fingerprint, direct_entry_winner_event_ids=(),
        participants=tuple(WorldTourFinalsSelectedPlayer(player_id=f"P{i}", race_rank=i, race_points=0, seed=i, qualification_source="race") for i in range(1, 7)),
    )


def test_decline_then_accept_keeps_initial_selection_and_frozen_race_order():
    race = _race()
    selection = _selection(race)
    initial = initial_effective_participant_state(selection, command_id="initial")

    preview = preview_race_replacement(race=race, selection=selection, effective=initial, withdrawn_player_id="P3", withdrawal_reason="injury described by admin", vacancy_id="vacancy-1")
    assert (preview.offered_candidate_player_id, preview.offered_candidate_race_rank) == ("P7", 7)
    declined, state = decide_race_replacement(preview=preview, race=race, selection=selection, effective=initial, decision="decline", command_id="decline-7")
    assert state is None
    assert declined.offered_candidate_player_id == "P8"

    accepted, effective = decide_race_replacement(preview=declined, race=race, selection=selection, effective=initial, decision="accept", command_id="accept-8")
    assert effective is not None
    assert tuple(p.player_id for p in effective.participants) == ("P1", "P2", "P4", "P5", "P6", "P8")
    assert tuple(p.seed for p in effective.participants) == (1, 2, 3, 4, 5, 6)
    assert tuple(p.player_id for p in selection.participants) == tuple(f"P{i}" for i in range(1, 7))
    assert accepted.resulting_effective_state_fingerprint == effective.fingerprint
    assert [(d.player_id, d.race_rank, d.decision) for d in accepted.decisions] == [("P7", 7, "declined"), ("P8", 8, "accepted")]


def test_accepted_replacement_can_withdraw_and_exhaustion_fails_closed():
    race = _race()
    selection = _selection(race)
    initial = initial_effective_participant_state(selection, command_id="initial")
    first = preview_race_replacement(race=race, selection=selection, effective=initial, withdrawn_player_id="P3", withdrawal_reason="reason", vacancy_id="v1")
    _, replaced = decide_race_replacement(preview=first, race=race, selection=selection, effective=initial, decision="accept", command_id="accept-7")
    assert replaced is not None
    second = preview_race_replacement(race=race, selection=selection, effective=replaced, withdrawn_player_id="P7", withdrawal_reason="new reason", vacancy_id="v2")
    assert second.offered_candidate_player_id == "P3"  # frozen Race order; former player is not globally barred
    current = second
    for index in range(3, 10):
        current, _ = decide_race_replacement(preview=current, race=race, selection=selection, effective=replaced, decision="decline", command_id=f"decline-{index}")
        if current.status == "exhausted":
            break
    assert current.status == "exhausted"
    assert current.offered_candidate_player_id is None


def test_requires_reason_and_never_uses_player_id_fallback():
    race = _race()
    selection = _selection(race)
    initial = initial_effective_participant_state(selection, command_id="initial")
    try:
        preview_race_replacement(race=race, selection=selection, effective=initial, withdrawn_player_id="P3", withdrawal_reason=" ", vacancy_id="v")
    except ValueError as exc:
        assert str(exc) == "Finals withdrawal reason is required"
    else:
        raise AssertionError("blank reason accepted")
