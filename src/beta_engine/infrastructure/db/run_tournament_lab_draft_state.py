"""Saved Revision state for reviewed Tournament Lab -> Run draft proposals."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.infrastructure.db.models import RunTournamentLabDraftModel


RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY = "run_tournament_lab_drafts"
RUN_TOURNAMENT_LAB_DRAFT_SCHEMA = "run_tournament_lab_draft_state.v1"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_id(value: object, *, field: str, max_length: int = 160) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"Tournament Lab Run draft {field} must be a non-blank normalized string")
    if len(value) > max_length:
        raise ValueError(f"Tournament Lab Run draft {field} is too long")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"Tournament Lab Run draft {field} must be SHA-256")
    return value


@dataclass(frozen=True)
class RunTournamentLabDraft:
    schema_version: str
    run_id: str
    branch_id: str
    event_id: str
    version: int
    source_session_id: str
    source_session_fingerprint: str
    source_scenario_fingerprint: str
    source_preview_fingerprint: str
    candidate: dict[str, object]
    candidate_fingerprint: str
    fingerprint: str


@dataclass(frozen=True)
class RunTournamentLabDraftState:
    schema_version: str
    run_id: str
    branch_id: str
    drafts: tuple[RunTournamentLabDraft, ...]
    fingerprint: str


def _draft_payload(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    version: int,
    source_session_id: str,
    source_session_fingerprint: str,
    source_scenario_fingerprint: str,
    source_preview_fingerprint: str,
    candidate: dict[str, object],
    candidate_fingerprint: str,
) -> dict[str, object]:
    return {
        "schema_version": RUN_TOURNAMENT_LAB_DRAFT_SCHEMA,
        "run_id": run_id,
        "branch_id": branch_id,
        "event_id": event_id,
        "version": version,
        "source_session_id": source_session_id,
        "source_session_fingerprint": source_session_fingerprint,
        "source_scenario_fingerprint": source_scenario_fingerprint,
        "source_preview_fingerprint": source_preview_fingerprint,
        "candidate": candidate,
        "candidate_fingerprint": candidate_fingerprint,
    }


def build_run_tournament_lab_draft(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    version: int,
    source_session_id: str,
    source_session_fingerprint: str,
    source_scenario_fingerprint: str,
    source_preview_fingerprint: str,
    candidate: dict[str, object],
    candidate_fingerprint: str,
) -> RunTournamentLabDraft:
    run_id = _require_id(run_id, field="run_id", max_length=128)
    branch_id = _require_id(branch_id, field="branch_id", max_length=128)
    event_id = _require_id(event_id, field="event_id", max_length=160)
    source_session_id = _require_id(
        source_session_id, field="source_session_id", max_length=128
    )
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("Tournament Lab Run draft version must be positive")
    if not isinstance(candidate, dict):
        raise ValueError("Tournament Lab Run draft candidate must be an object")
    source_session_fingerprint = _require_sha256(
        source_session_fingerprint, field="source_session_fingerprint"
    )
    source_scenario_fingerprint = _require_sha256(
        source_scenario_fingerprint, field="source_scenario_fingerprint"
    )
    source_preview_fingerprint = _require_sha256(
        source_preview_fingerprint, field="source_preview_fingerprint"
    )
    candidate_fingerprint = _require_sha256(
        candidate_fingerprint, field="candidate_fingerprint"
    )
    if candidate_fingerprint != _hash(candidate):
        raise ValueError("Tournament Lab Run draft candidate fingerprint mismatch")
    payload = _draft_payload(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        version=version,
        source_session_id=source_session_id,
        source_session_fingerprint=source_session_fingerprint,
        source_scenario_fingerprint=source_scenario_fingerprint,
        source_preview_fingerprint=source_preview_fingerprint,
        candidate=candidate,
        candidate_fingerprint=candidate_fingerprint,
    )
    return RunTournamentLabDraft(
        **payload,
        fingerprint=_hash(payload),
    )


def _from_model(model: RunTournamentLabDraftModel) -> RunTournamentLabDraft:
    try:
        candidate = json.loads(model.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Tournament Lab Run draft payload JSON is malformed") from exc
    if not isinstance(candidate, dict):
        raise ValueError("Tournament Lab Run draft candidate must be an object")
    draft = build_run_tournament_lab_draft(
        run_id=model.run_id,
        branch_id=model.branch_id,
        event_id=model.event_id,
        version=model.version,
        source_session_id=model.source_session_id,
        source_session_fingerprint=model.source_session_fingerprint,
        source_scenario_fingerprint=model.source_scenario_fingerprint,
        source_preview_fingerprint=model.source_preview_fingerprint,
        candidate=candidate,
        candidate_fingerprint=model.candidate_fingerprint,
    )
    if draft.fingerprint != model.fingerprint:
        raise ValueError("Tournament Lab Run draft fingerprint mismatch")
    return draft


def get_run_tournament_lab_draft(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> RunTournamentLabDraft | None:
    row = session.get(RunTournamentLabDraftModel, (run_id, branch_id, event_id))
    return _from_model(row) if row is not None else None


def put_run_tournament_lab_draft(session: Session, draft: RunTournamentLabDraft) -> None:
    row = session.get(
        RunTournamentLabDraftModel,
        (draft.run_id, draft.branch_id, draft.event_id),
    )
    if row is None:
        row = RunTournamentLabDraftModel(
            run_id=draft.run_id,
            branch_id=draft.branch_id,
            event_id=draft.event_id,
        )
        session.add(row)
    row.version = draft.version
    row.fingerprint = draft.fingerprint
    row.source_session_id = draft.source_session_id
    row.source_session_fingerprint = draft.source_session_fingerprint
    row.source_scenario_fingerprint = draft.source_scenario_fingerprint
    row.source_preview_fingerprint = draft.source_preview_fingerprint
    row.candidate_fingerprint = draft.candidate_fingerprint
    row.payload_json = _canonical_json(draft.candidate)


def _state_fingerprint(
    *,
    run_id: str,
    branch_id: str,
    drafts: tuple[RunTournamentLabDraft, ...],
) -> str:
    return _hash(
        {
            "schema_version": RUN_TOURNAMENT_LAB_DRAFT_SCHEMA,
            "run_id": run_id,
            "branch_id": branch_id,
            "drafts": [
                {
                    "event_id": item.event_id,
                    "fingerprint": item.fingerprint,
                }
                for item in drafts
            ],
        }
    )


def capture_run_tournament_lab_draft_state(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
) -> RunTournamentLabDraftState | None:
    rows = session.execute(
        select(RunTournamentLabDraftModel)
        .where(
            RunTournamentLabDraftModel.run_id == run_id,
            RunTournamentLabDraftModel.branch_id == branch_id,
        )
        .order_by(RunTournamentLabDraftModel.event_id.asc())
    ).scalars().all()
    if not rows:
        return None
    drafts = tuple(_from_model(row) for row in rows)
    return RunTournamentLabDraftState(
        schema_version=RUN_TOURNAMENT_LAB_DRAFT_SCHEMA,
        run_id=run_id,
        branch_id=branch_id,
        drafts=drafts,
        fingerprint=_state_fingerprint(
            run_id=run_id,
            branch_id=branch_id,
            drafts=drafts,
        ),
    )


def saved_run_tournament_lab_draft_component(
    state: RunTournamentLabDraftState,
) -> dict[str, object]:
    return {
        "schema_version": state.schema_version,
        "run_id": state.run_id,
        "branch_id": state.branch_id,
        "drafts": [
            {
                **_draft_payload(
                    run_id=item.run_id,
                    branch_id=item.branch_id,
                    event_id=item.event_id,
                    version=item.version,
                    source_session_id=item.source_session_id,
                    source_session_fingerprint=item.source_session_fingerprint,
                    source_scenario_fingerprint=item.source_scenario_fingerprint,
                    source_preview_fingerprint=item.source_preview_fingerprint,
                    candidate=item.candidate,
                    candidate_fingerprint=item.candidate_fingerprint,
                ),
                "fingerprint": item.fingerprint,
            }
            for item in state.drafts
        ],
        "fingerprint": state.fingerprint,
    }


def capture_saved_run_tournament_lab_drafts(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> RunTournamentLabDraftState | None:
    content = payload.setdefault("content", {})
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    state = capture_run_tournament_lab_draft_state(
        session,
        run_id=run_id,
        branch_id=branch_id,
    )
    if state is None:
        content.pop(RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY, None)
        return None
    content[RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY] = (
        saved_run_tournament_lab_draft_component(state)
    )
    return state


def load_saved_run_tournament_lab_drafts(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> RunTournamentLabDraftState | None:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    raw = content.get(RUN_TOURNAMENT_LAB_DRAFT_COMPONENT_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Tournament Lab Run draft component must be an object")
    if raw.get("schema_version") != RUN_TOURNAMENT_LAB_DRAFT_SCHEMA:
        raise ValueError("Tournament Lab Run draft component schema is unsupported")
    if raw.get("run_id") != run_id or raw.get("branch_id") != branch_id:
        raise ValueError("Tournament Lab Run draft component scope mismatch")
    raw_drafts = raw.get("drafts")
    if not isinstance(raw_drafts, list):
        raise ValueError("Tournament Lab Run draft component drafts must be a list")
    drafts = []
    for item in raw_drafts:
        if not isinstance(item, dict):
            raise ValueError("Tournament Lab Run draft entry must be an object")
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            raise ValueError("Tournament Lab Run draft candidate must be an object")
        draft = build_run_tournament_lab_draft(
            run_id=run_id,
            branch_id=branch_id,
            event_id=item.get("event_id"),
            version=item.get("version"),
            source_session_id=item.get("source_session_id"),
            source_session_fingerprint=item.get("source_session_fingerprint"),
            source_scenario_fingerprint=item.get("source_scenario_fingerprint"),
            source_preview_fingerprint=item.get("source_preview_fingerprint"),
            candidate=dict(candidate),
            candidate_fingerprint=item.get("candidate_fingerprint"),
        )
        if item.get("fingerprint") != draft.fingerprint:
            raise ValueError("Tournament Lab Run draft entry fingerprint mismatch")
        drafts.append(draft)
    frozen = tuple(drafts)
    event_ids = [item.event_id for item in frozen]
    if event_ids != sorted(event_ids) or len(event_ids) != len(set(event_ids)):
        raise ValueError("Tournament Lab Run draft event identities are not canonical")
    expected = _state_fingerprint(run_id=run_id, branch_id=branch_id, drafts=frozen)
    if raw.get("fingerprint") != expected:
        raise ValueError("Tournament Lab Run draft component fingerprint mismatch")
    return RunTournamentLabDraftState(
        schema_version=RUN_TOURNAMENT_LAB_DRAFT_SCHEMA,
        run_id=run_id,
        branch_id=branch_id,
        drafts=frozen,
        fingerprint=expected,
    )


def restore_saved_run_tournament_lab_drafts(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    load_saved_run_tournament_lab_drafts(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_run_tournament_lab_drafts(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    session.execute(
        delete(RunTournamentLabDraftModel).where(
            RunTournamentLabDraftModel.run_id == run_id,
            RunTournamentLabDraftModel.branch_id == branch_id,
        )
    )
    if target is not None:
        for draft in target.drafts:
            put_run_tournament_lab_draft(session, draft)


def remap_saved_run_tournament_lab_drafts(
    source_payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> RunTournamentLabDraftState | None:
    source = load_saved_run_tournament_lab_drafts(
        source_payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None
    drafts = tuple(
        build_run_tournament_lab_draft(
            run_id=run_id,
            branch_id=target_branch_id,
            event_id=item.event_id,
            version=item.version,
            source_session_id=item.source_session_id,
            source_session_fingerprint=item.source_session_fingerprint,
            source_scenario_fingerprint=item.source_scenario_fingerprint,
            source_preview_fingerprint=item.source_preview_fingerprint,
            candidate=dict(item.candidate),
            candidate_fingerprint=item.candidate_fingerprint,
        )
        for item in source.drafts
    )
    return RunTournamentLabDraftState(
        schema_version=RUN_TOURNAMENT_LAB_DRAFT_SCHEMA,
        run_id=run_id,
        branch_id=target_branch_id,
        drafts=drafts,
        fingerprint=_state_fingerprint(
            run_id=run_id,
            branch_id=target_branch_id,
            drafts=drafts,
        ),
    )
