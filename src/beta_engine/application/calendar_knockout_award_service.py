"""Review/confirm/Save of native four-player knockout points (not Official).

The policy is operator-authored, with a versioned source and immutable Signed
Saved capture. There is no Category/Event configuration provenance yet, and
Week 2 Official publication is deliberately not performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import text

from beta_engine.application.calendar_standalone_match_service import CalendarStandaloneMatchService
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_knockout_awards_state import (
    CalendarKnockoutPointPolicy, CalendarScoredOpeningKnockout,
    derive_knockout_prepared_awards,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    CalendarOpeningKnockout, load_match_rows, load_saved_calendar_match,
    replace_saved_knockout_with_prepared_awards,
)


class CalendarAwardProposal(FrozenInput):
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_knockout_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: CalendarKnockoutPointPolicy
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)


class CalendarAwardApplyCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    proposal: CalendarAwardProposal
    expected_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    explicit_confirmation: Literal[True]


@dataclass(slots=True)
class CalendarKnockoutAwardService:
    repository: object

    def _source(self, session, *, run_id: str, branch_id: str,
                proposal: CalendarAwardProposal):
        clock, revision, _ = CalendarStandaloneMatchService(
            self.repository
        )._context(session, run_id=run_id, branch_id=branch_id)
        if revision.saved_head_revision_id != proposal.expected_saved_head:
            raise ValueError("Saved HEAD changed since prepared award review")
        rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
        if len(rows) != 1 or not isinstance(rows[0], CalendarOpeningKnockout):
            raise ValueError("Prepared points require a real Saved four-player knockout")
        knockout = rows[0]
        saved = load_saved_calendar_match(
            revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
        )
        if (
            not isinstance(saved, CalendarOpeningKnockout)
            or saved.fingerprint != knockout.fingerprint
            or knockout.fingerprint != proposal.expected_knockout_fingerprint
        ):
            raise ValueError("Knockout is not the exact Signed Saved HEAD evidence")
        if proposal.policy.validity_weeks != clock.weeks_per_year:
            raise ValueError("Ranking validity must equal the Run year W for this supported policy")
        if clock.weeks_per_year < 2:
            raise ValueError("Opening knockout publication requires an existing Week 2")
        return clock, revision, knockout

    @staticmethod
    def _prepared(*, clock, revision, knockout, run_id, branch_id,
                  proposal: CalendarAwardProposal) -> dict:
        awards = derive_knockout_prepared_awards(knockout, proposal.policy)
        target = RunWeekPosition(calendar=clock, season_index=0, week=2)
        preview_fp = canonical_hash({
            "schema_version": "calendar_knockout_award_review.v1",
            "run_id": run_id, "branch_id": branch_id,
            "saved_head_revision_id": revision.saved_head_revision_id,
            "saved_head_content_hash": revision.saved_revision.content_hash,
            "source_knockout_fingerprint": knockout.fingerprint,
            "proposal": proposal.model_dump(mode="json"),
            "first_publication_week": target.model_dump(mode="json"),
            "prepared_awards": [a.model_dump(mode="json") for a in awards],
        })
        return {
            "schema_version": "calendar_knockout_award_review.v1",
            "run_id": run_id, "branch_id": branch_id,
            "source_saved_head": revision.saved_head_revision_id,
            "source_knockout_fingerprint": knockout.fingerprint,
            "first_publication_week": target.model_dump(mode="json"),
            "policy_fingerprint": proposal.policy.fingerprint,
            "awards": [a.model_dump(mode="json") for a in awards],
            "preview_fingerprint": preview_fp,
            "publication_status": "prepared_not_official",
        }

    def review(self, *, run_id: str, branch_id: str,
               proposal: CalendarAwardProposal) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock, revision, knockout = self._source(
                session, run_id=run_id, branch_id=branch_id, proposal=proposal
            )
            return self._prepared(clock=clock, revision=revision, knockout=knockout,
                                  run_id=run_id, branch_id=branch_id, proposal=proposal)

    def apply(self, *, run_id: str, branch_id: str,
              command: CalendarAwardApplyCommand) -> dict:
        request_fp = canonical_hash({
            "run_id": run_id, "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
        })
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            # Check the existing persisted command first for exact response-loss
            # retry. A changed payload, duplicate ID or a different scored
            # tournament must not be accepted.
            existing = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            if len(existing) == 1 and isinstance(existing[0], CalendarScoredOpeningKnockout):
                scored = existing[0]
                if scored.command_id != command.command_id or scored.request_fingerprint != request_fp:
                    raise ValueError("Knockout already has different prepared point awards")
                return {"prepared": scored.model_dump(mode="json"),
                        "fingerprint": scored.fingerprint}
            clock, revision, knockout = self._source(
                session, run_id=run_id, branch_id=branch_id, proposal=command.proposal
            )
            prepared = self._prepared(
                clock=clock, revision=revision, knockout=knockout,
                run_id=run_id, branch_id=branch_id, proposal=command.proposal,
            )
            if prepared["preview_fingerprint"] != command.expected_preview_fingerprint:
                raise ValueError("Knockout policy review changed since confirmation")
            policy = command.proposal.policy
            scored = CalendarScoredOpeningKnockout(
                run_id=run_id, branch_id=branch_id, match_id=knockout.match_id,
                command_id=command.command_id, request_fingerprint=request_fp,
                source_saved_head=revision.saved_head_revision_id,
                source_initial_world_fingerprint=knockout.source_initial_world_fingerprint,
                week=knockout.week, knockout=knockout,
                knockout_fingerprint=knockout.fingerprint,
                policy=policy,
                first_publication_week=RunWeekPosition(
                    calendar=clock, season_index=0, week=2
                ),
                awards=derive_knockout_prepared_awards(knockout, policy),
                operator_label=command.proposal.operator_label,
                audit_reason=command.proposal.audit_reason,
            )
            replace_saved_knockout_with_prepared_awards(
                session, original=knockout, scored=scored,
            )
            return {"prepared": scored.model_dump(mode="json"),
                    "fingerprint": scored.fingerprint}
