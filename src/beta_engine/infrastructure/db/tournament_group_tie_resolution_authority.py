"""Persistence and preview flow for explicit Admin group tie resolution."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder,
    TournamentGroupStandingsTieCase,
    TournamentGroupStandingsUnresolvedTie,
    TournamentGroupTieResolutionDecision,
)
from beta_engine.domain.tournaments.group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthority,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentGroupStandingsAuthorityModel,
    TournamentGroupTieResolutionAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityStore,
)


class TournamentGroupTieResolutionAuthorityConflict(ValueError):
    """An Admin tie-resolution command conflicts with immutable evidence/history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupTieResolutionAuthorityStore:
    """Resolve only the exact unresolved case exposed by current canonical evidence."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Group Tie Resolution Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Group Tie Resolution scope is not writable")

    @staticmethod
    def _request(
        *,
        schedule_fingerprint: str,
        case: TournamentGroupStandingsTieCase,
        ordered_player_ids: tuple[str, ...],
        admin_reason: str,
    ) -> dict:
        return {
            "group_match_schedule_fingerprint": schedule_fingerprint,
            "case_fingerprint": case.fingerprint,
            "ordered_player_ids": list(ordered_player_ids),
            "admin_reason": admin_reason,
        }

    def list_authorities(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> tuple[TournamentGroupTieResolutionAuthority, ...]:
        self._scope(run_id, branch_id)
        schedule = TournamentGroupMatchScheduleAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if schedule is None:
            return ()
        rows = self.session.scalars(
            select(TournamentGroupTieResolutionAuthorityModel)
            .where(
                TournamentGroupTieResolutionAuthorityModel.run_id == run_id,
                TournamentGroupTieResolutionAuthorityModel.branch_id == branch_id,
                TournamentGroupTieResolutionAuthorityModel.event_id == event_id,
            )
            .order_by(TournamentGroupTieResolutionAuthorityModel.case_fingerprint)
        ).all()
        values = []
        for row in rows:
            value = TournamentGroupTieResolutionAuthority.model_validate_json(
                row.payload_json
            )
            if (
                value.run_id,
                value.branch_id,
                value.event_id,
                value.resolved_by_command_id,
                value.case.fingerprint,
                value.group_match_schedule_fingerprint,
                value.fingerprint,
            ) != (
                row.run_id,
                row.branch_id,
                row.event_id,
                row.command_id,
                row.case_fingerprint,
                row.group_match_schedule_fingerprint,
                row.authority_fingerprint,
            ):
                raise ValueError("Stored Group Tie Resolution authority is corrupt")
            if value.group_match_schedule_fingerprint != schedule.fingerprint:
                raise ValueError("Group Tie Resolution references stale Match Schedule")
            request = self._request(
                schedule_fingerprint=schedule.fingerprint,
                case=value.case,
                ordered_player_ids=value.decision.ordered_player_ids,
                admin_reason=value.decision.admin_reason,
            )
            if row.request_fingerprint != _request_fingerprint(request):
                raise ValueError("Group Tie Resolution request fingerprint is corrupt")
            values.append(value)
        return tuple(values)

    def current_unresolved_case(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentGroupStandingsTieCase | None:
        self._scope(run_id, branch_id)
        if self.session.get(
            TournamentGroupStandingsAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            return None
        schedule = TournamentGroupMatchScheduleAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if schedule is None:
            raise ValueError("Group Tie Resolution requires frozen Group Match Schedule")

        standings_store = TournamentGroupStandingsAuthorityStore(self.session)
        receipts = standings_store._result_receipts(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            schedule=schedule,
        )
        decisions = tuple(
            authority.decision
            for authority in self.list_authorities(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
        )
        try:
            TournamentGroupStandingsBuilder.build(
                schedule=schedule,
                receipts=receipts,
                command_id="preview-group-standings-resolution",
                admin_tie_resolutions=decisions,
            )
        except TournamentGroupStandingsUnresolvedTie as exc:
            return exc.case
        return None

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        case_fingerprint: str,
        ordered_player_ids: tuple[str, ...],
        admin_reason: str,
    ) -> TournamentGroupTieResolutionAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Group Tie Resolution requires a valid command ID")
        if len(case_fingerprint) != 64:
            raise ValueError("Group Tie Resolution requires a case fingerprint")
        normalized_reason = admin_reason.strip()
        if not normalized_reason:
            raise ValueError("Group Tie Resolution requires an Admin reason")
        schedule = TournamentGroupMatchScheduleAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if schedule is None:
            raise ValueError("Group Tie Resolution requires frozen Group Match Schedule")

        # Completed command replay must remain idempotent even after this decision
        # moved the standings pipeline forward or final standings were frozen.
        retry = self.session.scalar(
            select(TournamentGroupTieResolutionAuthorityModel).where(
                TournamentGroupTieResolutionAuthorityModel.run_id == run_id,
                TournamentGroupTieResolutionAuthorityModel.branch_id == branch_id,
                TournamentGroupTieResolutionAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            values = self.list_authorities(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            value = next(
                (
                    item
                    for item in values
                    if item.resolved_by_command_id == command_id
                ),
                None,
            )
            if value is None:
                raise ValueError("Stored Group Tie Resolution command is corrupt")
            request = self._request(
                schedule_fingerprint=schedule.fingerprint,
                case=value.case,
                ordered_player_ids=value.decision.ordered_player_ids,
                admin_reason=value.decision.admin_reason,
            )
            if (
                retry.event_id != event_id
                or retry.case_fingerprint != case_fingerprint
                or value.case.fingerprint != case_fingerprint
                or value.decision.ordered_player_ids != ordered_player_ids
                or value.decision.admin_reason != normalized_reason
                or retry.request_fingerprint != _request_fingerprint(request)
            ):
                raise TournamentGroupTieResolutionAuthorityConflict(
                    "Group Tie Resolution command ID already has a different request"
                )
            return value

        if self.session.get(
            TournamentGroupStandingsAuthorityModel,
            (run_id, branch_id, event_id),
        ) is not None:
            raise TournamentGroupTieResolutionAuthorityConflict(
                "Final Group Standings already exist and cannot be re-ordered"
            )

        case = self.current_unresolved_case(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if case is None:
            raise TournamentGroupTieResolutionAuthorityConflict(
                "Current group evidence has no unresolved tie requiring Admin resolution"
            )
        if case.fingerprint != case_fingerprint:
            raise TournamentGroupTieResolutionAuthorityConflict(
                "Group Tie Resolution case is stale or differs from current evidence"
            )

        decision = TournamentGroupTieResolutionDecision(
            case=case,
            ordered_player_ids=ordered_player_ids,
            admin_reason=normalized_reason,
        )
        proposed = TournamentGroupTieResolutionAuthority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            resolved_by_command_id=command_id,
            group_match_schedule_fingerprint=schedule.fingerprint,
            decision=decision,
        )
        request = self._request(
            schedule_fingerprint=schedule.fingerprint,
            case=case,
            ordered_player_ids=decision.ordered_player_ids,
            admin_reason=decision.admin_reason,
        )
        request_fp = _request_fingerprint(request)

        existing = self.session.get(
            TournamentGroupTieResolutionAuthorityModel,
            (run_id, branch_id, event_id, case.fingerprint),
        )
        if existing is not None:
            raise TournamentGroupTieResolutionAuthorityConflict(
                "This unresolved tie case already has an immutable Admin resolution"
            )

        self.session.add(
            TournamentGroupTieResolutionAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                case_fingerprint=case.fingerprint,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                group_match_schedule_fingerprint=schedule.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
