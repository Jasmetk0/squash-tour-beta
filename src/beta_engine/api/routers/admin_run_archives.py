"""Binary archive endpoints; no uploaded path, SQL or source registry is used."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.run_branch_archive_service import RunBranchArchiveService
from beta_engine.domain.run_branch_archive import MAX_ARCHIVE_BYTES, ArchiveError

router = APIRouter(prefix="/admin/run-archives", tags=["admin-run-archives"])


class ExportSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)


class ExportRequest(ExportSelection):
    expected_head_revision_id: str = Field(min_length=1, max_length=128)
    expected_archive_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _error(exc):
    code = exc.code if isinstance(exc, ArchiveError) else "archive_validation_failed"
    raise HTTPException(409, {"code": code, "message": str(exc)}) from exc


async def _read(request):
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_ARCHIVE_BYTES:
            raise HTTPException(
                413,
                {
                    "code": "archive_request_too_large",
                    "message": "Archive exceeds this operation's parser budget",
                },
            )
        data.extend(chunk)
    return bytes(data)


@router.post("/export/preview")
def export_preview(
    payload: ExportSelection, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    try:
        return RunBranchArchiveService(runtime.repository).export_preview(
            **payload.model_dump()
        )
    except (ValueError, TypeError, KeyError) as exc:
        _error(exc)


@router.post("/export")
def export(
    payload: ExportRequest, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    try:
        raw = RunBranchArchiveService(runtime.repository).export(**payload.model_dump())
        return Response(
            raw,
            media_type="application/vnd.squash.saved-branch+json",
            headers={
                "Content-Disposition": 'attachment; filename="saved-branch-v1.sqbranch"'
            },
        )
    except (ValueError, TypeError, KeyError) as exc:
        _error(exc)


@router.post("/import/preview")
async def import_preview(
    request: Request, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    raw = await _read(request)
    # The heavy parser/replay runs in the thread pool, like the normal synchronous
    # command routes; it must not block unrelated ASGI requests.
    from starlette.concurrency import run_in_threadpool

    try:
        return await run_in_threadpool(
            RunBranchArchiveService(runtime.repository).import_preview, raw
        )
    except (ValueError, TypeError, KeyError) as exc:
        _error(exc)


@router.post("/import/confirm", status_code=201)
async def import_confirm(
    request: Request,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    command_id: str = Query(min_length=1, max_length=128),
    expected_preview_fingerprint: str = Query(pattern=r"^[0-9a-f]{64}$"),
    explicit_confirmation: bool = False,
    operator_label: str = Query(default="", max_length=160),
    audit_reason: str = Query(default="", max_length=1000),
):
    raw = await _read(request)
    from starlette.concurrency import run_in_threadpool

    try:
        return await run_in_threadpool(
            RunBranchArchiveService(runtime.repository).confirm,
            raw,
            command_id=command_id,
            expected_preview_fingerprint=expected_preview_fingerprint,
            explicit_confirmation=explicit_confirmation,
            operator_label=operator_label,
            audit_reason=audit_reason,
        )
    except (ValueError, TypeError, KeyError) as exc:
        _error(exc)
