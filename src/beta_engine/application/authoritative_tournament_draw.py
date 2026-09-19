"""Canonical Run/Branch Admin boundary for Draw Input and initial Draw authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.bracket_diagnostics import (
    TournamentBracketDiagnostic,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
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


class CanonicalDrawInputCommitCommand(FrozenInput):
    """Freeze the current canonical field/ranking inputs at the draw boundary."""

    schema_version: Literal[
        "canonical_tournament_draw_input_commit_command.v1"
    ] = "canonical_tournament_draw_input_commit_command.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    expected_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    draw_seed: int


class CanonicalDrawGenerateCommand(FrozenInput):
    """Generate the immutable initial bracket from one committed Draw Input."""

    schema_version: Literal[
        "canonical_tournament_draw_generate_command.v1"
    ] = "canonical_tournament_draw_generate_command.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    expected_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CanonicalTournamentDrawState(FrozenInput):
    """Read model for the initial canonical pre-draw authority pipeline."""

    schema_version: Literal["canonical_tournament_draw_state.v1"] = (
        "canonical_tournament_draw_state.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    field_sequence: int = Field(ge=1)
    field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    main_draw_capacity: int = Field(ge=2, le=128)
    active_main_entrant_count: int = Field(ge=0, le=128)
    effective_main_bye_count: int = Field(ge=0, le=128)
    draw_input_committed: bool
    draw_input_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    draw_seed: int | None = None
    main_seed_count: int | None = Field(default=None, ge=0)
    qualification_seed_count: int | None = Field(default=None, ge=0)
    initial_draw_generated: bool
    draw_authority_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    draw_algorithm_version: str | None = None
    main_slot_count: int | None = Field(default=None, ge=2, le=128)
    main_node_count: int | None = Field(default=None, ge=1)
    main_bye_count: int | None = Field(default=None, ge=0, le=128)
    qualification_section_count: int | None = Field(default=None, ge=0)
    qualification_section_sizes: tuple[int, ...] = ()
    main_diagnostics: tuple[TournamentBracketDiagnostic, ...] = ()


class CanonicalTournamentDrawRevisionSummary(FrozenInput):
    sequence: int = Field(ge=1)
    schema_version: str
    command_id: str
    repair_kind: str
    affected_draw_types: tuple[str, ...]
    withdrawn_player_ids: tuple[str, ...]
    main_process_window_ordinal: int | None = Field(default=None, ge=1)
    qualification_process_window_ordinal: int | None = Field(default=None, ge=1)
    main_repair_action: str | None = None
    qualification_repair_action: str | None = None
    repair_draw_seed: int | None = None
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CanonicalTournamentDrawRevisionHistoryState(FrozenInput):
    schema_version: Literal["canonical_tournament_draw_revision_history.v1"] = (
        "canonical_tournament_draw_revision_history.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    initial_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    revisions: tuple[CanonicalTournamentDrawRevisionSummary, ...]


@dataclass(slots=True)
class CanonicalTournamentDrawService:
    """Transaction owner for initial Draw Input commitment and Draw generation."""

    factory: sessionmaker[Session]

    def inspect(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> CanonicalTournamentDrawState:
        with self.factory() as session:
            return self._state(
                session,
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )

    def inspect_initial_authority(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawAuthority:
        with self.factory() as session:
            authority = TournamentDrawAuthorityStore(session).get_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if authority is None:
                raise KeyError(
                    f"Initial Tournament Draw authority does not exist for event '{event_id}'"
                )
            return authority

    def inspect_effective_authority(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawAuthority:
        """Return the current canonical Draw projection after append-only revisions."""

        with self.factory() as session:
            authority = TournamentDrawAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if authority is None:
                raise KeyError(
                    f"Effective Tournament Draw authority does not exist for event '{event_id}'"
                )
            return authority

    def inspect_revision_history(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> CanonicalTournamentDrawRevisionHistoryState:
        """Return compact append-only Draw revision audit history."""

        with self.factory() as session:
            initial = TournamentDrawAuthorityStore(session).get_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if initial is None:
                raise KeyError(
                    f"Initial Tournament Draw authority does not exist for event '{event_id}'"
                )
            history = TournamentDrawRevisionStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            effective = history[-1].successor_draw if history else initial
            return CanonicalTournamentDrawRevisionHistoryState(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                initial_draw_fingerprint=initial.fingerprint,
                effective_draw_fingerprint=effective.fingerprint,
                revisions=tuple(
                    CanonicalTournamentDrawRevisionSummary(
                        sequence=revision.sequence,
                        schema_version=revision.schema_version,
                        command_id=revision.command_id,
                        repair_kind=revision.repair_kind,
                        affected_draw_types=revision.affected_draw_types,
                        withdrawn_player_ids=revision.withdrawn_player_ids,
                        main_process_window_ordinal=revision.main_process_window_ordinal,
                        qualification_process_window_ordinal=(
                            revision.qualification_process_window_ordinal
                        ),
                        main_repair_action=revision.main_repair_action,
                        qualification_repair_action=(
                            revision.qualification_repair_action
                        ),
                        repair_draw_seed=revision.repair_draw_seed,
                        predecessor_draw_fingerprint=(
                            revision.predecessor_draw_fingerprint
                        ),
                        successor_draw_input_fingerprint=(
                            revision.successor_draw_input.fingerprint
                        ),
                        successor_draw_fingerprint=revision.successor_draw.fingerprint,
                    )
                    for revision in history
                ),
            )

    def commit_input(
        self, command: CanonicalDrawInputCommitCommand
    ) -> CanonicalTournamentDrawState:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            history = TournamentEntryFieldStore(session).history(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )
            if not history:
                raise KeyError(
                    f"Tournament Entry Field does not exist for event '{command.event_id}'"
                )
            latest = history[-1]
            if latest.fingerprint != command.expected_field_fingerprint:
                raise ValueError(
                    "Tournament Entry Field changed since Draw Input commitment was prepared"
                )
            TournamentDrawInputAuthorityStore(session).commit(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
                command_id=command.command_id,
                draw_seed=command.draw_seed,
            )
            return self._state(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )

    def generate(
        self, command: CanonicalDrawGenerateCommand
    ) -> CanonicalTournamentDrawState:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            draw_input = TournamentDrawInputAuthorityStore(session).get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )
            if draw_input is None:
                raise ValueError(
                    "Tournament Draw generation requires committed Draw Input authority"
                )
            if draw_input.fingerprint != command.expected_draw_input_fingerprint:
                raise ValueError(
                    "Tournament Draw Input changed since Draw generation was prepared"
                )
            TournamentDrawAuthorityStore(session).generate(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
                command_id=command.command_id,
            )
            return self._state(
                session,
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=command.event_id,
            )

    @staticmethod
    def _state(
        session: Session,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
    ) -> CanonicalTournamentDrawState:
        history = TournamentEntryFieldStore(session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise KeyError(
                f"Tournament Entry Field does not exist for event '{event_id}'"
            )
        field = history[-1]
        draw_input = TournamentDrawInputAuthorityStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        initial_draw = TournamentDrawAuthorityStore(session).get_initial(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        qualification_sections = (
            initial_draw.qualification_brackets if initial_draw is not None else ()
        )
        return CanonicalTournamentDrawState(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            field_sequence=len(history),
            field_fingerprint=field.fingerprint,
            main_draw_capacity=field.capacity.main_draw_size,
            active_main_entrant_count=field.active_main_entrant_count,
            effective_main_bye_count=field.effective_main_bye_count,
            draw_input_committed=draw_input is not None,
            draw_input_fingerprint=(
                draw_input.fingerprint if draw_input is not None else None
            ),
            draw_seed=draw_input.draw_seed if draw_input is not None else None,
            main_seed_count=(
                draw_input.main_seed_count if draw_input is not None else None
            ),
            qualification_seed_count=(
                draw_input.qualification_seed_count
                if draw_input is not None
                else None
            ),
            initial_draw_generated=initial_draw is not None,
            draw_authority_fingerprint=(
                initial_draw.fingerprint if initial_draw is not None else None
            ),
            draw_algorithm_version=(
                initial_draw.algorithm_version if initial_draw is not None else None
            ),
            main_slot_count=(
                len(initial_draw.main.slots) if initial_draw is not None else None
            ),
            main_node_count=(
                len(initial_draw.main.nodes) if initial_draw is not None else None
            ),
            main_bye_count=(
                len(initial_draw.main.bye_slot_indexes)
                if initial_draw is not None
                else None
            ),
            qualification_section_count=(
                len(qualification_sections) if initial_draw is not None else None
            ),
            qualification_section_sizes=tuple(
                section.bracket_size for section in qualification_sections
            ),
            main_diagnostics=(
                initial_draw.main_bracket_diagnostics
                if initial_draw is not None
                else field.main_diagnostics
            ),
        )
