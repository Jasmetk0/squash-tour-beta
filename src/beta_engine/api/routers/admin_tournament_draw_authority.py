"""Canonical Admin HTTP boundary for Run/Branch initial Tournament Draw authority."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.application.authoritative_frozen_main_replacement import (
    AuthoritativeFrozenMainReplacement,
    AuthoritativeFrozenMainReplacementCommitCommand,
    AuthoritativeFrozenMainReplacementConflict,
    AuthoritativeFrozenMainReplacementRequest,
)
from beta_engine.application.authoritative_tournament_draw import (
    CanonicalDrawGenerateCommand,
    CanonicalDrawInputCommitCommand,
    CanonicalTournamentDrawRevisionHistoryState,
    CanonicalTournamentDrawService,
    CanonicalTournamentDrawState,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/draw",
    tags=["admin-tournament-draw-authority"],
)


def _service(runtime: ApiRuntime) -> CanonicalTournamentDrawService:
    return CanonicalTournamentDrawService(runtime.repository._session_factory)


@router.get("", response_model=CanonicalTournamentDrawState)
def inspect_draw_state(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawState:
    try:
        return _service(runtime).inspect(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_state_conflict", "message": str(exc)},
        ) from exc


@router.get("/authority", response_model=TournamentDrawAuthority)
def inspect_initial_draw_authority(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentDrawAuthority:
    try:
        return _service(runtime).inspect_initial_authority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_authority_conflict", "message": str(exc)},
        ) from exc


@router.get("/effective-authority", response_model=TournamentDrawAuthority)
def inspect_effective_draw_authority(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentDrawAuthority:
    """Read the active canonical Draw after any append-only revision chain."""

    try:
        return _service(runtime).inspect_effective_authority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_effective_draw_conflict", "message": str(exc)},
        ) from exc


@router.get("/revisions", response_model=CanonicalTournamentDrawRevisionHistoryState)
def inspect_draw_revision_history(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawRevisionHistoryState:
    try:
        return _service(runtime).inspect_revision_history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_revision_history_conflict", "message": str(exc)},
        ) from exc


@router.post("/frozen-main-replacement/preview")
def preview_frozen_main_replacement(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        request = AuthoritativeFrozenMainReplacementRequest.model_validate_json(
            json.dumps(payload)
        )
        with runtime.repository._session_factory() as session:
            return AuthoritativeFrozenMainReplacement(session).preview(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                withdrawn_player_id=request.withdrawn_player_id,
                unavailable_player_ids=request.unavailable_player_ids,
            )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "frozen_main_replacement_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/frozen-main-replacement/commit", status_code=201)
def commit_frozen_main_replacement(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        command = AuthoritativeFrozenMainReplacementCommitCommand.model_validate_json(
            json.dumps(
                {
                    **payload,
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "event_id": event_id,
                }
            )
        )
        with runtime.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            result = AuthoritativeFrozenMainReplacement(session).execute(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=command.command_id,
                withdrawn_player_id=command.withdrawn_player_id,
                main_process_window_ordinal=command.main_process_window_ordinal,
                qualification_process_window_ordinal=(
                    command.qualification_process_window_ordinal
                ),
                repair_draw_seed=command.repair_draw_seed,
                unavailable_player_ids=command.unavailable_player_ids,
                expected_source_fingerprint=command.expected_source_fingerprint,
            )
            revisions = result.draw_revisions
            return {
                "schema_version": "authoritative_frozen_main_replacement_commit.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "withdrawn_player_id": command.withdrawn_player_id,
                "source": result.source,
                "source_authority_fingerprint": command.expected_source_fingerprint,
                "draw_revision_sequences": [
                    revision.sequence for revision in revisions
                ],
                "draw_revision_fingerprints": [
                    revision.fingerprint for revision in revisions
                ],
                "successor_draw_fingerprint": (
                    revisions[-1].successor_draw.fingerprint
                    if revisions
                    else None
                ),
            }
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthoritativeFrozenMainReplacementConflict as exc:
        code = (
            "frozen_main_replacement_walkover_handoff"
            if "W/O source requires authoritative week, slot and group target"
            in str(exc)
            else "frozen_main_replacement_commit_conflict"
        )
        raise HTTPException(
            status_code=409,
            detail={"code": code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "frozen_main_replacement_commit_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/commit-input", response_model=CanonicalTournamentDrawState)
def commit_draw_input(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawState:
    try:
        command = CanonicalDrawInputCommitCommand.model_validate(payload)
        if (command.run_id, command.branch_id, command.event_id) != (
            run_id,
            branch_id,
            event_id,
        ):
            raise ValueError("canonical Draw Input request scope mismatch")
        return _service(runtime).commit_input(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_input_conflict", "message": str(exc)},
        ) from exc


@router.post("/generate", response_model=CanonicalTournamentDrawState)
def generate_initial_draw(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> CanonicalTournamentDrawState:
    try:
        command = CanonicalDrawGenerateCommand.model_validate(payload)
        if (command.run_id, command.branch_id, command.event_id) != (
            run_id,
            branch_id,
            event_id,
        ):
            raise ValueError("canonical Draw generation request scope mismatch")
        return _service(runtime).generate(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "canonical_draw_generation_conflict", "message": str(exc)},
        ) from exc
