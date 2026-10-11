import pytest
from pydantic import ValidationError

from beta_engine.application.run_entry_decision_slot import (
    freeze_entry_batch_as_run_slot,
)
from beta_engine.application.season_entry_batch_service import (
    EntryBatchMetadata,
    SeasonEntryBatchResult,
)
from beta_engine.domain.entries import EntryDecision, EntryTarget
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    ValidatedApplicationDecision,
    ValidatedEntryDecisionSlot,
)


def _decision(**overrides):
    payload = {
        "player_id": "player-1",
        "event_id": "event-1",
        "week": 20,
        "target": EntryTarget.MAIN,
        "entry_score": 0.5,
        "entry_probability": 0.7,
        "travel_score": 0.8,
        "quality_score": 0.6,
        "prestige_score": 0.9,
    }
    payload.update(overrides)
    return EntryDecision(**payload)


def _fingerprint(value):
    import hashlib
    import json

    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


def _batch(*decisions, persisted=True):
    canonical = tuple(
        sorted(
            decisions,
            key=lambda item: (item.event_id, item.player_id, item.target.value),
        )
    )
    application_fp = _fingerprint(
        [item.model_dump(mode="json") for item in canonical]
    )
    return SeasonEntryBatchResult(
        entry_lists_by_event_id={},
        application_decisions=canonical,
        metadata=EntryBatchMetadata(
            event_ids=tuple(sorted({item.event_id for item in canonical})),
            season="2000/2001",
            seed=123,
            dry_run=not persisted,
            persisted=persisted,
            active_players_fingerprint="a" * 64,
            resolved_conflict_player_count=0,
            unresolved_conflict_player_count=0,
            application_decisions_fingerprint=application_fp,
            build_fingerprint="b" * 64,
            persistence_path="entries.json" if persisted else None,
        ),
    )


@pytest.mark.pr_critical
def test_persisted_shared_batch_freezes_exact_run_branch_week_and_global_slot():
    main = _decision()
    qualification = _decision(
        player_id="player-2",
        event_id="event-2",
        target=EntryTarget.QUALIFICATION,
    )
    batch = _batch(qualification, main)

    authority = freeze_entry_batch_as_run_slot(
        batch=batch,
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=4,
    )

    assert authority.run_id == "run"
    assert authority.branch_id == "branch"
    assert authority.decision_position == (
        RankingWeek(season_index=0, week=9).ordinal,
        4,
    )
    assert tuple(
        (item.event_id, item.player_id, item.target)
        for item in authority.decisions
    ) == (
        ("event-1", "player-1", "MAIN"),
        ("event-2", "player-2", "QUALIFICATION"),
    )
    assert authority.source_entry_batch_fingerprint == "b" * 64
    assert authority.source_active_players_fingerprint == "a" * 64
    assert len(authority.fingerprint) == 64


@pytest.mark.pr_critical
def test_run_slot_rejects_preview_or_tampered_application_decisions():
    preview = _batch(_decision(), persisted=False)
    with pytest.raises(ValueError, match="persisted Entry batch"):
        freeze_entry_batch_as_run_slot(
            batch=preview,
            run_id="run",
            branch_id="branch",
            week=RankingWeek(season_index=0, week=9),
            decision_slot_ordinal=1,
        )

    tampered = _batch(_decision())
    tampered.metadata.application_decisions_fingerprint = "c" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        freeze_entry_batch_as_run_slot(
            batch=tampered,
            run_id="run",
            branch_id="branch",
            week=RankingWeek(season_index=0, week=9),
            decision_slot_ordinal=1,
        )


@pytest.mark.pr_critical
def test_global_entry_slot_ordinal_starts_at_one():
    with pytest.raises(ValidationError):
        freeze_entry_batch_as_run_slot(
            batch=_batch(_decision()),
            run_id="run",
            branch_id="branch",
            week=RankingWeek(season_index=0, week=9),
            decision_slot_ordinal=0,
        )


@pytest.mark.pr_critical
def test_validated_subset_projects_only_valid_decisions_to_submission_batch():
    main = _decision()
    qualification = _decision(
        player_id="player-2",
        event_id="event-2",
        target=EntryTarget.QUALIFICATION,
    )
    authority = freeze_entry_batch_as_run_slot(
        batch=_batch(main, qualification),
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=4,
    )
    main_evidence = authority.decisions[0]

    validated = ValidatedEntryDecisionSlot(
        slot=authority,
        valid_applications=(
            ValidatedApplicationDecision(
                application_id="application-1",
                event_id=main_evidence.event_id,
                player_id=main_evidence.player_id,
                entry_window="main",
                source_decision_fingerprint=main_evidence.source_decision_fingerprint,
                nr_tie_break_token="nr-token-1",
                validation_authority_id="validation-1",
                validation_authority_fingerprint="d" * 64,
                provenance="validated MSA Tour application",
            ),
        ),
    )
    submission_batch = validated.to_submission_batch()

    assert submission_batch is not None
    assert len(submission_batch.submissions) == 1
    submission = submission_batch.submissions[0]
    assert submission.run_id == "run"
    assert submission.branch_id == "branch"
    assert submission.submission_week == RankingWeek(season_index=0, week=9)
    assert submission.decision_slot_ordinal == 4
    assert submission.event_id == "event-1"
    assert submission.player_id == "player-1"
    assert submission.entry_window == "main"


@pytest.mark.pr_critical
def test_validation_must_match_preserved_decision_identity_target_and_fingerprint():
    authority = freeze_entry_batch_as_run_slot(
        batch=_batch(_decision()),
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=4,
    )
    evidence = authority.decisions[0]

    def validated(**overrides):
        payload = {
            "application_id": "application-1",
            "event_id": evidence.event_id,
            "player_id": evidence.player_id,
            "entry_window": "main",
            "source_decision_fingerprint": evidence.source_decision_fingerprint,
            "nr_tie_break_token": "nr-token-1",
            "validation_authority_id": "validation-1",
            "validation_authority_fingerprint": "d" * 64,
            "provenance": "validated MSA Tour application",
        }
        payload.update(overrides)
        return ValidatedApplicationDecision(**payload)

    with pytest.raises(ValidationError, match="does not exist"):
        ValidatedEntryDecisionSlot(
            slot=authority,
            valid_applications=(validated(event_id="other-event"),),
        )
    with pytest.raises(ValidationError, match="window differs"):
        ValidatedEntryDecisionSlot(
            slot=authority,
            valid_applications=(validated(entry_window="qualification"),),
        )
    with pytest.raises(ValidationError, match="fingerprint does not match"):
        ValidatedEntryDecisionSlot(
            slot=authority,
            valid_applications=(
                validated(source_decision_fingerprint="e" * 64),
            ),
        )


@pytest.mark.pr_critical
def test_no_valid_applications_produces_no_submission_batch():
    authority = freeze_entry_batch_as_run_slot(
        batch=_batch(_decision()),
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=2,
    )
    validated = ValidatedEntryDecisionSlot(
        slot=authority,
        valid_applications=(),
    )
    assert validated.to_submission_batch() is None
