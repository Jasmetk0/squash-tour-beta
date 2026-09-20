import pytest

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardSlotResolution,
)


def _wild_card_authority(*, reserve=False, unfilled=False):
    if unfilled:
        slot = TournamentWildCardSlotResolution(
            wildcard_index=1,
            source="unfilled",
        )
    elif reserve:
        slot = TournamentWildCardSlotResolution(
            wildcard_index=1,
            original_player_id=None,
            active_player_id="prospect-rwc",
            source="reserve_wc",
            reserve_ordinal=2,
        )
    else:
        slot = TournamentWildCardSlotResolution(
            wildcard_index=1,
            original_player_id="prospect-wc",
            active_player_id="prospect-wc",
            source="original_wc",
        )
    return TournamentWildCardAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        resolved_by_command_id="wc-command",
        entry_field_fingerprint="a" * 64,
        field_sequence=3,
        original_wild_card_player_ids=(slot.original_player_id,),
        reserve_wild_card_player_ids=("prospect-rwc",) if reserve else (),
        slots=(slot,),
        adjusted_qualification_player_ids=(),
        adjusted_below_qualification_cut_player_ids=(),
    )


@pytest.mark.pr_critical
def test_definitive_wc_assignment_binds_exact_resolution_and_decision_time():
    source = _wild_card_authority()
    assignment = DefinitiveWildCardAssignmentAuthority.from_resolution(
        authority=source,
        wildcard_index=1,
        assignment_week=RankingWeek(season_index=2, week=18),
        decision_slot_ordinal=7,
        provenance="canonical definitive WC field assignment",
    )

    assert assignment.player_id == "prospect-wc"
    assert assignment.assignment_source == "original_wc"
    assert assignment.reserve_ordinal is None
    assert assignment.decision_position == (
        RankingWeek(season_index=2, week=18).ordinal,
        7,
    )
    assert assignment.source_wild_card_authority_fingerprint == source.fingerprint
    assert assignment.source_entry_field_fingerprint == source.entry_field_fingerprint
    assert assignment.source_field_sequence == source.field_sequence
    assert len(assignment.fingerprint) == 64


@pytest.mark.pr_critical
def test_definitive_rwc_assignment_preserves_reserve_provenance():
    assignment = DefinitiveWildCardAssignmentAuthority.from_resolution(
        authority=_wild_card_authority(reserve=True),
        wildcard_index=1,
        assignment_week=RankingWeek(season_index=2, week=18),
        decision_slot_ordinal=8,
        provenance="canonical definitive RWC field assignment",
    )
    assert assignment.player_id == "prospect-rwc"
    assert assignment.assignment_source == "reserve_wc"
    assert assignment.reserve_ordinal == 2


@pytest.mark.pr_critical
def test_unfilled_or_absent_wc_slot_cannot_create_definitive_assignment():
    with pytest.raises(ValueError, match="not a definitive assignment"):
        DefinitiveWildCardAssignmentAuthority.from_resolution(
            authority=_wild_card_authority(unfilled=True),
            wildcard_index=1,
            assignment_week=RankingWeek(season_index=2, week=18),
            decision_slot_ordinal=8,
            provenance="test",
        )
    with pytest.raises(ValueError, match="absent"):
        DefinitiveWildCardAssignmentAuthority.from_resolution(
            authority=_wild_card_authority(),
            wildcard_index=2,
            assignment_week=RankingWeek(season_index=2, week=18),
            decision_slot_ordinal=8,
            provenance="test",
        )


@pytest.mark.pr_critical
def test_definitive_wc_projects_exactly_to_tour_entry_trigger():
    assignment = DefinitiveWildCardAssignmentAuthority.from_resolution(
        authority=_wild_card_authority(),
        wildcard_index=1,
        assignment_week=RankingWeek(season_index=2, week=18),
        decision_slot_ordinal=7,
        provenance="canonical definitive WC field assignment",
    )
    trigger = assignment.to_tour_entry_trigger()

    assert isinstance(trigger, PlayerTourEntryTrigger)
    assert trigger.trigger_kind == "definitive_wild_card_assignment"
    assert trigger.player_id == assignment.player_id
    assert trigger.event_id == assignment.event_id
    assert trigger.trigger_week == assignment.assignment_week
    assert trigger.decision_slot_ordinal == assignment.decision_slot_ordinal
    assert trigger.source_evidence_id == assignment.source_evidence_id
    assert trigger.source_evidence_fingerprint == assignment.fingerprint


@pytest.mark.pr_critical
def test_valid_application_projects_exactly_to_same_tour_entry_contract():
    submission = TournamentApplicationSubmissionAuthority(
        application_id="application-1",
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id="prospect-app",
        entry_window="qualification",
        submission_week=RankingWeek(season_index=2, week=14),
        decision_slot_ordinal=4,
        nr_tie_break_token="nr-token",
        validation_authority_id="validation-1",
        validation_authority_fingerprint="b" * 64,
        provenance="canonical valid tournament application",
    )
    trigger = submission.to_tour_entry_trigger()

    assert trigger.trigger_kind == "valid_tournament_application"
    assert trigger.player_id == submission.player_id
    assert trigger.event_id == submission.event_id
    assert trigger.trigger_week == submission.submission_week
    assert trigger.decision_slot_ordinal == submission.decision_slot_ordinal
    assert trigger.source_evidence_id == submission.application_id
    assert trigger.source_evidence_fingerprint == submission.fingerprint
