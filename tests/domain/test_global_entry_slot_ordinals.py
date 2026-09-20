import pytest
from pydantic import ValidationError

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryApplication


WEEK = RankingWeek(season_index=0, week=9)


def _submission(slot=1):
    return TournamentApplicationSubmissionAuthority(
        application_id="application-1",
        run_id="run",
        branch_id="branch",
        event_id="event-1",
        player_id="player-1",
        entry_window="main",
        submission_week=WEEK,
        decision_slot_ordinal=slot,
        nr_tie_break_token="nr-token",
        validation_authority_id="validation-1",
        validation_authority_fingerprint="a" * 64,
        provenance="test",
    )


@pytest.mark.pr_critical
def test_global_entry_timing_contracts_reject_slot_zero():
    with pytest.raises(ValidationError):
        PlayerTourEntryTrigger(
            run_id="run",
            branch_id="branch",
            player_id="player-1",
            event_id="event-1",
            trigger_kind="valid_tournament_application",
            trigger_week=WEEK,
            decision_slot_ordinal=0,
            source_evidence_id="application-1",
            source_evidence_fingerprint="a" * 64,
            provenance="test",
        )

    with pytest.raises(ValidationError):
        _submission(slot=0)

    with pytest.raises(ValidationError):
        TournamentApplicationSubmissionBatchAuthority(
            run_id="run",
            branch_id="branch",
            submission_week=WEEK,
            decision_slot_ordinal=0,
            submissions=(_submission(slot=1),),
        )

    with pytest.raises(ValidationError):
        DefinitiveWildCardAssignmentAuthority(
            run_id="run",
            branch_id="branch",
            event_id="event-1",
            player_id="player-1",
            wildcard_index=1,
            assignment_source="original_wc",
            assignment_week=WEEK,
            decision_slot_ordinal=0,
            source_wild_card_command_id="wc-command",
            source_wild_card_authority_fingerprint="b" * 64,
            source_entry_field_fingerprint="c" * 64,
            source_field_sequence=1,
            provenance="test",
        )

    with pytest.raises(ValidationError):
        TournamentEntryApplication(
            application_id="application-1",
            run_id="run",
            branch_id="branch",
            event_id="event-1",
            player_id="player-1",
            entry_window="main",
            decision_slot_ordinal=0,
            nr_tie_break_token="nr-token",
        )


@pytest.mark.pr_critical
def test_global_entry_timing_contracts_accept_slot_one():
    submission = _submission(slot=1)
    batch = TournamentApplicationSubmissionBatchAuthority.from_submissions((submission,))
    trigger = submission.to_tour_entry_trigger()
    field_application = submission.to_entry_field_application()

    wildcard = DefinitiveWildCardAssignmentAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-1",
        player_id="player-1",
        wildcard_index=1,
        assignment_source="original_wc",
        assignment_week=WEEK,
        decision_slot_ordinal=1,
        source_wild_card_command_id="wc-command",
        source_wild_card_authority_fingerprint="b" * 64,
        source_entry_field_fingerprint="c" * 64,
        source_field_sequence=1,
        provenance="test",
    )

    assert batch.decision_slot_ordinal == 1
    assert trigger.decision_slot_ordinal == 1
    assert field_application.decision_slot_ordinal == 1
    assert wildcard.decision_slot_ordinal == 1
    assert wildcard.to_tour_entry_trigger().decision_slot_ordinal == 1
