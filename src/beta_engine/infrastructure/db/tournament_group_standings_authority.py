"""Persistence/replay for immutable tournament group standings authority."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupResultReceipt,
    TournamentGroupStandingsAuthority,
    TournamentGroupStandingsBuilder,
    TournamentGroupTieResolutionDecision,
)
from beta_engine.domain.tournaments.group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthority,
)
from beta_engine.infrastructure.db.authoritative_group_state import (
    load_authoritative_group,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    TournamentGroupStandingsAuthorityModel,
    TournamentGroupTieResolutionAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityStore,
)


class TournamentGroupStandingsAuthorityConflict(ValueError):
    """A standings command conflicts with immutable Tournament Edition history."""


def _request_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupStandingsAuthorityStore:
    """Freeze one final group table from the exact canonical result receipts."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Group Standings Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Group Standings scope is not writable")

    @staticmethod
    def _request(
        *,
        schedule_fingerprint: str,
        receipts: tuple[TournamentGroupResultReceipt, ...],
        resolutions: tuple[TournamentGroupTieResolutionDecision, ...] = (),
        include_resolutions: bool = True,
    ) -> dict:
        payload = {
            "group_match_schedule_fingerprint": schedule_fingerprint,
            "source_results": [
                [receipt.match_id, receipt.result_fingerprint]
                for receipt in receipts
            ],
            "scoring_policy_id": "master_group_table_points.v1",
            "tie_break_policy_id": "wins_points_h2h_ratios_admin_unresolved.v1",
            "walkover_policy_id": "group_wo_win_max_points_no_fabricated_ratios.v1",
        }
        if include_resolutions:
            payload["admin_tie_resolution_fingerprints"] = [
                decision.fingerprint for decision in resolutions
            ]
        return payload

    def _result_receipts(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        schedule,
    ) -> tuple[TournamentGroupResultReceipt, ...]:
        match_by_id = {match.match_id: match for match in schedule.matches}
        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.match_id.in_(tuple(match_by_id)),
            )
        ).all()
        by_match: dict[str, TournamentGroupResultReceipt] = {}
        for row in rows:
            decoded = load_authoritative_group(row)
            source = decoded.authoritative_input
            if source.event_id != event_id:
                continue
            scheduled = match_by_id.get(row.match_id)
            if scheduled is None:
                continue
            if row.match_id in by_match:
                raise ValueError(
                    "Group Standings found duplicate canonical result receipt"
                )
            by_match[row.match_id] = TournamentGroupStandingsBuilder.receipt_from_result(
                scheduled_match=scheduled,
                result=decoded.result,
                result_fingerprint=decoded.result_fingerprint,
            )

        missing = tuple(
            match.match_id
            for match in schedule.matches
            if match.match_id not in by_match
        )
        if missing:
            raise ValueError(
                "Group Standings requires completed canonical result receipts for: "
                + ", ".join(missing)
            )
        return tuple(by_match[match.match_id] for match in schedule.matches)

    def _tie_resolution_decisions(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        schedule,
    ) -> tuple[TournamentGroupTieResolutionDecision, ...]:
        rows = self.session.scalars(
            select(TournamentGroupTieResolutionAuthorityModel)
            .where(
                TournamentGroupTieResolutionAuthorityModel.run_id == run_id,
                TournamentGroupTieResolutionAuthorityModel.branch_id == branch_id,
                TournamentGroupTieResolutionAuthorityModel.event_id == event_id,
            )
            .order_by(TournamentGroupTieResolutionAuthorityModel.case_fingerprint)
        ).all()
        decisions = []
        for row in rows:
            authority = TournamentGroupTieResolutionAuthority.model_validate_json(
                row.payload_json
            )
            if (
                authority.run_id,
                authority.branch_id,
                authority.event_id,
                authority.resolved_by_command_id,
                authority.case.fingerprint,
                authority.group_match_schedule_fingerprint,
                authority.fingerprint,
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
            if authority.group_match_schedule_fingerprint != schedule.fingerprint:
                raise ValueError("Group Tie Resolution references stale Match Schedule")
            decisions.append(authority.decision)
        return tuple(decisions)

    def validate_row(
        self,
        row: TournamentGroupStandingsAuthorityModel,
        *,
        schedule,
    ) -> TournamentGroupStandingsAuthority:
        authority = TournamentGroupStandingsAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.group_match_schedule_fingerprint,
            authority.group_rules_policy_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.group_match_schedule_fingerprint,
            row.group_rules_policy_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Group Standings authority is corrupt")
        if authority.group_match_schedule_fingerprint != schedule.fingerprint:
            raise ValueError("Group Standings references stale Match Schedule")
        if (
            authority.group_rules_policy_fingerprint
            != schedule.group_rules_policy_fingerprint
        ):
            raise ValueError("Group Standings references stale group rules")

        receipts = self._result_receipts(
            run_id=row.run_id,
            branch_id=row.branch_id,
            event_id=row.event_id,
            schedule=schedule,
        )
        resolutions = (
            ()
            if authority.schema_version == "tournament_group_standings_authority.v1"
            else self._tie_resolution_decisions(
                run_id=row.run_id,
                branch_id=row.branch_id,
                event_id=row.event_id,
                schedule=schedule,
            )
        )
        rebuilt = TournamentGroupStandingsBuilder.build(
            schedule=schedule,
            receipts=receipts,
            command_id=row.command_id,
            admin_tie_resolutions=resolutions,
            schema_version=authority.schema_version,
        )
        if rebuilt != authority:
            raise ValueError(
                "Group Standings does not replay from frozen schedule/results"
            )
        request = self._request(
            schedule_fingerprint=schedule.fingerprint,
            receipts=receipts,
            resolutions=resolutions,
            include_resolutions=(
                authority.schema_version
                == "tournament_group_standings_authority.v2"
            ),
        )
        if row.request_fingerprint != _request_fingerprint(request):
            raise ValueError("Group Standings request fingerprint is corrupt")
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentGroupStandingsAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentGroupStandingsAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if row is None:
            return None
        schedule = TournamentGroupMatchScheduleAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if schedule is None:
            raise ValueError("Group Standings references missing Match Schedule")
        return self.validate_row(row, schedule=schedule)

    def generate(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> TournamentGroupStandingsAuthority:
        self._scope(run_id, branch_id, writing=True)
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Group Standings requires a valid command ID")

        schedule = TournamentGroupMatchScheduleAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if schedule is None:
            raise ValueError("Group Standings requires frozen Group Match Schedule")
        receipts = self._result_receipts(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            schedule=schedule,
        )
        resolutions = self._tie_resolution_decisions(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            schedule=schedule,
        )
        proposed = TournamentGroupStandingsBuilder.build(
            schedule=schedule,
            receipts=receipts,
            command_id=command_id,
            admin_tie_resolutions=resolutions,
        )
        request = self._request(
            schedule_fingerprint=schedule.fingerprint,
            receipts=receipts,
            resolutions=resolutions,
        )
        request_fp = _request_fingerprint(request)

        retry = self.session.scalar(
            select(TournamentGroupStandingsAuthorityModel).where(
                TournamentGroupStandingsAuthorityModel.run_id == run_id,
                TournamentGroupStandingsAuthorityModel.branch_id == branch_id,
                TournamentGroupStandingsAuthorityModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.event_id != event_id or retry.request_fingerprint != request_fp:
                raise TournamentGroupStandingsAuthorityConflict(
                    "Group Standings command ID already has a different request"
                )
            return self.validate_row(retry, schedule=schedule)

        existing = self.session.get(
            TournamentGroupStandingsAuthorityModel,
            (run_id, branch_id, event_id),
        )
        if existing is not None:
            raise TournamentGroupStandingsAuthorityConflict(
                "Tournament Edition already has immutable Group Standings authority"
            )

        self.session.add(
            TournamentGroupStandingsAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command_id,
                request_fingerprint=request_fp,
                authority_fingerprint=proposed.fingerprint,
                group_match_schedule_fingerprint=schedule.fingerprint,
                group_rules_policy_fingerprint=schedule.group_rules_policy_fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
