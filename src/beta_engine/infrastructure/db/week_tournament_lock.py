"""Persistence and canonical derivation for explicit Week Tournament Locks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.week_tournament_lock import (
    WeekTournamentLockAuthority,
    WeekTournamentLockEventEvidence,
    WeekTournamentPlayerLock,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    WeekTournamentLockAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)


class WeekTournamentLockConflict(ValueError):
    """Week Tournament Lock identity or current field evidence changed."""


@dataclass(frozen=True)
class WeekTournamentLockCommit:
    authority: WeekTournamentLockAuthority
    exact_retry: bool


def _request(
    *,
    week: RankingWeek,
    event_ids: tuple[str, ...] | list[str],
    selections: dict[str, str],
    command_id: str,
    operator_label: str,
    audit_reason: str,
) -> dict:
    return {
        "week": week.model_dump(mode="json"),
        "event_ids": list(sorted(set(event_ids))),
        "selections": {
            player_id: selections[player_id] for player_id in sorted(selections)
        },
        "command_id": command_id,
        "operator_label": operator_label,
        "audit_reason": audit_reason,
    }


def _fp(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def derive_week_tournament_lock_authority(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    event_ids: tuple[str, ...] | list[str],
    selections: dict[str, str],
    command_id: str,
    operator_label: str,
    audit_reason: str,
) -> WeekTournamentLockAuthority:
    canonical_event_ids = tuple(sorted(set(event_ids)))
    if not canonical_event_ids:
        raise ValueError("Week Tournament Lock requires current-week tournament events")
    if len(canonical_event_ids) != len(tuple(event_ids)):
        raise ValueError("Week Tournament Lock event IDs must be unique")

    evidence = []
    for event_id in canonical_event_ids:
        field = TournamentEntryFieldStore(session).latest(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if field is None:
            raise ValueError(
                f"Week Tournament Lock requires a canonical Entry Field for event {event_id}"
            )
        accepted = tuple(
            sorted(
                set(field.direct_main_player_ids)
                | set(field.qualification_player_ids)
            )
        )
        evidence.append(
            WeekTournamentLockEventEvidence(
                event_id=event_id,
                entry_field_fingerprint=field.fingerprint,
                accepted_player_ids=accepted,
            )
        )

    accepted_by_player: dict[str, list[str]] = {}
    for item in evidence:
        for player_id in item.accepted_player_ids:
            accepted_by_player.setdefault(player_id, []).append(item.event_id)
    conflicts = {
        player_id: tuple(sorted(set(events)))
        for player_id, events in accepted_by_player.items()
        if len(set(events)) > 1
    }
    if set(selections) != set(conflicts):
        missing = sorted(set(conflicts) - set(selections))
        extra = sorted(set(selections) - set(conflicts))
        details = []
        if missing:
            details.append("missing selections: " + ", ".join(missing))
        if extra:
            details.append("non-conflicting selections: " + ", ".join(extra))
        raise ValueError(
            "Week Tournament Lock selections must cover every and only conflict"
            + (": " + "; ".join(details) if details else "")
        )

    locks = tuple(
        WeekTournamentPlayerLock(
            player_id=player_id,
            eligible_event_ids=conflicts[player_id],
            selected_event_id=selections[player_id],
        )
        for player_id in sorted(conflicts)
    )
    return WeekTournamentLockAuthority(
        run_id=run_id,
        branch_id=branch_id,
        week=week,
        resolved_by_command_id=command_id,
        operator_label=operator_label,
        audit_reason=audit_reason,
        event_evidence=tuple(evidence),
        player_locks=locks,
    )


class WeekTournamentLockStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Week Tournament Lock Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Week Tournament Lock Run/Branch scope is not writable")

    @staticmethod
    def _load(row: WeekTournamentLockAuthorityModel) -> WeekTournamentLockAuthority:
        authority = WeekTournamentLockAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.week.ordinal,
            authority.resolved_by_command_id,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.week_ordinal,
            row.command_id,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Week Tournament Lock authority is corrupt")
        return authority

    def get(
        self, *, run_id: str, branch_id: str, week_ordinal: int
    ) -> WeekTournamentLockAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WeekTournamentLockAuthorityModel,
            (run_id, branch_id, week_ordinal),
        )
        return None if row is None else self._load(row)

    def list(
        self, *, run_id: str, branch_id: str
    ) -> tuple[WeekTournamentLockAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(WeekTournamentLockAuthorityModel)
            .where(
                WeekTournamentLockAuthorityModel.run_id == run_id,
                WeekTournamentLockAuthorityModel.branch_id == branch_id,
            )
            .order_by(WeekTournamentLockAuthorityModel.week_ordinal)
        ).all()
        return tuple(self._load(row) for row in rows)

    def commit(
        self,
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        event_ids: tuple[str, ...] | list[str],
        selections: dict[str, str],
        command_id: str,
        operator_label: str,
        audit_reason: str,
        expected_authority_fingerprint: str,
    ) -> WeekTournamentLockCommit:
        self._scope(run_id, branch_id, writing=True)
        request_fp = _fp(
            _request(
                week=week,
                event_ids=event_ids,
                selections=selections,
                command_id=command_id,
                operator_label=operator_label,
                audit_reason=audit_reason,
            )
        )
        existing = self.session.get(
            WeekTournamentLockAuthorityModel,
            (run_id, branch_id, week.ordinal),
        )
        if existing is not None:
            loaded = self._load(existing)
            if (
                existing.command_id == command_id
                and existing.request_fingerprint == request_fp
                and loaded.fingerprint == expected_authority_fingerprint
            ):
                return WeekTournamentLockCommit(
                    authority=loaded,
                    exact_retry=True,
                )
            raise WeekTournamentLockConflict(
                "Week Tournament Lock is already immutable for this week"
            )

        authority = derive_week_tournament_lock_authority(
            self.session,
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            event_ids=event_ids,
            selections=selections,
            command_id=command_id,
            operator_label=operator_label,
            audit_reason=audit_reason,
        )
        if authority.fingerprint != expected_authority_fingerprint:
            raise WeekTournamentLockConflict(
                "Week Tournament Lock changed since preview"
            )
        self.session.add(
            WeekTournamentLockAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=authority.fingerprint,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return WeekTournamentLockCommit(
            authority=authority,
            exact_retry=False,
        )
