import pytest
from pydantic import ValidationError

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)


def _submission(**overrides):
    payload = {
        "application_id": "app-1",
        "run_id": "run",
        "branch_id": "branch",
        "event_id": "event-1",
        "player_id": "prospect-1",
        "entry_window": "qualification",
        "submission_week": RankingWeek(season_index=2, week=14),
        "decision_slot_ordinal": 5,
        "nr_tie_break_token": "nr-token-1",
        "validation_authority_id": "entry-validation-1",
        "validation_authority_fingerprint": "a" * 64,
        "provenance": "canonical valid application submission",
    }
    payload.update(overrides)
    return TournamentApplicationSubmissionAuthority(**payload)


@pytest.mark.pr_critical
def test_valid_application_submission_freezes_exact_decision_time_and_evidence():
    submission = _submission()

    assert submission.decision_position == (submission.submission_week.ordinal, 5)
    assert len(submission.fingerprint) == 64
    assert submission == _submission()
    assert submission.fingerprint == _submission().fingerprint


@pytest.mark.pr_critical
def test_submission_projects_losslessly_to_existing_field_application():
    submission = _submission()
    field_app = submission.to_entry_field_application()

    assert field_app.application_id == submission.application_id
    assert field_app.run_id == submission.run_id
    assert field_app.branch_id == submission.branch_id
    assert field_app.event_id == submission.event_id
    assert field_app.player_id == submission.player_id
    assert field_app.entry_window == submission.entry_window
    assert field_app.decision_slot_ordinal == submission.decision_slot_ordinal
    assert field_app.nr_tie_break_token == submission.nr_tie_break_token
    assert field_app.eligible is True


@pytest.mark.pr_critical
def test_submission_fingerprint_binds_scope_timing_and_validation_authority():
    baseline = _submission()
    variants = (
        _submission(branch_id="other"),
        _submission(player_id="prospect-2"),
        _submission(event_id="event-2"),
        _submission(submission_week=RankingWeek(season_index=2, week=15)),
        _submission(decision_slot_ordinal=6),
        _submission(validation_authority_id="entry-validation-2"),
        _submission(validation_authority_fingerprint="b" * 64),
        _submission(nr_tie_break_token="other-token"),
    )
    assert all(item.fingerprint != baseline.fingerprint for item in variants)


@pytest.mark.pr_critical
def test_submission_rejects_missing_validation_or_malformed_decision_evidence():
    with pytest.raises(ValidationError):
        _submission(validation_authority_id="")
    with pytest.raises(ValidationError):
        _submission(validation_authority_fingerprint="bad")
    with pytest.raises(ValidationError):
        _submission(decision_slot_ordinal=-1)
    with pytest.raises(ValidationError):
        _submission(entry_window="wild_card")

@pytest.mark.pr_critical
def test_application_batch_canonicalizes_input_order_without_creating_priority():
    a = _submission(application_id="app-a", event_id="event-a")
    b = _submission(application_id="app-b", event_id="event-b")
    first = TournamentApplicationSubmissionBatchAuthority.from_submissions((b, a))
    second = TournamentApplicationSubmissionBatchAuthority.from_submissions((a, b))

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert tuple(item.application_id for item in first.submissions) == ("app-a", "app-b")
    assert first.representative_first_applications() == (a,)


@pytest.mark.pr_critical
def test_application_batch_rejects_mixed_scope_or_decision_slot():
    baseline = _submission(application_id="app-a")
    with pytest.raises(ValidationError, match="Run/Branch"):
        TournamentApplicationSubmissionBatchAuthority.from_submissions(
            (baseline, _submission(application_id="app-b", branch_id="other"))
        )
    with pytest.raises(ValidationError, match="decision slot"):
        TournamentApplicationSubmissionBatchAuthority.from_submissions(
            (
                baseline,
                _submission(
                    application_id="app-b",
                    decision_slot_ordinal=6,
                ),
            )
        )

