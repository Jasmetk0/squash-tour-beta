import hashlib
import json

import pytest

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
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TournamentApplicationSubmissionStore,
    record_valid_application_submission_batch,
)


def _fp(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


@pytest.mark.pr_critical
def test_pre_cut_decision_to_persisted_first_tour_entry_end_to_end(tmp_path):
    decision = EntryDecision(
        player_id="prospect-1",
        event_id="event-1",
        week=20,
        target=EntryTarget.MAIN,
        entry_score=0.5,
        entry_probability=0.7,
        travel_score=0.8,
        quality_score=0.6,
        prestige_score=0.9,
    )
    application_fp = _fp([decision.model_dump(mode="json")])
    legacy_batch = SeasonEntryBatchResult(
        entry_lists_by_event_id={},
        application_decisions=(decision,),
        metadata=EntryBatchMetadata(
            event_ids=("event-1",),
            season="2000/2001",
            seed=123,
            dry_run=False,
            persisted=True,
            active_players_fingerprint="a" * 64,
            resolved_conflict_player_count=0,
            unresolved_conflict_player_count=0,
            application_decisions_fingerprint=application_fp,
            build_fingerprint="b" * 64,
            persistence_path="entries.json",
        ),
    )
    slot = freeze_entry_batch_as_run_slot(
        batch=legacy_batch,
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=9),
        decision_slot_ordinal=4,
    )
    evidence = slot.decisions[0]
    validated = ValidatedEntryDecisionSlot(
        slot=slot,
        valid_applications=(
            ValidatedApplicationDecision(
                application_id="application-1",
                event_id=evidence.event_id,
                player_id=evidence.player_id,
                entry_window="main",
                source_decision_fingerprint=evidence.source_decision_fingerprint,
                nr_tie_break_token="nr-token-1",
                validation_authority_id="validation-1",
                validation_authority_fingerprint="c" * 64,
                provenance="validated MSA Tour application",
            ),
        ),
    )
    submission_batch = validated.to_submission_batch()
    assert submission_batch is not None

    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'run-entry-slot.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    try:
        with factory.begin() as session:
            session.add(
                RunContainerModel(
                    run_id="run",
                    display_name="Run",
                    storage_kind="custom_local",
                    read_only=0,
                    timeline_start_season=2000,
                    timeline_end_season=2049,
                    official_branch_id="branch",
                    status="working",
                )
            )
            session.add(
                RunBranchModel(
                    run_id="run",
                    branch_id="branch",
                    display_name="Timeline 1",
                    status="active",
                    read_only=0,
                )
            )
            session.flush()

            committed = record_valid_application_submission_batch(
                session,
                submission_batch,
            )

            assert committed.batch == submission_batch
            assert TournamentApplicationSubmissionStore(session).list(
                run_id="run",
                branch_id="branch",
            ) == submission_batch.submissions
            trigger = PlayerTourEntryTriggerStore(session).get(
                run_id="run",
                branch_id="branch",
                player_id="prospect-1",
            )
            assert trigger is not None
            assert trigger.trigger_week == RankingWeek(season_index=0, week=9)
            assert trigger.decision_slot_ordinal == 4
            assert trigger.trigger_kind == "valid_tournament_application"
    finally:
        engine.dispose()
