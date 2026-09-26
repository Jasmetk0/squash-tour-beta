"""Canonical Run-owned tournament preparation inspection.

This read model intentionally composes only DB-backed Run/Branch authorities. It is
the preparation/navigation surface for Admin UI and orchestration; legacy EntryList,
DrawPackage, WC JSON and pre-draw replacement registries are not inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.simulation_slots import fingerprint

from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)


TournamentPreparationPhase = Literal[
    "ranking_snapshot_required",
    "entry_field_required",
    "wild_card_review_required",
    "draw_input_ready",
    "draw_generation_ready",
    "draw_ready",
]

TournamentPreparationNextAction = Literal[
    "adopt_ranking_snapshot",
    "build_entry_field",
    "review_wild_cards",
    "review_pre_draw_or_commit_draw_input",
    "generate_draw",
    "none",
]


class CanonicalWeekSchedulePreparationState(BaseModel):
    """Canonical readiness rollup for Week Schedule proposal/adoption."""

    schema_version: Literal["canonical_week_schedule_preparation_state.v1"] = (
        "canonical_week_schedule_preparation_state.v1"
    )
    run_id: str
    branch_id: str
    event_ids: tuple[str, ...]
    tournaments: tuple["CanonicalTournamentPreparationState", ...]
    ready_for_week_schedule: bool
    blockers: tuple[str, ...] = ()
    preparation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_source: Literal["run_owned_db_authorities.v1"] = (
        "run_owned_db_authorities.v1"
    )


class CanonicalTournamentPreparationState(BaseModel):
    """One authoritative navigation/readiness snapshot for tournament preparation."""

    schema_version: Literal["canonical_tournament_preparation_state.v1"] = (
        "canonical_tournament_preparation_state.v1"
    )
    run_id: str
    branch_id: str
    event_id: str

    phase: TournamentPreparationPhase
    next_required_action: TournamentPreparationNextAction
    blockers: tuple[str, ...] = ()

    ranking_snapshot_ready: bool
    ranking_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    ranking_week_ordinal: int | None = Field(default=None, ge=0)

    entry_field_ready: bool
    field_sequence: int = Field(ge=0)
    entry_field_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    entry_field_mode: str | None = None
    main_draw_size: int | None = Field(default=None, ge=2, le=128)
    qualification_draw_size: int | None = Field(default=None, ge=0, le=128)
    qualifier_spots: int | None = Field(default=None, ge=0, le=128)
    wild_card_slots: int | None = Field(default=None, ge=0, le=128)
    direct_main_player_count: int = Field(ge=0)
    qualification_player_count: int = Field(ge=0)
    reserve_player_count: int = Field(ge=0)
    withdrawn_player_count: int = Field(ge=0)

    wild_card_required: bool
    wild_card_ready: bool
    wild_card_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    active_wild_card_player_ids: tuple[str, ...] = ()

    pre_draw_repair_open: bool
    draw_input_ready: bool
    draw_input_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    draw_seed: int | None = None

    draw_ready: bool
    initial_draw_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    effective_draw_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    draw_revision_count: int = Field(ge=0)

    can_review_wild_cards: bool
    can_apply_pre_draw_withdrawal: bool
    can_commit_draw_input: bool
    can_generate_draw: bool
    ready_for_match_schedule: bool

    authority_source: Literal["run_owned_db_authorities.v1"] = (
        "run_owned_db_authorities.v1"
    )


@dataclass(slots=True)
class CanonicalTournamentPreparationService:
    factory: sessionmaker[Session]

    def inspect(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> CanonicalTournamentPreparationState:
        with self.factory() as session:
            return self.inspect_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

    def inspect_many(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_ids: tuple[str, ...],
    ) -> CanonicalWeekSchedulePreparationState:
        with self.factory() as session:
            return self.inspect_many_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_ids=event_ids,
            )

    @classmethod
    def inspect_many_in_session(
        cls,
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        event_ids: tuple[str, ...],
    ) -> CanonicalWeekSchedulePreparationState:
        canonical_event_ids = tuple(sorted(set(event_ids)))
        if not canonical_event_ids:
            raise ValueError("Week Schedule preparation requires at least one event")
        if event_ids != canonical_event_ids:
            raise ValueError(
                "Week Schedule preparation event IDs must be sorted and unique"
            )

        states = tuple(
            cls.inspect_in_session(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            for event_id in canonical_event_ids
        )
        blockers = tuple(
            f"{state.event_id}:{state.phase}"
            for state in states
            if not state.ready_for_match_schedule
        )
        payload = {
            "schema_version": "canonical_week_schedule_preparation_state.v1",
            "run_id": run_id,
            "branch_id": branch_id,
            "event_ids": canonical_event_ids,
            "tournaments": [
                state.model_dump(mode="json")
                for state in states
            ],
            "ready_for_week_schedule": not blockers,
            "blockers": blockers,
            "authority_source": "run_owned_db_authorities.v1",
        }
        return CanonicalWeekSchedulePreparationState(
            **payload,
            preparation_fingerprint=fingerprint(payload),
        )

    @staticmethod
    def inspect_in_session(
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
    ) -> CanonicalTournamentPreparationState:
        ranking = TournamentRankingSnapshotAuthorityStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        history = TournamentEntryFieldStore(session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        field = history[-1] if history else None

        wc = None
        if field is not None and field.capacity.wild_card_slots:
            wc = TournamentWildCardAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

        draw_input = None
        if field is not None:
            draw_input = TournamentDrawInputAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

        initial_draw = None
        effective_draw = None
        revisions = ()
        if draw_input is not None:
            initial_draw = TournamentDrawAuthorityStore(session).get_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if initial_draw is not None:
                effective_draw = TournamentDrawAuthorityStore(session).get(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                )
                revisions = TournamentDrawRevisionStore(session).history(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                )

        ranking_ready = ranking is not None
        field_ready = field is not None
        wc_required = bool(
            field is not None and field.capacity.wild_card_slots > 0
        )
        wc_ready = not wc_required or wc is not None
        draw_input_ready = draw_input is not None
        draw_ready = effective_draw is not None

        blockers: list[str] = []
        if not ranking_ready:
            phase: TournamentPreparationPhase = "ranking_snapshot_required"
            next_action: TournamentPreparationNextAction = "adopt_ranking_snapshot"
            blockers.append("tournament_ranking_snapshot_required")
        elif not field_ready:
            phase = "entry_field_required"
            next_action = "build_entry_field"
            blockers.append("tournament_entry_field_required")
        elif wc_required and not wc_ready:
            phase = "wild_card_review_required"
            next_action = "review_wild_cards"
            blockers.append("tournament_wild_card_review_required")
        elif not draw_input_ready:
            phase = "draw_input_ready"
            next_action = "review_pre_draw_or_commit_draw_input"
        elif not draw_ready:
            phase = "draw_generation_ready"
            next_action = "generate_draw"
        else:
            phase = "draw_ready"
            next_action = "none"

        active_wc_ids = ()
        if wc is not None:
            active_wc_ids = tuple(
                slot.active_player_id
                for slot in wc.slots
                if slot.active_player_id is not None and slot.source != "unfilled"
            )

        return CanonicalTournamentPreparationState(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            phase=phase,
            next_required_action=next_action,
            blockers=tuple(blockers),
            ranking_snapshot_ready=ranking_ready,
            ranking_authority_fingerprint=(
                ranking.fingerprint if ranking is not None else None
            ),
            ranking_week_ordinal=(
                ranking.ranking_week.ordinal if ranking is not None else None
            ),
            entry_field_ready=field_ready,
            field_sequence=len(history),
            entry_field_fingerprint=(
                field.fingerprint if field is not None else None
            ),
            entry_field_mode=field.mode if field is not None else None,
            main_draw_size=(
                field.capacity.main_draw_size if field is not None else None
            ),
            qualification_draw_size=(
                field.capacity.qualification_draw_size
                if field is not None
                else None
            ),
            qualifier_spots=(
                field.capacity.qualifier_spots if field is not None else None
            ),
            wild_card_slots=(
                field.capacity.wild_card_slots if field is not None else None
            ),
            direct_main_player_count=(
                len(field.direct_main_player_ids) if field is not None else 0
            ),
            qualification_player_count=(
                len(field.qualification_player_ids) if field is not None else 0
            ),
            reserve_player_count=(
                len(field.below_qualification_cut_player_ids)
                if field is not None
                else 0
            ),
            withdrawn_player_count=(
                len(field.withdrawn_player_ids) if field is not None else 0
            ),
            wild_card_required=wc_required,
            wild_card_ready=wc_ready,
            wild_card_authority_fingerprint=(
                wc.fingerprint if wc is not None else None
            ),
            active_wild_card_player_ids=active_wc_ids,
            pre_draw_repair_open=field_ready and not draw_input_ready,
            draw_input_ready=draw_input_ready,
            draw_input_fingerprint=(
                draw_input.fingerprint if draw_input is not None else None
            ),
            draw_seed=draw_input.draw_seed if draw_input is not None else None,
            draw_ready=draw_ready,
            initial_draw_fingerprint=(
                initial_draw.fingerprint if initial_draw is not None else None
            ),
            effective_draw_fingerprint=(
                effective_draw.fingerprint if effective_draw is not None else None
            ),
            draw_revision_count=len(revisions),
            can_review_wild_cards=(
                field_ready and wc_required and not wc_ready and not draw_input_ready
            ),
            can_apply_pre_draw_withdrawal=field_ready and not draw_input_ready,
            can_commit_draw_input=(
                ranking_ready and field_ready and wc_ready and not draw_input_ready
            ),
            can_generate_draw=draw_input_ready and not draw_ready,
            ready_for_match_schedule=draw_ready,
        )
