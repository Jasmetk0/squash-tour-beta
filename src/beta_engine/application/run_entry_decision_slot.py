"""Adapter from persisted shared-snapshot Entry batches to Run/Branch slot truth."""

from __future__ import annotations

import hashlib
import json

from beta_engine.application.season_entry_batch_service import SeasonEntryBatchResult
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.domain.rankings.official import RankingWeek


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


def freeze_entry_batch_as_run_slot(
    *,
    batch: SeasonEntryBatchResult,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    decision_slot_ordinal: int,
) -> RunEntryDecisionSlotAuthority:
    """Bind committed legacy entry-decision evidence to exact Run chronology.

    The legacy Season batch owns shared-snapshot AI decision generation but does not
    know Run, Branch or the actual global Simulation Slot in which those decisions
    occurred. The caller supplies only that chronological scope; this adapter verifies
    the batch evidence and never decides application validity.
    """

    if not batch.metadata.persisted or batch.metadata.dry_run:
        raise ValueError("Run entry decision authority requires a persisted Entry batch")

    raw_decisions = [
        decision.model_dump(mode="json")
        for decision in batch.application_decisions
    ]
    decisions_fingerprint = _fingerprint(raw_decisions)
    if decisions_fingerprint != batch.metadata.application_decisions_fingerprint:
        raise ValueError("Entry batch application decision fingerprint mismatch")

    decisions = tuple(
        sorted(
            (
                EntryDecisionEvidence(
                    event_id=decision.event_id,
                    player_id=decision.player_id,
                    target=decision.target.value,
                    source_decision_fingerprint=_fingerprint(
                        decision.model_dump(mode="json")
                    ),
                )
                for decision in batch.application_decisions
            ),
            key=lambda item: (item.event_id, item.player_id, item.target),
        )
    )

    return RunEntryDecisionSlotAuthority(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        decision_slot_ordinal=decision_slot_ordinal,
        source_entry_batch_fingerprint=batch.metadata.build_fingerprint,
        source_application_decisions_fingerprint=decisions_fingerprint,
        source_active_players_fingerprint=batch.metadata.active_players_fingerprint,
        decisions=decisions,
    )
