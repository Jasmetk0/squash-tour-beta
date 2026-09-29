"""Guarded application workflow for World Tour Finals Race replacements."""

from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from beta_engine.domain.finals import (
    WorldTourFinalsReplacementAuthority,
    decide_race_replacement,
    initial_effective_participant_state,
    preview_race_replacement,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.finals_race_authority import (
    WorldTourFinalsRaceAuthorityStore,
)
from beta_engine.infrastructure.db.finals_race_replacement import (
    WorldTourFinalsReplacementStore,
)
from beta_engine.infrastructure.db.models import TournamentDrawInputAuthorityModel
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)


class FinalsReplacementPreviewCommand(FrozenInput):
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    withdrawn_player_id: str = Field(min_length=1)
    withdrawal_reason: str = Field(min_length=1, max_length=2000)
    vacancy_id: str = Field(min_length=1, max_length=128)
    expected_effective_state_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    command_id: str = Field(min_length=1, max_length=128)


class FinalsReplacementDecisionCommand(FrozenInput):
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    vacancy_id: str = Field(min_length=1, max_length=128)
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_effective_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["decline", "accept"]
    command_id: str = Field(min_length=1, max_length=128)
    main_process_window_ordinal: int | None = Field(default=None, ge=1)
    repair_draw_seed: int | None = None


@dataclass(slots=True)
class WorldTourFinalsReplacementService:
    factory: object

    def _sources(self, session, command):
        selection = WorldTourFinalsParticipantSelectionStore(session).get_snapshot(
            run_id=command.run_id,
            branch_id=command.branch_id,
            target_season_index=command.target_season_index,
        )
        race = WorldTourFinalsRaceAuthorityStore(session).get_snapshot(
            run_id=command.run_id,
            branch_id=command.branch_id,
            target_season_index=command.target_season_index,
        )
        if selection is None or race is None:
            raise ValueError(
                "Finals replacement requires frozen Race and initial participant selection"
            )
        return race, selection

    def inspect(self, *, run_id: str, branch_id: str, target_season_index: int):
        with self.factory() as session:
            store = WorldTourFinalsReplacementStore(session)
            state = store.latest_state(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            selection = WorldTourFinalsParticipantSelectionStore(session).get_snapshot(
                run_id=run_id, branch_id=branch_id,
                target_season_index=target_season_index,
            )
            if selection is None:
                return {"effective_state": None, "replacement_history": (), "draw_revision": None}
            history = store.event_authority_history(
                run_id=run_id, branch_id=branch_id,
                target_season_index=target_season_index,
                finals_event_id=selection.finals_event_id,
            )
            revisions = TournamentDrawRevisionStore(session).history(
                run_id=run_id, branch_id=branch_id,
                event_id=selection.finals_event_id,
            ) if session.get(TournamentDrawInputAuthorityModel, (run_id, branch_id, selection.finals_event_id)) is not None else ()
            return {
                "effective_state": state,
                "replacement_history": history,
                "draw_revision": revisions[-1] if revisions else None,
            }

    def preview(
        self, command: FinalsReplacementPreviewCommand
    ) -> WorldTourFinalsReplacementAuthority:
        with self.factory.begin() as session:
            race, selection = self._sources(session, command)
            store = WorldTourFinalsReplacementStore(session)
            effective = store.latest_state(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            if effective is None:
                effective = store.put_state(
                    initial_effective_participant_state(
                        selection, command_id=f"initial:{selection.fingerprint}"
                    )
                )
            if (
                command.expected_effective_state_fingerprint is not None
                and effective.fingerprint
                != command.expected_effective_state_fingerprint
            ):
                raise ValueError(
                    "Effective Finals participant state changed since preview was prepared"
                )
            existing = store.authority_history(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
                finals_event_id=selection.finals_event_id,
                vacancy_id=command.vacancy_id,
            )
            if existing:
                retry = next(
                    (
                        item
                        for item in existing
                        if item.command_id == command.command_id
                    ),
                    None,
                )
                if retry is not None:
                    return store.put_authority(retry)
                raise ValueError(
                    "Finals replacement vacancy already exists; decide its current candidate"
                )
            value = preview_race_replacement(
                race=race,
                selection=selection,
                effective=effective,
                withdrawn_player_id=command.withdrawn_player_id,
                withdrawal_reason=command.withdrawal_reason,
                vacancy_id=command.vacancy_id,
                command_id=command.command_id,
            )
            return store.put_authority(value)

    def decide(
        self, command: FinalsReplacementDecisionCommand
    ) -> WorldTourFinalsReplacementAuthority:
        with self.factory.begin() as session:
            race, selection = self._sources(session, command)
            store = WorldTourFinalsReplacementStore(session)
            history = store.authority_history(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
                finals_event_id=selection.finals_event_id,
                vacancy_id=command.vacancy_id,
            )
            retry = next(
                (item for item in history if item.command_id == command.command_id),
                None,
            )
            if retry is not None:
                return store.put_authority(retry)
            if (
                not history
                or history[-1].fingerprint != command.expected_preview_fingerprint
            ):
                raise ValueError("Finals replacement preview changed before decision")
            effective = store.latest_state(
                run_id=command.run_id,
                branch_id=command.branch_id,
                target_season_index=command.target_season_index,
            )
            if (
                effective is None
                or effective.fingerprint != command.expected_effective_state_fingerprint
            ):
                raise ValueError(
                    "Effective Finals participant state changed before decision"
                )
            authority, successor = decide_race_replacement(
                preview=history[-1],
                race=race,
                selection=selection,
                effective=effective,
                decision=command.decision,
                command_id=command.command_id,
            )
            store.put_authority(authority)
            if successor is not None:
                store.put_state(successor)
                if (
                    session.get(
                        TournamentDrawInputAuthorityModel,
                        (command.run_id, command.branch_id, selection.finals_event_id),
                    )
                    is None
                ):
                    TournamentEntryFieldStore(
                        session
                    ).stage_from_finals_effective_state(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=selection.finals_event_id,
                        target_season_index=command.target_season_index,
                        effective_state_fingerprint=successor.fingerprint,
                        command_id=f"{command.command_id}:entry-field"[:128],
                    )
                else:
                    if command.main_process_window_ordinal is None:
                        raise ValueError(
                            "Post-draw Finals replacement requires Main process-window ordinal"
                        )
                    TournamentDrawRevisionStore(session).finals_race_replacement(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=selection.finals_event_id,
                        command_id=f"{command.command_id}:draw-revision"[:128],
                        replacement_authority=authority,
                        effective_state=successor,
                        main_process_window_ordinal=command.main_process_window_ordinal,
                        repair_draw_seed=command.repair_draw_seed,
                    )
            return authority
