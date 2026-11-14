"""Admin following (Run level) and derived follow alerts (Branch level). Read/preference only."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.follow_notification_service import FollowNotificationService

router = APIRouter(prefix="/admin/runs/{run_id}", tags=["admin-follow-notifications"])


def _conflict(exc):
    return HTTPException(
        status_code=409, detail={"code": "follow_notification_conflict", "message": str(exc)}
    )


def _guard(call):
    try:
        return call()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except (ValueError, TypeError) as exc:
        raise _conflict(exc) from exc


class FollowBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alerts_enabled: bool = True


class StateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: str
    seen_item_count: int | None = Field(default=None, ge=0, strict=True)


@router.get("/follows")
def list_follows(run_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    return _guard(lambda: FollowNotificationService(runtime.repository).list_follows(run_id=run_id))


@router.put("/follows/{kind}/{subject_id}")
def put_follow(
    run_id: str, kind: str, subject_id: str, body: FollowBody,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    return _guard(lambda: FollowNotificationService(runtime.repository).set_follow(
        run_id=run_id, kind=kind, subject_id=subject_id, alerts_enabled=body.alerts_enabled))


@router.delete("/follows/{kind}/{subject_id}")
def delete_follow(
    run_id: str, kind: str, subject_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    return _guard(lambda: FollowNotificationService(runtime.repository).remove_follow(
        run_id=run_id, kind=kind, subject_id=subject_id))


@router.get("/branches/{branch_id}/notifications")
def notifications(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    as_of_ordinal: int | None = Query(default=None, ge=0),
    include_hidden: bool = Query(default=False),
):
    return _guard(lambda: FollowNotificationService(runtime.repository).notifications(
        run_id=run_id, branch_id=branch_id, as_of_ordinal=as_of_ordinal,
        include_hidden=include_hidden))


@router.put("/branches/{branch_id}/notifications/{notification_key}/state")
def put_notification_state(
    run_id: str, branch_id: str, notification_key: str, body: StateBody,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    return _guard(lambda: FollowNotificationService(runtime.repository).set_state(
        run_id=run_id, branch_id=branch_id, notification_key=notification_key, state=body.state, seen_item_count=body.seen_item_count))
