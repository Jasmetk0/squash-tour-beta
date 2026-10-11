"""Persistence for immutable season-versioned group-rules policy."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.format_authority import (
    TournamentGroupMatchBestOf,
    TournamentGroupRulesPolicy,
)
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    TournamentGroupRulesPolicyModel,
)


class TournamentGroupRulesPolicyConflict(ValueError):
    """A group-rules version conflicts with immutable history."""


class TournamentGroupRulesPolicyStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament group-rules Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament group-rules scope is not writable")

    @staticmethod
    def validate_row(row: TournamentGroupRulesPolicyModel) -> TournamentGroupRulesPolicy:
        policy = TournamentGroupRulesPolicy.model_validate_json(row.payload_json)
        if (
            policy.run_id,
            policy.branch_id,
            policy.effective_from_season_index,
            policy.adopted_by_command_id,
            policy.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.effective_from_season_index,
            row.command_id,
            row.authority_fingerprint,
        ):
            raise ValueError("Stored Tournament group-rules policy is corrupt")
        return policy

    def list_versions(
        self, *, run_id: str, branch_id: str
    ) -> tuple[TournamentGroupRulesPolicy, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(TournamentGroupRulesPolicyModel)
            .where(
                TournamentGroupRulesPolicyModel.run_id == run_id,
                TournamentGroupRulesPolicyModel.branch_id == branch_id,
            )
            .order_by(TournamentGroupRulesPolicyModel.effective_from_season_index)
        ).all()
        return tuple(self.validate_row(row) for row in rows)

    def get_by_fingerprint(
        self,
        *,
        run_id: str,
        branch_id: str,
        authority_fingerprint: str,
    ) -> TournamentGroupRulesPolicy | None:
        self._scope(run_id, branch_id)
        row = self.session.scalar(
            select(TournamentGroupRulesPolicyModel).where(
                TournamentGroupRulesPolicyModel.run_id == run_id,
                TournamentGroupRulesPolicyModel.branch_id == branch_id,
                TournamentGroupRulesPolicyModel.authority_fingerprint
                == authority_fingerprint,
            )
        )
        return None if row is None else self.validate_row(row)

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_season_index: int,
    ) -> TournamentGroupRulesPolicy | None:
        if not 0 <= target_season_index <= 49:
            raise ValueError("Tournament group-rules target season is outside Run timeline")
        versions = self.list_versions(run_id=run_id, branch_id=branch_id)
        candidates = tuple(
            value
            for value in versions
            if value.effective_from_season_index <= target_season_index
        )
        return candidates[-1] if candidates else None

    def adopt(
        self,
        *,
        run_id: str,
        branch_id: str,
        effective_from_season_index: int,
        command_id: str,
        default_match_best_of: TournamentGroupMatchBestOf,
    ) -> TournamentGroupRulesPolicy:
        self._scope(run_id, branch_id, writing=True)
        if not 0 <= effective_from_season_index <= 49:
            raise ValueError("Tournament group-rules effective season is outside Run timeline")
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Tournament group-rules policy requires a valid command ID")

        proposed = TournamentGroupRulesPolicy(
            run_id=run_id,
            branch_id=branch_id,
            effective_from_season_index=effective_from_season_index,
            default_match_best_of=default_match_best_of,
            adopted_by_command_id=command_id,
        )
        command_row = self.session.scalar(
            select(TournamentGroupRulesPolicyModel).where(
                TournamentGroupRulesPolicyModel.run_id == run_id,
                TournamentGroupRulesPolicyModel.branch_id == branch_id,
                TournamentGroupRulesPolicyModel.command_id == command_id,
            )
        )
        if command_row is not None:
            stored = self.validate_row(command_row)
            if stored != proposed:
                raise TournamentGroupRulesPolicyConflict(
                    "Tournament group-rules command ID already has a different request"
                )
            return stored

        existing = self.session.get(
            TournamentGroupRulesPolicyModel,
            (run_id, branch_id, effective_from_season_index),
        )
        if existing is not None:
            stored = self.validate_row(existing)
            if stored == proposed:
                return stored
            raise TournamentGroupRulesPolicyConflict(
                "Tournament group-rules version already exists for this effective season"
            )

        self.session.add(
            TournamentGroupRulesPolicyModel(
                run_id=run_id,
                branch_id=branch_id,
                effective_from_season_index=effective_from_season_index,
                command_id=command_id,
                authority_fingerprint=proposed.fingerprint,
                payload_json=proposed.model_dump_json(),
            )
        )
        self.session.flush()
        return proposed
