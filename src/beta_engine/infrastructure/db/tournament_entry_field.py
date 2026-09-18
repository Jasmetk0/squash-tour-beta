"""Append-only Run/Branch tournament field state derived from frozen ranking authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryField,
    TournamentEntryFieldCapacity,
    TournamentEntryFieldResolver,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentEntryFieldVersionModel,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


class TournamentEntryFieldConflict(ValueError):
    """A field command or predecessor no longer matches authoritative state."""


def _canonical_applications(
    applications: tuple[TournamentEntryApplication, ...] | list[TournamentEntryApplication],
) -> tuple[TournamentEntryApplication, ...]:
    canonical = tuple(
        sorted(
            (
                TournamentEntryApplication.model_validate_json(app.model_dump_json())
                for app in applications
            ),
            key=lambda app: app.application_id,
        )
    )
    application_ids = [app.application_id for app in canonical]
    if len(application_ids) != len(set(application_ids)):
        raise ValueError("Duplicate Tournament Entry/Application identity")
    return canonical


def _applications_json(
    applications: tuple[TournamentEntryApplication, ...],
) -> str:
    return json.dumps(
        [app.model_dump(mode="json") for app in applications],
        sort_keys=True,
        separators=(",", ":"),
    )


def _applications_fingerprint(
    applications: tuple[TournamentEntryApplication, ...],
) -> str:
    return hashlib.sha256(_applications_json(applications).encode()).hexdigest()


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentEntryFieldStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament entry field Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament entry field scope is not writable")

    def _rows(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> tuple[TournamentEntryFieldVersionModel, ...]:
        return tuple(
            self.session.scalars(
                select(TournamentEntryFieldVersionModel)
                .where(
                    TournamentEntryFieldVersionModel.run_id == run_id,
                    TournamentEntryFieldVersionModel.branch_id == branch_id,
                    TournamentEntryFieldVersionModel.event_id == event_id,
                )
                .order_by(TournamentEntryFieldVersionModel.sequence)
            ).all()
        )

    def _command_row(
        self, *, run_id: str, branch_id: str, command_id: str
    ) -> TournamentEntryFieldVersionModel | None:
        return self.session.scalar(
            select(TournamentEntryFieldVersionModel).where(
                TournamentEntryFieldVersionModel.run_id == run_id,
                TournamentEntryFieldVersionModel.branch_id == branch_id,
                TournamentEntryFieldVersionModel.command_id == command_id,
            )
        )

    @staticmethod
    def _load_row(
        row: TournamentEntryFieldVersionModel,
    ) -> tuple[TournamentEntryField, tuple[TournamentEntryApplication, ...]]:
        field = TournamentEntryField.model_validate_json(row.payload_json)
        raw_apps = json.loads(row.applications_json)
        if not isinstance(raw_apps, list):
            raise ValueError("Stored Tournament Entry/Application payload is invalid")
        applications = _canonical_applications(
            [TournamentEntryApplication.model_validate(value) for value in raw_apps]
        )
        applications_json = _applications_json(applications)
        applications_fp = _applications_fingerprint(applications)
        if applications_json != row.applications_json:
            raise ValueError(
                "Stored Tournament Entry/Application ordering is not canonical"
            )
        if (
            field.run_id,
            field.branch_id,
            field.event_id,
            field.fingerprint,
            field.base_field_fingerprint,
            field.tournament_ranking_authority_fingerprint,
            field.applications_fingerprint,
            applications_fp,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.field_fingerprint,
            row.predecessor_fingerprint,
            row.ranking_authority_fingerprint,
            row.applications_fingerprint,
            row.applications_fingerprint,
        ):
            raise ValueError("Stored Tournament Entry Field row is corrupt")
        return field, applications

    @classmethod
    def validate_rows(
        cls,
        rows: tuple[TournamentEntryFieldVersionModel, ...]
        | list[TournamentEntryFieldVersionModel],
        *,
        authority,
    ) -> tuple[TournamentEntryField, ...]:
        ordered = tuple(sorted(rows, key=lambda row: row.sequence))
        if not ordered:
            return ()
        if [row.sequence for row in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("Tournament entry field version sequence has a gap")

        result: list[TournamentEntryField] = []
        previous: TournamentEntryField | None = None
        for row in ordered:
            field, applications = cls._load_row(row)
            if (row.run_id, row.branch_id, row.event_id) != (
                authority.run_id,
                authority.branch_id,
                authority.event_id,
            ):
                raise ValueError(
                    "Tournament Entry Field row scope differs from ranking authority"
                )
            if row.sequence == 1:
                if field.mode != "initial" or previous is not None:
                    raise ValueError(
                        "First Tournament Entry Field version must be initial"
                    )
                rebuilt = TournamentEntryFieldResolver.build_initial(
                    authority=authority,
                    applications=applications,
                    capacity=field.capacity,
                )
                expected_request_fingerprint = _request_fingerprint(
                    {
                        "mode": "initial",
                        "run_id": authority.run_id,
                        "branch_id": authority.branch_id,
                        "event_id": authority.event_id,
                        "authority_fingerprint": authority.fingerprint,
                        "applications_fingerprint": field.applications_fingerprint,
                        "capacity": field.capacity.model_dump(mode="json"),
                    }
                )
            else:
                if previous is None or field.mode != "pre_draw_repair":
                    raise ValueError(
                        "Later Tournament Entry Field versions must be pre-draw repairs"
                    )
                if field.base_field_fingerprint != previous.fingerprint:
                    raise ValueError(
                        "Tournament Entry Field predecessor fingerprint is corrupt"
                    )
                newly_withdrawn = tuple(
                    sorted(
                        set(field.withdrawn_player_ids)
                        - set(previous.withdrawn_player_ids)
                    )
                )
                if not newly_withdrawn:
                    raise ValueError(
                        "Persisted Tournament Entry Field repair has no new withdrawal"
                    )
                rebuilt = TournamentEntryFieldResolver.repair_pre_draw(
                    authority=authority,
                    applications=applications,
                    previous=previous,
                    withdrawn_player_ids=newly_withdrawn,
                )
                expected_request_fingerprint = _request_fingerprint(
                    {
                        "mode": "pre_draw_repair",
                        "run_id": authority.run_id,
                        "branch_id": authority.branch_id,
                        "event_id": authority.event_id,
                        "authority_fingerprint": authority.fingerprint,
                        "applications_fingerprint": field.applications_fingerprint,
                        "predecessor_fingerprint": previous.fingerprint,
                        "withdrawn_player_ids": newly_withdrawn,
                    }
                )
            if rebuilt != field:
                raise ValueError(
                    "Tournament Entry Field does not replay from frozen authoritative inputs"
                )
            if row.request_fingerprint != expected_request_fingerprint:
                raise ValueError(
                    "Tournament Entry Field command request fingerprint is corrupt"
                )
            if not row.command_id.strip() or len(row.command_id) > 128:
                raise ValueError("Tournament Entry Field command identity is corrupt")
            result.append(field)
            previous = field
        return tuple(result)

    def history(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> tuple[TournamentEntryField, ...]:
        self._scope(run_id, branch_id)
        rows = self._rows(run_id=run_id, branch_id=branch_id, event_id=event_id)
        if not rows:
            return ()
        authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if authority is None:
            raise ValueError(
                "Tournament entry field references missing Tournament Ranking Snapshot authority"
            )
        return self.validate_rows(rows, authority=authority)

    def latest(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentEntryField | None:
        history = self.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
        return history[-1] if history else None

    def stage_initial(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        applications: tuple[TournamentEntryApplication, ...]
        | list[TournamentEntryApplication],
        capacity: TournamentEntryFieldCapacity,
        command_id: str,
    ) -> TournamentEntryField:
        self._scope(run_id, branch_id, writing=True)
        authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if authority is None:
            raise ValueError(
                "Tournament entry field requires Tournament Ranking Snapshot authority"
            )
        canonical_apps = _canonical_applications(applications)
        apps_fp = _applications_fingerprint(canonical_apps)
        request_fp = _request_fingerprint(
            {
                "mode": "initial",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "authority_fingerprint": authority.fingerprint,
                "applications_fingerprint": apps_fp,
                "capacity": capacity.model_dump(mode="json"),
            }
        )
        retry = self._command_row(
            run_id=run_id, branch_id=branch_id, command_id=command_id
        )
        if retry is not None:
            field, frozen_apps = self._load_row(retry)
            if (
                retry.request_fingerprint != request_fp
                or frozen_apps != canonical_apps
                or field.mode != "initial"
            ):
                raise TournamentEntryFieldConflict(
                    "Tournament entry field command ID already has a different request"
                )
            return field

        if self._rows(run_id=run_id, branch_id=branch_id, event_id=event_id):
            raise TournamentEntryFieldConflict(
                "Tournament entry field already exists for this event"
            )

        field = TournamentEntryFieldResolver.build_initial(
            authority=authority,
            applications=canonical_apps,
            capacity=capacity,
        )
        self._append(
            field=field,
            applications=canonical_apps,
            command_id=command_id,
            request_fingerprint=request_fp,
            sequence=1,
        )
        return field

    def stage_pre_draw_repair(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        applications: tuple[TournamentEntryApplication, ...]
        | list[TournamentEntryApplication],
        withdrawn_player_ids: tuple[str, ...] | list[str],
        command_id: str,
    ) -> TournamentEntryField:
        self._scope(run_id, branch_id, writing=True)
        authority = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if authority is None:
            raise ValueError(
                "Tournament entry field requires Tournament Ranking Snapshot authority"
            )
        canonical_apps = _canonical_applications(applications)
        apps_fp = _applications_fingerprint(canonical_apps)
        requested = tuple(sorted(set(withdrawn_player_ids)))

        retry = self._command_row(
            run_id=run_id, branch_id=branch_id, command_id=command_id
        )
        if retry is not None:
            field, frozen_apps = self._load_row(retry)
            retry_fp = _request_fingerprint(
                {
                    "mode": "pre_draw_repair",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "event_id": event_id,
                    "authority_fingerprint": authority.fingerprint,
                    "applications_fingerprint": apps_fp,
                    "predecessor_fingerprint": retry.predecessor_fingerprint,
                    "withdrawn_player_ids": requested,
                }
            )
            if (
                retry.request_fingerprint != retry_fp
                or frozen_apps != canonical_apps
                or field.mode != "pre_draw_repair"
            ):
                raise TournamentEntryFieldConflict(
                    "Tournament entry field command ID already has a different request"
                )
            return field

        previous = self.latest(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if previous is None:
            raise TournamentEntryFieldConflict(
                "Pre-draw repair requires an initial Tournament Entry Field"
            )
        request_fp = _request_fingerprint(
            {
                "mode": "pre_draw_repair",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "authority_fingerprint": authority.fingerprint,
                "applications_fingerprint": apps_fp,
                "predecessor_fingerprint": previous.fingerprint,
                "withdrawn_player_ids": requested,
            }
        )
        field = TournamentEntryFieldResolver.repair_pre_draw(
            authority=authority,
            applications=canonical_apps,
            previous=previous,
            withdrawn_player_ids=requested,
        )
        if field == previous:
            raise TournamentEntryFieldConflict(
                "Tournament entry field repair contains no new withdrawal"
            )
        self._append(
            field=field,
            applications=canonical_apps,
            command_id=command_id,
            request_fingerprint=request_fp,
            sequence=len(
                self._rows(run_id=run_id, branch_id=branch_id, event_id=event_id)
            )
            + 1,
        )
        return field

    def _append(
        self,
        *,
        field: TournamentEntryField,
        applications: tuple[TournamentEntryApplication, ...],
        command_id: str,
        request_fingerprint: str,
        sequence: int,
    ) -> None:
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament entry field requires a valid command ID")
        self.session.add(
            TournamentEntryFieldVersionModel(
                run_id=field.run_id,
                branch_id=field.branch_id,
                event_id=field.event_id,
                sequence=sequence,
                command_id=command_id,
                request_fingerprint=request_fingerprint,
                field_fingerprint=field.fingerprint,
                predecessor_fingerprint=field.base_field_fingerprint,
                ranking_authority_fingerprint=(
                    field.tournament_ranking_authority_fingerprint
                ),
                applications_fingerprint=field.applications_fingerprint,
                applications_json=_applications_json(applications),
                payload_json=field.model_dump_json(),
            )
        )
        self.session.flush()
