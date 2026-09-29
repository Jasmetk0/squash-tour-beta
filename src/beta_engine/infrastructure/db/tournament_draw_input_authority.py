"""Persistence for immutable Run/Branch tournament draw input commitment."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentDrawInputAuthorityModel,
)
from beta_engine.infrastructure.db.finals_participant_selection import (
    WorldTourFinalsParticipantSelectionStore,
)
from beta_engine.infrastructure.db.finals_race_replacement import (
    WorldTourFinalsReplacementStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)


class TournamentDrawInputAuthorityConflict(ValueError):
    """A committed draw input or command identity conflicts with stored authority."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentDrawInputAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Draw Input Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Draw Input scope is not writable")

    def _command_row(
        self, *, run_id: str, branch_id: str, command_id: str
    ) -> TournamentDrawInputAuthorityModel | None:
        return self.session.scalar(
            select(TournamentDrawInputAuthorityModel).where(
                TournamentDrawInputAuthorityModel.run_id == run_id,
                TournamentDrawInputAuthorityModel.branch_id == branch_id,
                TournamentDrawInputAuthorityModel.command_id == command_id,
            )
        )

    @classmethod
    def validate_row(
        cls,
        row: TournamentDrawInputAuthorityModel,
        *,
        field,
        field_sequence: int,
        ranking_authority=None,
        wild_card_authority=None,
        finals_selection=None,
        finals_effective_state=None,
        format_authority=None,
    ) -> TournamentDrawInputAuthority:
        """Validate one frozen row against already-resolved target dependencies."""

        committed = TournamentDrawInputAuthority.model_validate_json(row.payload_json)
        if (
            committed.run_id,
            committed.branch_id,
            committed.event_id,
            committed.committed_by_command_id,
            committed.field_sequence,
            committed.entry_field_fingerprint,
            committed.source_authority_fingerprint,
            committed.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.field_sequence,
            row.entry_field_fingerprint,
            row.ranking_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament Draw Input authority is corrupt")
        if row.field_sequence != field_sequence:
            raise ValueError(
                "Tournament Draw Input authority no longer references the terminal Entry Field"
            )
        if field.fingerprint != row.entry_field_fingerprint:
            raise ValueError(
                "Tournament Draw Input authority Entry Field fingerprint is stale"
            )

        if committed.source_kind in {
            "finals_participant_selection",
            "finals_effective_participant_state",
        }:
            if finals_selection is None or format_authority is None:
                raise ValueError(
                    "Finals Draw Input authority references missing Finals/Format authority"
                )
            if (
                finals_selection.fingerprint
                != committed.finals_participant_selection_fingerprint
                or finals_selection.race_snapshot_fingerprint
                != committed.finals_race_snapshot_fingerprint
                or format_authority.fingerprint
                != committed.tournament_format_authority_fingerprint
            ):
                raise ValueError(
                    "Finals Draw Input source authority fingerprint is stale"
                )
            if committed.source_kind == "finals_effective_participant_state":
                if (
                    finals_effective_state is None
                    or finals_effective_state.fingerprint
                    != committed.finals_effective_participant_state_fingerprint
                ):
                    raise ValueError(
                        "Effective Finals Draw Input references missing/stale participant state"
                    )
            elif finals_effective_state is not None:
                raise ValueError(
                    "Initial Finals Draw Input cannot carry effective participant state"
                )
            rebuilt = TournamentDrawInputAuthorityBuilder.build_finals_knockout(
                selection=finals_selection,
                field=field,
                field_sequence=field_sequence,
                format_authority=format_authority,
                command_id=row.command_id,
                draw_seed=committed.draw_seed,
                effective_state=finals_effective_state,
            )
            expected_request = cls._finals_request(
                source_kind=committed.source_kind,
                finals_participant_selection_fingerprint=finals_selection.fingerprint,
                finals_effective_participant_state_fingerprint=(
                    finals_effective_state.fingerprint
                    if finals_effective_state is not None
                    else None
                ),
                finals_race_snapshot_fingerprint=finals_selection.race_snapshot_fingerprint,
                tournament_format_authority_fingerprint=format_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                draw_seed=committed.draw_seed,
                main_seed_count=committed.main_seed_count,
                bye_slots=committed.capacity.bye_slots,
            )
        else:
            if ranking_authority is None:
                raise ValueError(
                    "Tournament Draw Input authority references missing ranking authority"
                )
            if ranking_authority.fingerprint != row.ranking_authority_fingerprint:
                raise ValueError(
                    "Tournament Draw Input authority ranking fingerprint is stale"
                )
            rebuilt = TournamentDrawInputAuthorityBuilder.build(
                authority=ranking_authority,
                field=field,
                field_sequence=field_sequence,
                command_id=row.command_id,
                draw_seed=committed.draw_seed,
                main_seed_count=committed.main_seed_count,
                qualification_seed_count=committed.qualification_seed_count,
                schema_version=committed.schema_version,
                wild_card_authority=wild_card_authority,
            )
            expected_request = cls._request(
                ranking_authority_fingerprint=ranking_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                draw_seed=committed.draw_seed,
                main_seed_count=committed.main_seed_count,
                qualification_seed_count=committed.qualification_seed_count,
                wild_card_authority_fingerprint=committed.wild_card_authority_fingerprint,
            )

        if rebuilt != committed:
            raise ValueError(
                "Tournament Draw Input authority does not replay from frozen inputs"
            )
        if row.request_fingerprint != _request_fingerprint(expected_request):
            raise ValueError(
                "Tournament Draw Input authority request fingerprint is corrupt"
            )
        return committed

    def _load_row(
        self, row: TournamentDrawInputAuthorityModel
    ) -> TournamentDrawInputAuthority:
        history = TournamentEntryFieldStore(self.session).history(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if not history:
            raise ValueError(
                "Tournament Draw Input authority references missing Entry Field history"
            )
        field = history[-1]
        committed = TournamentDrawInputAuthority.model_validate_json(row.payload_json)
        if committed.source_kind in {
            "finals_participant_selection",
            "finals_effective_participant_state",
        }:
            finals_selection = WorldTourFinalsParticipantSelectionStore(
                self.session
            ).find_snapshot_for_event(
                run_id=row.run_id,
                branch_id=row.branch_id,
                event_id=row.event_id,
            )
            finals_effective_state = None
            if (
                committed.source_kind == "finals_effective_participant_state"
                and finals_selection is not None
            ):
                finals_effective_state = next(
                    (
                        state
                        for state in WorldTourFinalsReplacementStore(
                            self.session
                        ).state_history(
                            run_id=row.run_id,
                            branch_id=row.branch_id,
                            target_season_index=finals_selection.target_season_index,
                        )
                        if state.fingerprint
                        == committed.finals_effective_participant_state_fingerprint
                    ),
                    None,
                )
            format_authority = TournamentFormatAuthorityStore(self.session).get(
                run_id=row.run_id,
                branch_id=row.branch_id,
                event_id=row.event_id,
            )
            return self.validate_row(
                row,
                field=field,
                field_sequence=len(history),
                finals_selection=finals_selection,
                finals_effective_state=finals_effective_state,
                format_authority=format_authority,
            )

        ranking_authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
        )
        if ranking_authority is None:
            raise ValueError(
                "Tournament Draw Input authority references missing ranking authority"
            )
        wild_card_authority = (
            TournamentWildCardAuthorityStore(self.session).get(
                run_id=row.run_id,
                branch_id=row.branch_id,
                event_id=row.event_id,
            )
            if field.capacity.wild_card_slots
            else None
        )
        return self.validate_row(
            row,
            field=field,
            field_sequence=len(history),
            ranking_authority=ranking_authority,
            wild_card_authority=wild_card_authority,
        )

    @staticmethod
    def _request(
        *,
        ranking_authority_fingerprint: str,
        entry_field_fingerprint: str,
        field_sequence: int,
        draw_seed: int,
        main_seed_count: int,
        qualification_seed_count: int,
        wild_card_authority_fingerprint: str | None = None,
    ) -> dict:
        return {
            "ranking_authority_fingerprint": ranking_authority_fingerprint,
            "entry_field_fingerprint": entry_field_fingerprint,
            "field_sequence": field_sequence,
            "draw_seed": draw_seed,
            "main_seed_count": main_seed_count,
            "qualification_seed_count": qualification_seed_count,
            "wild_card_authority_fingerprint": wild_card_authority_fingerprint,
        }

    @staticmethod
    def _finals_request(
        *,
        source_kind: str,
        finals_participant_selection_fingerprint: str,
        finals_effective_participant_state_fingerprint: str | None,
        finals_race_snapshot_fingerprint: str,
        tournament_format_authority_fingerprint: str,
        entry_field_fingerprint: str,
        field_sequence: int,
        draw_seed: int,
        main_seed_count: int,
        bye_slots: int,
    ) -> dict:
        return {
            "source_kind": source_kind,
            "finals_participant_selection_fingerprint": (
                finals_participant_selection_fingerprint
            ),
            "finals_effective_participant_state_fingerprint": (
                finals_effective_participant_state_fingerprint
            ),
            "finals_race_snapshot_fingerprint": finals_race_snapshot_fingerprint,
            "tournament_format_authority_fingerprint": (
                tournament_format_authority_fingerprint
            ),
            "entry_field_fingerprint": entry_field_fingerprint,
            "field_sequence": field_sequence,
            "draw_seed": draw_seed,
            "main_seed_count": main_seed_count,
            "qualification_seed_count": 0,
            "bye_slots": bye_slots,
        }

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentDrawInputAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        )
        return None if row is None else self._load_row(row)

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        draw_seed: int,
        main_seed_count: int | None = None,
        qualification_seed_count: int | None = None,
    ) -> TournamentDrawInputAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament Draw Input requires a valid command ID")

        history = TournamentEntryFieldStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not history:
            raise ValueError(
                "Tournament Draw Input requires a persisted Tournament Entry Field"
            )
        field = history[-1]
        field_sequence = len(history)

        if field.source_kind in {
            "finals_participant_selection",
            "finals_effective_participant_state",
        }:
            if main_seed_count is not None or qualification_seed_count is not None:
                raise ValueError(
                    "Finals Draw Input derives seed counts from canonical bracket policy"
                )
            finals_selection = WorldTourFinalsParticipantSelectionStore(
                self.session
            ).find_snapshot_for_event(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if finals_selection is None:
                raise ValueError(
                    "Finals Draw Input requires frozen participant-selection authority"
                )
            finals_effective_state = None
            if field.source_kind == "finals_effective_participant_state":
                finals_effective_state = WorldTourFinalsReplacementStore(
                    self.session
                ).latest_state(
                    run_id=run_id,
                    branch_id=branch_id,
                    target_season_index=finals_selection.target_season_index,
                )
                if (
                    finals_effective_state is None
                    or finals_effective_state.fingerprint
                    != field.finals_effective_participant_state_fingerprint
                ):
                    raise ValueError(
                        "Finals Draw Input requires latest effective replacement state"
                    )
            format_authority = TournamentFormatAuthorityStore(self.session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if format_authority is None:
                raise ValueError(
                    "Finals Draw Input requires configured tournament-format authority"
                )
            proposed = TournamentDrawInputAuthorityBuilder.build_finals_knockout(
                selection=finals_selection,
                field=field,
                field_sequence=field_sequence,
                format_authority=format_authority,
                command_id=command_id,
                draw_seed=draw_seed,
                effective_state=finals_effective_state,
            )
            request = self._finals_request(
                source_kind=proposed.source_kind,
                finals_participant_selection_fingerprint=finals_selection.fingerprint,
                finals_effective_participant_state_fingerprint=(
                    finals_effective_state.fingerprint
                    if finals_effective_state is not None
                    else None
                ),
                finals_race_snapshot_fingerprint=finals_selection.race_snapshot_fingerprint,
                tournament_format_authority_fingerprint=format_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                draw_seed=draw_seed,
                main_seed_count=proposed.main_seed_count,
                bye_slots=proposed.capacity.bye_slots,
            )
        else:
            ranking_authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if ranking_authority is None:
                raise ValueError(
                    "Tournament Draw Input requires Tournament Ranking Snapshot authority"
                )
            wild_card_authority = (
                TournamentWildCardAuthorityStore(self.session).get(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                )
                if field.capacity.wild_card_slots
                else None
            )

            # New ranking-sourced commitments use v3 when canonical WC authority is
            # required, otherwise they retain the Master-aligned v2 contract.
            proposed = TournamentDrawInputAuthorityBuilder.build(
                authority=ranking_authority,
                field=field,
                field_sequence=field_sequence,
                command_id=command_id,
                draw_seed=draw_seed,
                main_seed_count=main_seed_count,
                qualification_seed_count=qualification_seed_count,
                schema_version=(
                    "tournament_draw_input_authority.v3"
                    if field.capacity.wild_card_slots
                    else "tournament_draw_input_authority.v2"
                ),
                wild_card_authority=wild_card_authority,
            )
            request = self._request(
                ranking_authority_fingerprint=ranking_authority.fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                draw_seed=draw_seed,
                main_seed_count=proposed.main_seed_count,
                qualification_seed_count=proposed.qualification_seed_count,
                wild_card_authority_fingerprint=proposed.wild_card_authority_fingerprint,
            )

        request_fp = _request_fingerprint(request)
        retry = self._command_row(
            run_id=run_id,
            branch_id=branch_id,
            command_id=command_id,
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentDrawInputAuthorityConflict(
                    "Tournament Draw Input command ID already has a different request"
                )
            return self._load_row(retry)

        existing = self.session.get(
            TournamentDrawInputAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentDrawInputAuthorityConflict(
                "Tournament event already has committed Draw Input authority"
            )

        self.session.add(
            TournamentDrawInputAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                # Compatibility storage column: old rows carry Ranking authority;
                # Finals v10 rows carry participant-selection source authority.
                ranking_authority_fingerprint=proposed.source_authority_fingerprint,
                entry_field_fingerprint=field.fingerprint,
                field_sequence=field_sequence,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed

