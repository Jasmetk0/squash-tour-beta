"""Atomic ordinary Season Transition writer for seasons 0-48."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from beta_engine.application.season_closing_ranking_resolution import (
    stage_canonical_season_closing_ranking,
)
from beta_engine.application.season_closure_resolution import (
    resolve_canonical_season_closure_package,
)
from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    stage_season_transition_lifecycle,
)
from beta_engine.application.season_transition_ranking import (
    stage_season_transition_ranking,
)
from beta_engine.application.season_transition_sporting import (
    stage_season_transition_sporting,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.run_containers import is_pre_completion_run_status
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    ORDINARY_SEASON_TRANSITION_AUDIT_EVENT_KIND,
    ORDINARY_SEASON_TRANSITION_SAVED_REVISION_KIND,
    RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
    saved_revision_content_hash,
    viewer_branch_saved_revision_payload,
)
from beta_engine.domain.season_closure import bind_season_closure_marker
from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
)
from beta_engine.infrastructure.db.initial_world_state import capture_saved_initial_world
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldEventModel,
    AuthoritativeWorldStateModel,
    BranchRevisionAuditEventModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    capture_saved_lifecycle,
    get_lifecycle,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    capture_saved_sporting,
    get_sporting,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    capture_saved_ranking_component,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
)


WORLD_EVENT_KIND = "season_transition_completed"


class OrdinarySeasonTransitionCommand(FrozenInput):
    schema_version: Literal["ordinary_season_transition_command.v1"] = (
        "ordinary_season_transition_command.v1"
    )
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    configuration: SeasonTransitionConfiguration
    expected_preflight_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_saved_revision_id: str = Field(min_length=1)
    expected_draft_version: int = Field(ge=0)
    next_saved_revision_id: str = Field(min_length=1, max_length=128)
    audit_event_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.configuration.run_id, self.configuration.branch_id) != (
            self.run_id,
            self.branch_id,
        ):
            raise ValueError("Season Transition command/configuration scope mismatch")
        if self.configuration.completed_week.season_index >= 49:
            raise ValueError("Ordinary Season Transition cannot target the final season")
        if self.configuration.base_revision_id != self.expected_saved_revision_id:
            raise ValueError("Season Transition configuration/base revision mismatch")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class OrdinarySeasonTransitionResult(FrozenInput):
    schema_version: Literal["ordinary_season_transition_result.v1"] = (
        "ordinary_season_transition_result.v1"
    )
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    target_week: RankingWeek
    saved_revision_id: str
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    closing_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    season_summary_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    closure_marker_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    player_sporting_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    player_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    official_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_event_kind: Literal["season_transition_completed"] = WORLD_EVENT_KIND
    draft_version: int = Field(ge=0)


def _revision_payload(row: BranchSavedRevisionModel) -> tuple[dict, dict]:
    try:
        payload = json.loads(row.payload_json)
        summary = json.loads(row.change_summary_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Season Transition Saved Revision JSON is corrupt") from exc
    if not isinstance(payload, dict) or not isinstance(summary, dict):
        raise ValueError("Season Transition Saved Revision payload is corrupt")
    expected = saved_revision_content_hash(
        revision_id=row.revision_id,
        run_id=row.run_id,
        branch_id=row.branch_id,
        sequence=row.sequence,
        parent_revision_id=row.parent_revision_id,
        kind=row.kind,
        payload_schema_version=row.payload_schema_version,
        payload=payload,
        change_summary=summary,
    )
    if row.content_hash_algorithm != CONTENT_HASH_ALGORITHM or row.content_hash != expected:
        raise ValueError("Season Transition Saved Revision content hash is corrupt")
    return payload, summary


def _world_event_payload(
    command: OrdinarySeasonTransitionCommand,
    *,
    closing_fingerprint: str,
    summary_fingerprint: str,
    marker_fingerprint: str,
    sporting_fingerprint: str,
    lifecycle_fingerprint: str,
    ranking_fingerprint: str,
) -> str:
    return json.dumps(
        {
            "schema_version": "season_transition_world_event.v1",
            "command_id": command.command_id,
            "configuration_fingerprint": command.configuration.fingerprint,
            "completed_week": command.configuration.completed_week.model_dump(mode="json"),
            "target_week": command.configuration.target_week.model_dump(mode="json"),
            "closing_ranking_fingerprint": closing_fingerprint,
            "season_summary_fingerprint": summary_fingerprint,
            "closure_marker_fingerprint": marker_fingerprint,
            "player_sporting_fingerprint": sporting_fingerprint,
            "player_lifecycle_fingerprint": lifecycle_fingerprint,
            "official_ranking_fingerprint": ranking_fingerprint,
            "saved_revision_id": command.next_saved_revision_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _retry_result(
    session: Session,
    command: OrdinarySeasonTransitionCommand,
) -> OrdinarySeasonTransitionResult | None:
    revision = session.get(BranchSavedRevisionModel, command.next_saved_revision_id)
    if revision is None:
        return None

    branch = session.get(RunBranchModel, command.branch_id)
    run = session.get(RunContainerModel, command.run_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == command.branch_id
        )
    )
    audit = session.scalar(
        select(BranchRevisionAuditEventModel).where(
            BranchRevisionAuditEventModel.saved_revision_id
            == command.next_saved_revision_id
        )
    )
    if (
        revision.run_id != command.run_id
        or revision.branch_id != command.branch_id
        or revision.kind != ORDINARY_SEASON_TRANSITION_SAVED_REVISION_KIND
        or branch is None
        or branch.saved_head_revision_id != command.next_saved_revision_id
        or run is None
        or not is_pre_completion_run_status(run.status)
        or draft is None
        or draft.base_revision_id != command.next_saved_revision_id
        or audit is None
        or audit.audit_event_id != command.audit_event_id
        or audit.event_kind != ORDINARY_SEASON_TRANSITION_AUDIT_EVENT_KIND
    ):
        raise ValueError("Season Transition retry identity is already in conflict")

    payload, _ = _revision_payload(revision)
    try:
        audit_payload = json.loads(audit.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Season Transition audit is corrupt") from exc
    if audit_payload.get("request_fingerprint") != command.fingerprint:
        raise ValueError("Season Transition command retry has different inputs")

    closure = load_saved_revision_season_closure(
        payload,
        run_id=command.run_id,
        branch_id=command.branch_id,
        revision_id=command.next_saved_revision_id,
    )
    if closure is None:
        raise ValueError("Season Transition Saved Revision lost closure evidence")
    summary = closure.parsed_summary
    marker = closure.parsed_marker

    publication = session.get(
        PublishedOfficialRankingModel,
        (command.run_id, command.branch_id, command.configuration.target_week.ordinal),
    )
    world = session.get(AuthoritativeWorldStateModel, (command.run_id, command.branch_id))
    lifecycle = get_lifecycle(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        week=command.configuration.target_week,
    )
    sporting = get_sporting(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        week=command.configuration.target_week,
    )
    event = session.get(
        AuthoritativeWorldEventModel,
        (command.run_id, command.branch_id, command.command_id),
    )
    if (
        publication is None
        or world is None
        or lifecycle is None
        or sporting is None
        or event is None
        or world.current_ordinal != command.configuration.target_week.ordinal
        or world.ranking_fingerprint != publication.snapshot_fingerprint
        or event.week_ordinal != command.configuration.target_week.ordinal
        or event.event_kind != WORLD_EVENT_KIND
        or marker.final_saved_revision_id != command.next_saved_revision_id
    ):
        raise ValueError("Committed Season Transition state is corrupt")

    expected_event = _world_event_payload(
        command,
        closing_fingerprint=marker.closing_ranking_fingerprint,
        summary_fingerprint=summary.fingerprint,
        marker_fingerprint=marker.fingerprint,
        sporting_fingerprint=sporting.fingerprint,
        lifecycle_fingerprint=lifecycle.fingerprint,
        ranking_fingerprint=publication.snapshot_fingerprint,
    )
    if event.payload_json != expected_event:
        raise ValueError("Committed Season Transition World Event is corrupt")

    return OrdinarySeasonTransitionResult(
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=command.configuration.completed_week,
        target_week=command.configuration.target_week,
        saved_revision_id=command.next_saved_revision_id,
        configuration_fingerprint=command.configuration.fingerprint,
        closing_ranking_fingerprint=marker.closing_ranking_fingerprint,
        season_summary_fingerprint=summary.fingerprint,
        closure_marker_fingerprint=marker.fingerprint,
        player_sporting_fingerprint=sporting.fingerprint,
        player_lifecycle_fingerprint=lifecycle.fingerprint,
        official_ranking_fingerprint=publication.snapshot_fingerprint,
        draft_version=draft.draft_version,
    )


def commit_ordinary_season_transition(
    session: Session,
    command: OrdinarySeasonTransitionCommand,
    *,
    fault_at: str | None = None,
) -> OrdinarySeasonTransitionResult:
    """Commit one complete Week-61 -> next-season Week-1 transition atomically."""

    if not session.in_transaction():
        raise ValueError("Season Transition requires a caller transaction")

    retry = _retry_result(session, command)
    if retry is not None:
        return retry

    configuration = validate_season_transition_configuration(
        session,
        command.configuration,
    )
    if configuration.reset_catalog.component_ids:
        raise ValueError(
            "Season Transition reset catalog contains unsupported authoritative components"
        )

    run = session.get(RunContainerModel, command.run_id)
    branch = session.get(RunBranchModel, command.branch_id)
    draft = session.scalar(
        select(BranchWorkingDraftModel).where(
            BranchWorkingDraftModel.branch_id == command.branch_id
        )
    )
    if run is None or branch is None or branch.run_id != command.run_id or draft is None:
        raise ValueError("Season Transition Run/Branch scope is incomplete")
    if run.read_only or branch.read_only or branch.status != "active":
        raise ValueError("Season Transition requires a writable active Branch")
    if not is_pre_completion_run_status(run.status):
        raise ValueError("Season Transition requires a Working Run")
    if (
        branch.saved_head_revision_id != command.expected_saved_revision_id
        or draft.base_revision_id != command.expected_saved_revision_id
    ):
        raise ValueError("Season Transition Saved Revision head is stale")
    if (
        draft.status != CLEAN_WORKING_DRAFT_STATUS
        or draft.change_count != 0
        or json.loads(draft.changes_json) != []
    ):
        raise ValueError("Season Transition requires a clean Working Draft")
    if draft.draft_version != command.expected_draft_version:
        raise ValueError("Season Transition Working Draft version is stale")

    head = session.get(BranchSavedRevisionModel, command.expected_saved_revision_id)
    if head is None or (head.run_id, head.branch_id) != (
        command.run_id,
        command.branch_id,
    ):
        raise ValueError("Season Transition Saved Revision head is missing")
    base_payload, _ = _revision_payload(head)

    if session.get(BranchSavedRevisionModel, command.next_saved_revision_id) is not None:
        raise ValueError("Season Transition Saved Revision id is already in use")
    if session.get(BranchRevisionAuditEventModel, command.audit_event_id) is not None:
        raise ValueError("Season Transition audit id is already in use")
    if (
        session.get(
            AuthoritativeWorldEventModel,
            (command.run_id, command.branch_id, command.command_id),
        )
        is not None
    ):
        raise ValueError("Season Transition command id is already in use")

    closing = stage_canonical_season_closing_ranking(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=configuration.completed_week,
    )
    package = resolve_canonical_season_closure_package(
        session,
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=configuration.completed_week,
    )
    sporting = stage_season_transition_sporting(session, configuration)
    lifecycle = stage_season_transition_lifecycle(session, configuration)
    ranking = stage_season_transition_ranking(session, configuration)
    if ranking.lifecycle_fingerprint != lifecycle.target_state.fingerprint:
        raise ValueError("Season Transition Ranking/lifecycle staging differs")

    target = configuration.target_week
    if (
        session.get(
            PublishedOfficialRankingModel,
            (command.run_id, command.branch_id, target.ordinal),
        )
        is not None
    ):
        raise ValueError("Season Transition target Official Ranking is already published")

    world = session.get(AuthoritativeWorldStateModel, (command.run_id, command.branch_id))
    if (
        world is None
        or world.current_ordinal != configuration.completed_week.ordinal
        or world.ranking_fingerprint != configuration.predecessor_official_fingerprint
    ):
        raise ValueError("Season Transition authoritative Week-61 world head changed")

    marker = bind_season_closure_marker(
        package.marker,
        final_saved_revision_id=command.next_saved_revision_id,
    )
    publication = PublishedOfficialRankingModel(
        run_id=command.run_id,
        branch_id=command.branch_id,
        week_ordinal=target.ordinal,
        snapshot_fingerprint=ranking.target_snapshot.fingerprint,
        payload_json=ranking.target_snapshot.model_dump_json(),
    )
    session.add(publication)
    world.current_ordinal = target.ordinal
    world.ranking_fingerprint = ranking.target_snapshot.fingerprint

    event_payload = _world_event_payload(
        command,
        closing_fingerprint=closing.fingerprint,
        summary_fingerprint=package.summary.fingerprint,
        marker_fingerprint=marker.fingerprint,
        sporting_fingerprint=sporting.target_state.fingerprint,
        lifecycle_fingerprint=lifecycle.target_state.fingerprint,
        ranking_fingerprint=ranking.target_snapshot.fingerprint,
    )
    session.add(
        AuthoritativeWorldEventModel(
            run_id=command.run_id,
            branch_id=command.branch_id,
            command_id=command.command_id,
            week_ordinal=target.ordinal,
            event_kind=WORLD_EVENT_KIND,
            payload_json=event_payload,
        )
    )
    session.flush()
    if fault_at == "after_public_state":
        raise RuntimeError("fault after Season Transition public state")

    viewer_branch_id = (run.official_branch_id or "").strip()
    if not viewer_branch_id:
        raise ValueError("Season Transition requires a Viewer Branch")
    payload = viewer_branch_saved_revision_payload(
        base_payload=base_payload,
        run_id=command.run_id,
        display_name=run.display_name or command.run_id,
        run_status=run.status,
        timeline_start_season=run.timeline_start_season,
        timeline_end_season=run.timeline_end_season,
        branch_id=command.branch_id,
        branch_display_name=branch.display_name,
        branch_status=branch.status,
        forked_from_branch_id=branch.forked_from_branch_id,
        forked_from_saved_revision_id=branch.forked_from_saved_revision_id,
        viewer_branch_id=viewer_branch_id,
    )
    capture_saved_ranking_component(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_initial_world(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_lifecycle(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_sporting(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    capture_saved_simulation_slots(
        session, payload, run_id=command.run_id, branch_id=command.branch_id
    )
    install_saved_revision_season_closure(
        payload,
        package=package,
        marker=marker,
    )

    summary = {
        "kind": ORDINARY_SEASON_TRANSITION_SAVED_REVISION_KIND,
        "summary": (
            f"Advanced Season {configuration.completed_week.season_index} "
            f"Week 61 to Season {target.season_index} Week 1"
        ),
        "completed_week": configuration.completed_week.model_dump(mode="json"),
        "target_week": target.model_dump(mode="json"),
        "configuration_fingerprint": configuration.fingerprint,
        "closing_ranking_fingerprint": closing.fingerprint,
        "season_summary_fingerprint": package.summary.fingerprint,
        "closure_marker_fingerprint": marker.fingerprint,
        "player_sporting_fingerprint": sporting.target_state.fingerprint,
        "player_lifecycle_fingerprint": lifecycle.target_state.fingerprint,
        "official_ranking_fingerprint": ranking.target_snapshot.fingerprint,
    }
    sequence = head.sequence + 1
    content_hash = saved_revision_content_hash(
        revision_id=command.next_saved_revision_id,
        run_id=command.run_id,
        branch_id=command.branch_id,
        sequence=sequence,
        parent_revision_id=head.revision_id,
        kind=ORDINARY_SEASON_TRANSITION_SAVED_REVISION_KIND,
        payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
        payload=payload,
        change_summary=summary,
    )
    session.add(
        BranchSavedRevisionModel(
            revision_id=command.next_saved_revision_id,
            run_id=command.run_id,
            branch_id=command.branch_id,
            sequence=sequence,
            parent_revision_id=head.revision_id,
            kind=ORDINARY_SEASON_TRANSITION_SAVED_REVISION_KIND,
            payload_schema_version=RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
            content_hash_algorithm=CONTENT_HASH_ALGORITHM,
            content_hash=content_hash,
            payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            change_summary_json=json.dumps(
                summary, sort_keys=True, separators=(",", ":")
            ),
        )
    )
    session.flush()
    if fault_at == "after_revision":
        raise RuntimeError("fault after Season Transition revision")

    claimed = session.execute(
        update(BranchWorkingDraftModel)
        .where(
            BranchWorkingDraftModel.draft_id == draft.draft_id,
            BranchWorkingDraftModel.base_revision_id == command.expected_saved_revision_id,
            BranchWorkingDraftModel.draft_version == command.expected_draft_version,
            BranchWorkingDraftModel.status == CLEAN_WORKING_DRAFT_STATUS,
        )
        .values(
            base_revision_id=command.next_saved_revision_id,
            draft_version=command.expected_draft_version + 1,
            draft_schema_version=RUN_WORKING_DRAFT_SCHEMA_VERSION,
            status=CLEAN_WORKING_DRAFT_STATUS,
            change_count=0,
            changes_json="[]",
            updated_at=func.current_timestamp(),
        )
    )
    if claimed.rowcount != 1:
        raise ValueError("Season Transition Working Draft changed concurrently")

    branch.saved_head_revision_id = command.next_saved_revision_id
    session.add(
        BranchRevisionAuditEventModel(
            audit_event_id=command.audit_event_id,
            run_id=command.run_id,
            branch_id=command.branch_id,
            saved_revision_id=command.next_saved_revision_id,
            event_kind=ORDINARY_SEASON_TRANSITION_AUDIT_EVENT_KIND,
            payload_json=json.dumps(
                {
                    "command_id": command.command_id,
                    "request_fingerprint": command.fingerprint,
                    "previous_saved_revision_id": command.expected_saved_revision_id,
                    "next_saved_revision_id": command.next_saved_revision_id,
                    **summary,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    )
    session.flush()

    return OrdinarySeasonTransitionResult(
        run_id=command.run_id,
        branch_id=command.branch_id,
        completed_week=configuration.completed_week,
        target_week=target,
        saved_revision_id=command.next_saved_revision_id,
        configuration_fingerprint=configuration.fingerprint,
        closing_ranking_fingerprint=closing.fingerprint,
        season_summary_fingerprint=package.summary.fingerprint,
        closure_marker_fingerprint=marker.fingerprint,
        player_sporting_fingerprint=sporting.target_state.fingerprint,
        player_lifecycle_fingerprint=lifecycle.target_state.fingerprint,
        official_ranking_fingerprint=ranking.target_snapshot.fingerprint,
        draft_version=command.expected_draft_version + 1,
    )
