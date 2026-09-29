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
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
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
    main_process_window_ordinal: int | None = Field(default=None, ge=1)
    repair_draw_seed: int | None = None
    command_id: str = Field(min_length=1, max_length=128)


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
            return state

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
            draw = TournamentDrawAuthorityStore(session).get_initial(
                run_id=command.run_id,
                branch_id=command.branch_id,
                event_id=selection.finals_event_id,
            )
            if draw is not None:
                cutoff = TournamentPlayerReplacementCutoffAuthorityStore(
                    session
                ).resolve(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    event_id=selection.finals_event_id,
                    player_id=command.withdrawn_player_id,
                    draw_type="main",
                )
                if cutoff.status == "walkover_required":
                    raise ValueError(
                        "Finals replacement cutoff has passed; canonical W/O is required"
                    )
                if cutoff.status == "already_eliminated":
                    raise ValueError(
                        "Finals withdrawal cannot replace an already eliminated player"
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
                    if (
                        retry.withdrawn_player_id != command.withdrawn_player_id
                        or retry.withdrawal_reason != command.withdrawal_reason.strip()
                        or (
                            command.expected_effective_state_fingerprint is not None
                            and retry.source_effective_state_fingerprint
                            != command.expected_effective_state_fingerprint
                        )
                    ):
                        raise ValueError(
                            "Finals replacement command ID already has a different preview request"
                        )
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
                matching_decision = next(
                    (
                        item
                        for item in retry.decisions
                        if item.decision_id == command.command_id
                    ),
                    None,
                )
                if (
                    matching_decision is None
                    or matching_decision.decision
                    != ("accepted" if command.decision == "accept" else "declined")
                    or retry.source_effective_state_fingerprint
                    != command.expected_effective_state_fingerprint
                    or retry.predecessor_authority_fingerprint
                    != command.expected_preview_fingerprint
                ):
                    raise ValueError(
                        "Finals replacement command ID already has a different decision request"
                    )
                if command.decision == "accept":
                    draw = TournamentDrawAuthorityStore(session).get_initial(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=selection.finals_event_id,
                    )
                    if draw is not None:
                        revision = next(
                            (
                                item
                                for item in TournamentDrawRevisionStore(
                                    session
                                ).history(
                                    run_id=command.run_id,
                                    branch_id=command.branch_id,
                                    event_id=selection.finals_event_id,
                                )
                                if item.command_id == command.command_id
                            ),
                            None,
                        )
                        if (
                            revision is None
                            or revision.main_process_window_ordinal
                            != command.main_process_window_ordinal
                            or revision.repair_draw_seed != command.repair_draw_seed
                        ):
                            raise ValueError(
                                "Finals replacement command ID has different Draw repair context"
                            )
                    elif (
                        command.main_process_window_ordinal is not None
                        or command.repair_draw_seed is not None
                    ):
                        raise ValueError(
                            "Pre-draw Finals replacement cannot carry Draw repair context"
                        )
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
                draw = TournamentDrawAuthorityStore(session).get_initial(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    event_id=selection.finals_event_id,
                )
                if draw is None:
                    if (
                        command.main_process_window_ordinal is not None
                        or command.repair_draw_seed is not None
                    ):
                        raise ValueError(
                            "Pre-draw Finals replacement cannot carry Draw repair context"
                        )
                    TournamentEntryFieldStore(
                        session
                    ).stage_from_finals_effective_participant_state(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=selection.finals_event_id,
                        target_season_index=command.target_season_index,
                        expected_effective_state_fingerprint=successor.fingerprint,
                        command_id=(
                            f"finals-replacement-entry:{successor.fingerprint[:64]}"
                        ),
                    )
                else:
                    if command.main_process_window_ordinal is None:
                        raise ValueError(
                            "Post-draw Finals replacement requires Main process-window ordinal"
                        )
                    TournamentDrawRevisionStore(
                        session
                    ).apply_finals_race_replacement(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        event_id=selection.finals_event_id,
                        command_id=command.command_id,
                        withdrawn_player_id=authority.withdrawn_player_id,
                        effective_state_fingerprint=successor.fingerprint,
                        main_process_window_ordinal=(
                            command.main_process_window_ordinal
                        ),
                        repair_draw_seed=command.repair_draw_seed,
                    )
            return authority
