"""Single SQLite transaction owner for canonical Week Transition publication."""

from __future__ import annotations

import json

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.authoritative_week_transition import (
    AuthoritativeWeekTransitionCommand,
    AuthoritativeWeekTransitionResult,
)
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.infrastructure.db.models import (
    AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel,
    AuthoritativeWorldStateModel,
    BranchWorkingDraftModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    RunProspectModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)
from beta_engine.infrastructure.db.ranking_transition_authority import (
    RankingTransitionAuthorityStore,
    authority_carried_to_saved_head,
)
from beta_engine.infrastructure.db.ranking_week_command import (
    stage_ranking_week_command,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    transition_lifecycle,
)
from beta_engine.domain.rankings.official import (
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.domain.calendar.season_weeks import season_week_to_calendar_position


def _fault_injection_point(_name: str) -> None:
    """Test seam for proving rollback at otherwise unreachable failure points."""


def _world_event_payload(
    command, ranking_fingerprint: str, lifecycle_fingerprint: str
) -> str:
    return json.dumps(
        {
            "audit": command.audit.model_dump(mode="json"),
            "completed_week": command.completed_week.model_dump(mode="json"),
            "target_week": command.target_week.model_dump(mode="json"),
            "official_ranking_fingerprint": ranking_fingerprint,
            "player_lifecycle_fingerprint": lifecycle_fingerprint,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class AuthoritativeWeekTransitionRunner:
    def __init__(self, factory: sessionmaker[Session], awards=None):
        self.factory = factory
        self.awards = awards

    def preview(self, command: AuthoritativeWeekTransitionCommand):
        with self.factory() as session:
            try:
                session.execute(text("BEGIN IMMEDIATE"))
                return transition_in_transaction(session, self.awards, command)
            finally:
                session.rollback()

    def execute(
        self,
        command: AuthoritativeWeekTransitionCommand,
        *,
        expected_ranking_fingerprint=None,
    ):
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            result = transition_in_transaction(session, self.awards, command)
            if (
                expected_ranking_fingerprint is not None
                and result.official_ranking_fingerprint != expected_ranking_fingerprint
            ):
                raise ValueError("Week Transition inputs changed since preview")
            return result


def transition_in_transaction(session: Session, awards, command):
    """Validate, calculate, publish, advance and audit without an inner commit."""
    command = AuthoritativeWeekTransitionCommand.model_validate_json(
        command.model_dump_json()
    )
    key = (command.run_id, command.branch_id, command.command_id)
    receipt = session.get(AuthoritativeWeekTransitionReceiptModel, key)
    if receipt is not None:
        if (
            receipt.request_fingerprint != command.fingerprint
            or receipt.request_payload_json != command.canonical_request_json
        ):
            raise ValueError(
                "Week Transition command ID already has a different request"
            )
        result = AuthoritativeWeekTransitionResult.model_validate_json(
            receipt.result_json
        )
        if (
            result.run_id,
            result.branch_id,
            result.command_id,
            result.completed_week,
            result.target_week,
        ) != (
            command.run_id,
            command.branch_id,
            command.command_id,
            command.completed_week,
            command.target_week,
        ):
            raise ValueError("Completed Week Transition receipt identity is corrupt")
        publication = session.get(
            PublishedOfficialRankingModel,
            (command.run_id, command.branch_id, result.target_week.ordinal),
        )
        event = session.get(AuthoritativeWorldEventModel, key)
        world = session.get(
            AuthoritativeWorldStateModel, (command.run_id, command.branch_id)
        )
        if (
            publication is None
            or event is None
            or world is None
            or (
                publication.snapshot_fingerprint != result.official_ranking_fingerprint
                or world.current_ordinal < result.target_week.ordinal
                or event.run_id != command.run_id
                or event.branch_id != command.branch_id
                or event.command_id != command.command_id
                or event.week_ordinal != result.target_week.ordinal
                or event.event_kind != result.world_event_kind
                or event.payload_json
                != _world_event_payload(
                    command,
                    result.official_ranking_fingerprint,
                    result.player_lifecycle_fingerprint,
                )
            )
        ):
            raise ValueError("Completed Week Transition receipt is corrupt")
        load_official_ranking_snapshot(
            publication.payload_json,
            expected_fingerprint=publication.snapshot_fingerprint,
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=result.target_week,
        )
        head_publication = session.get(
            PublishedOfficialRankingModel,
            (command.run_id, command.branch_id, world.current_ordinal),
        )
        if (
            head_publication is None
            or head_publication.snapshot_fingerprint != world.ranking_fingerprint
        ):
            raise ValueError("Authoritative world ranking head is corrupt")
        load_official_ranking_snapshot(
            head_publication.payload_json,
            expected_fingerprint=head_publication.snapshot_fingerprint,
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=RankingWeek(
                season_index=world.current_ordinal // 61,
                week=world.current_ordinal % 61 + 1,
            ),
        )
        lifecycle = get_lifecycle(
            session,
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=result.target_week,
        )
        if lifecycle is None:
            raise ValueError("Completed Week Transition player lifecycle is missing")
        if lifecycle.fingerprint != result.player_lifecycle_fingerprint:
            raise ValueError("Completed Week Transition player lifecycle is corrupt")
        return result

    run = session.get(RunContainerModel, command.run_id)
    branch = session.get(RunBranchModel, command.branch_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == command.branch_id
        )
    )
    if (
        run is None
        or branch is None
        or draft is None
        or branch.run_id != command.run_id
    ):
        raise ValueError("Week Transition Run/Branch scope does not exist")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError("Week Transition requires a writable active Run/Branch")
    if (
        branch.saved_head_revision_id != command.base_revision_id
        or draft.base_revision_id != command.base_revision_id
    ):
        raise ValueError("Week Transition base/current Saved Revision changed")
    if draft.status != "clean":
        raise ValueError("Week Transition requires a clean Working Draft")

    authority = RankingTransitionAuthorityStore(session).get(
        run_id=command.run_id,
        branch_id=command.branch_id,
        target_ordinal=command.target_week.ordinal,
    )
    if authority is None or authority.fingerprint != command.authority_fingerprint:
        raise ValueError("Ranking transition authority changed")
    if not authority_carried_to_saved_head(session, authority, branch, draft):
        raise ValueError("Ranking transition authority base revision is stale")
    if (authority.completed_week, authority.target_week) != (
        command.completed_week,
        command.target_week,
    ):
        raise ValueError("Ranking transition authority boundary differs")

    target_position = season_week_to_calendar_position(
        2000 + command.target_week.season_index, command.target_week.week
    )
    pending_prospect = session.scalar(
        select(RunProspectModel.prospect_id)
        .where(
            RunProspectModel.run_id == command.run_id,
            RunProspectModel.season_start_year
            == 2000 + command.target_week.season_index,
            RunProspectModel.season_week == command.target_week.week,
            RunProspectModel.calendar_year == target_position.calendar_year,
            RunProspectModel.year_week == target_position.year_week,
        )
        .limit(1)
    )
    if pending_prospect is not None:
        raise ValueError(
            "Target week has Run-scoped prospect intake but no authoritative "
            "Run/Branch-owned player source bridge"
        )

    candidates = OfficialRankingCandidateStore(session).history(
        run_id=command.run_id, branch_id=command.branch_id
    )
    predecessor = next(
        (value for value in candidates if value.week == command.completed_week), None
    )
    if predecessor is None or candidates[-1].week != command.completed_week:
        raise ValueError("Current predecessor Official Ranking candidate is missing")
    world = session.get(
        AuthoritativeWorldStateModel, (command.run_id, command.branch_id)
    )
    if world is None:
        if command.completed_week.ordinal != 0:
            raise ValueError("Authoritative world clock is missing")
        session.add(
            PublishedOfficialRankingModel(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week_ordinal=0,
                snapshot_fingerprint=predecessor.fingerprint,
                payload_json=predecessor.model_dump_json(),
            )
        )
        world = AuthoritativeWorldStateModel(
            run_id=command.run_id,
            branch_id=command.branch_id,
            current_ordinal=0,
            ranking_fingerprint=predecessor.fingerprint,
        )
        session.add(world)
        session.flush()
    elif (
        world.current_ordinal != command.completed_week.ordinal
        or world.ranking_fingerprint != predecessor.fingerprint
    ):
        raise ValueError("Authoritative world predecessor state differs")

    lifecycle = transition_lifecycle(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed=command.completed_week,
        target=command.target_week,
    )
    _fault_injection_point("after_lifecycle_staging")
    derived_players = lifecycle.ranking_roster()
    authority_identity = tuple(
        (p.player_id, p.tie_break_token, p.tour_entry_week) for p in authority.players
    )
    derived_identity = tuple(
        (p.player_id, p.tie_break_token, p.tour_entry_week) for p in derived_players
    )
    if authority_identity != derived_identity:
        raise ValueError(
            "Ranking transition roster identity differs from authoritative player lifecycle state"
        )

    ranking_command = RankingWeekCommand(
        command_id=f"{command.command_id}:ranking",
        context=RankingTransitionContext(
            run_id=command.run_id,
            branch_id=command.branch_id,
            completed_week=authority.completed_week,
            target_week=authority.target_week,
            policy=authority.policy,
            players=derived_players,
            discipline="stored_zeros",
        ),
        tournaments=command.tournaments,
        corrections=command.corrections,
        zero_versions=command.zero_versions,
        audit=command.audit,
        authority_fingerprint=authority.fingerprint,
    )
    snapshot = stage_ranking_week_command(session, awards, ranking_command)
    _fault_injection_point("after_ranking_staging")
    if (
        session.get(
            PublishedOfficialRankingModel,
            (command.run_id, command.branch_id, command.target_week.ordinal),
        )
        is not None
    ):
        raise ValueError("Official Ranking target is already published")
    _fault_injection_point("before_publication")
    session.add(
        PublishedOfficialRankingModel(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week_ordinal=command.target_week.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()  # publication exists before the remaining atomic writes
    _fault_injection_point("after_publication")
    world.current_ordinal = command.target_week.ordinal
    world.ranking_fingerprint = snapshot.fingerprint
    event_payload = _world_event_payload(
        command, snapshot.fingerprint, lifecycle.fingerprint
    )
    session.add(
        AuthoritativeWorldEventModel(
            run_id=command.run_id,
            branch_id=command.branch_id,
            command_id=command.command_id,
            week_ordinal=command.target_week.ordinal,
            event_kind="week_transition_completed",
            payload_json=event_payload,
        )
    )
    result = AuthoritativeWeekTransitionResult(
        run_id=command.run_id,
        branch_id=command.branch_id,
        command_id=command.command_id,
        completed_week=command.completed_week,
        target_week=command.target_week,
        official_ranking_fingerprint=snapshot.fingerprint,
        player_lifecycle_fingerprint=lifecycle.fingerprint,
    )
    session.add(
        AuthoritativeWeekTransitionReceiptModel(
            run_id=command.run_id,
            branch_id=command.branch_id,
            command_id=command.command_id,
            request_fingerprint=command.fingerprint,
            request_payload_json=command.canonical_request_json,
            result_json=result.model_dump_json(),
        )
    )
    session.flush()
    return result
