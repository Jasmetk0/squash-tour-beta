import pytest
from pydantic import ValidationError

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)


def _slot():
    return RunEntryDecisionSlotAuthority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=4,
        source_entry_batch_fingerprint="a" * 64,
        source_application_decisions_fingerprint="b" * 64,
        source_active_players_fingerprint="c" * 64,
        decisions=(
            EntryDecisionEvidence(
                event_id="event-1",
                player_id="player-1",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
            EntryDecisionEvidence(
                event_id="event-2",
                player_id="player-2",
                target="QUALIFICATION",
                source_decision_fingerprint="e" * 64,
            ),
        ),
    )


def _validation(slot, **overrides):
    payload = {
        "validation_id": "validation-1",
        "application_id": "application-1",
        "run_id": slot.run_id,
        "branch_id": slot.branch_id,
        "week": slot.week,
        "decision_slot_ordinal": slot.decision_slot_ordinal,
        "source_slot_fingerprint": slot.fingerprint,
        "event_id": "event-1",
        "player_id": "player-1",
        "entry_window": "main",
        "source_decision_fingerprint": "d" * 64,
        "outcome": "valid",
        "nr_tie_break_token": "nr-token-1",
        "validation_policy_id": "policy-v1",
        "validation_policy_fingerprint": "f" * 64,
        "reasons": (),
        "provenance": "explicit pre-alpha validation result",
    }
    payload.update(overrides)
    return TournamentApplicationValidationAuthority(**payload)


@pytest.mark.pr_critical
def test_validation_authority_freezes_versioned_outcome_and_fingerprint():
    slot = _slot()
    validation = _validation(slot)

    assert validation.outcome == "valid"
    assert validation.decision_position == (slot.week.ordinal, 4)
    assert validation.source_slot_fingerprint == slot.fingerprint
    assert len(validation.fingerprint) == 64
    projected = validation.to_validated_application_decision()
    assert projected is not None
    assert projected.validation_authority_id == validation.validation_id
    assert projected.validation_authority_fingerprint == validation.fingerprint


@pytest.mark.pr_critical
def test_valid_requires_nr_token_and_invalid_requires_reason():
    slot = _slot()
    with pytest.raises(ValidationError, match="NR tie-break token"):
        _validation(slot, nr_tie_break_token=None)

    with pytest.raises(ValidationError, match="at least one reason"):
        _validation(
            slot,
            outcome="invalid",
            nr_tie_break_token=None,
            reasons=(),
        )

    invalid = _validation(
        slot,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("ineligible_under_resolved_policy",),
    )
    assert invalid.to_validated_application_decision() is None


@pytest.mark.pr_critical
def test_resolved_slot_requires_exact_complete_decision_coverage():
    slot = _slot()
    first = _validation(slot)
    with pytest.raises(ValidationError, match="every preserved decision"):
        ResolvedApplicationValidationSlot(
            slot=slot,
            validations=(first,),
        )

    second = _validation(
        slot,
        validation_id="validation-2",
        application_id="application-2",
        event_id="event-2",
        player_id="player-2",
        entry_window="qualification",
        source_decision_fingerprint="e" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("ineligible_under_resolved_policy",),
    )
    resolved = ResolvedApplicationValidationSlot(
        slot=slot,
        validations=(first, second),
    )
    assert len(resolved.validations) == 2
    assert len(resolved.fingerprint) == 64


@pytest.mark.pr_critical
def test_resolved_slot_rejects_scope_target_or_source_evidence_drift():
    slot = _slot()
    second = _validation(
        slot,
        validation_id="validation-2",
        application_id="application-2",
        event_id="event-2",
        player_id="player-2",
        entry_window="qualification",
        source_decision_fingerprint="e" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("ineligible_under_resolved_policy",),
    )

    with pytest.raises(ValidationError, match="scope or slot evidence"):
        ResolvedApplicationValidationSlot(
            slot=slot,
            validations=(
                _validation(slot, source_slot_fingerprint="0" * 64),
                second,
            ),
        )

    with pytest.raises(ValidationError, match="window differs"):
        ResolvedApplicationValidationSlot(
            slot=slot,
            validations=(
                _validation(slot, entry_window="qualification"),
                second,
            ),
        )

    with pytest.raises(ValidationError, match="decision fingerprint mismatch"):
        ResolvedApplicationValidationSlot(
            slot=slot,
            validations=(
                _validation(slot, source_decision_fingerprint="1" * 64),
                second,
            ),
        )


@pytest.mark.pr_critical
def test_only_valid_outcomes_project_to_submission_batch():
    slot = _slot()
    valid = _validation(slot)
    invalid = _validation(
        slot,
        validation_id="validation-2",
        application_id="application-2",
        event_id="event-2",
        player_id="player-2",
        entry_window="qualification",
        source_decision_fingerprint="e" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("ineligible_under_resolved_policy",),
    )
    resolved = ResolvedApplicationValidationSlot(
        slot=slot,
        validations=(valid, invalid),
    )
    validated_slot = resolved.to_validated_entry_slot()
    submission_batch = validated_slot.to_submission_batch()

    assert submission_batch is not None
    assert len(submission_batch.submissions) == 1
    submission = submission_batch.submissions[0]
    assert submission.application_id == "application-1"
    assert submission.player_id == "player-1"
    assert submission.validation_authority_id == valid.validation_id
    assert submission.validation_authority_fingerprint == valid.fingerprint


@pytest.mark.pr_critical
def test_all_invalid_slot_produces_no_submission_batch():
    slot = _slot()
    invalid_one = _validation(
        slot,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("rule-a",),
    )
    invalid_two = _validation(
        slot,
        validation_id="validation-2",
        application_id="application-2",
        event_id="event-2",
        player_id="player-2",
        entry_window="qualification",
        source_decision_fingerprint="e" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        reasons=("rule-b",),
    )
    resolved = ResolvedApplicationValidationSlot(
        slot=slot,
        validations=(invalid_one, invalid_two),
    )
    assert resolved.to_validated_entry_slot().to_submission_batch() is None
