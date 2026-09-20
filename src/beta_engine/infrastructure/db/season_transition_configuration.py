"""Persistence + Saved Revision projection for ordinary Season Transition configuration."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
)
from beta_engine.infrastructure.db.models import SeasonTransitionConfigurationModel

SEASON_TRANSITION_CONFIGURATION_COMPONENT_KEY = "season_transition_configuration"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


class SeasonTransitionConfigurationStore:
    def __init__(self, session: Session):
        self.session = session

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        target_ordinal: int,
    ) -> SeasonTransitionConfiguration | None:
        row = self.session.get(
            SeasonTransitionConfigurationModel,
            (run_id, branch_id, target_ordinal),
        )
        if row is None:
            return None
        value = SeasonTransitionConfiguration.model_validate_json(row.payload_json)
        if (
            value.run_id,
            value.branch_id,
            value.target_week.ordinal,
            value.fingerprint,
        ) != (
            run_id,
            branch_id,
            target_ordinal,
            row.fingerprint,
        ):
            raise ValueError(
                "Season Transition configuration identity or fingerprint mismatch"
            )
        return value

    def rows(self, *, run_id: str, branch_id: str):
        return tuple(
            self.session.scalars(
                select(SeasonTransitionConfigurationModel)
                .where(
                    SeasonTransitionConfigurationModel.run_id == run_id,
                    SeasonTransitionConfigurationModel.branch_id == branch_id,
                )
                .order_by(SeasonTransitionConfigurationModel.target_ordinal)
            ).all()
        )

    def put(
        self,
        value: SeasonTransitionConfiguration,
        *,
        command_id: str,
        request_fingerprint: str,
        expected_fingerprint: str | None,
    ) -> SeasonTransitionConfiguration:
        key = (value.run_id, value.branch_id, value.target_week.ordinal)
        row = self.session.get(SeasonTransitionConfigurationModel, key)
        if row is not None and row.command_id == command_id:
            if (
                row.request_fingerprint != request_fingerprint
                or row.fingerprint != value.fingerprint
            ):
                raise ValueError(
                    "Season Transition configuration command retry has different inputs"
                )
            return self.get(
                run_id=value.run_id,
                branch_id=value.branch_id,
                target_ordinal=value.target_week.ordinal,
            )
        if row is None:
            if expected_fingerprint is not None:
                raise ValueError(
                    "Season Transition configuration expected predecessor is missing"
                )
            self.session.add(
                SeasonTransitionConfigurationModel(
                    run_id=value.run_id,
                    branch_id=value.branch_id,
                    target_ordinal=value.target_week.ordinal,
                    fingerprint=value.fingerprint,
                    command_id=command_id,
                    request_fingerprint=request_fingerprint,
                    payload_json=value.model_dump_json(),
                )
            )
        else:
            if expected_fingerprint != row.fingerprint:
                raise ValueError(
                    "Season Transition configuration changed since preview"
                )
            row.fingerprint = value.fingerprint
            row.command_id = command_id
            row.request_fingerprint = request_fingerprint
            row.payload_json = value.model_dump_json()
        self.session.flush()
        installed = self.get(
            run_id=value.run_id,
            branch_id=value.branch_id,
            target_ordinal=value.target_week.ordinal,
        )
        if installed is None or installed.fingerprint != value.fingerprint:
            raise ValueError("Season Transition configuration write could not be verified")
        return installed


def _saved_state(session: Session, *, run_id: str, branch_id: str) -> dict | None:
    rows = SeasonTransitionConfigurationStore(session).rows(
        run_id=run_id,
        branch_id=branch_id,
    )
    if not rows:
        return None
    body = {
        "schema_version": "saved_season_transition_configuration.v1",
        "rows": [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "target_ordinal": row.target_ordinal,
                "fingerprint": row.fingerprint,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in rows
        ],
    }
    body["fingerprint"] = _hash(body)
    return body


def _load_component(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> dict | None:
    component = payload.get("content", {}).get(
        SEASON_TRANSITION_CONFIGURATION_COMPONENT_KEY
    )
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved Revision Season Transition configuration")
    state = component["state"]
    if (
        not isinstance(state, dict)
        or state.get("schema_version")
        != "saved_season_transition_configuration.v1"
        or state.get("fingerprint") != component["fingerprint"]
    ):
        raise ValueError("Saved Season Transition configuration envelope is invalid")
    unsealed = dict(state)
    fingerprint = unsealed.pop("fingerprint", None)
    if fingerprint != _hash(unsealed):
        raise ValueError("Saved Season Transition configuration fingerprint mismatch")

    target_ordinals = []
    for row in state.get("rows", []):
        if (row.get("run_id"), row.get("branch_id")) != (run_id, branch_id):
            raise ValueError("Saved Season Transition configuration scope mismatch")
        value = SeasonTransitionConfiguration.model_validate_json(row["payload_json"])
        if (
            value.run_id,
            value.branch_id,
            value.target_week.ordinal,
            value.fingerprint,
        ) != (
            run_id,
            branch_id,
            row["target_ordinal"],
            row["fingerprint"],
        ):
            raise ValueError("Saved Season Transition configuration row is corrupt")
        target_ordinals.append(row["target_ordinal"])
    if target_ordinals != sorted(set(target_ordinals)):
        raise ValueError(
            "Saved Season Transition configuration targets are not canonical"
        )
    return state


def capture_saved_season_transition_configurations(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    state = _saved_state(session, run_id=run_id, branch_id=branch_id)
    if state is not None:
        payload["content"][SEASON_TRANSITION_CONFIGURATION_COMPONENT_KEY] = {
            "fingerprint": state["fingerprint"],
            "state": state,
        }


def restore_saved_season_transition_configurations(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = _load_component(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = _load_component(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = _saved_state(session, run_id=run_id, branch_id=branch_id)
    if (live or {}).get("fingerprint") != (expected or {}).get("fingerprint"):
        raise ValueError(
            "Live Season Transition configuration differs from the Saved Revision head"
        )

    session.execute(
        delete(SeasonTransitionConfigurationModel).where(
            SeasonTransitionConfigurationModel.run_id == run_id,
            SeasonTransitionConfigurationModel.branch_id == branch_id,
        )
    )
    for row in (target or {}).get("rows", []):
        session.add(SeasonTransitionConfigurationModel(**row))
    session.flush()
    installed = _saved_state(session, run_id=run_id, branch_id=branch_id)
    if (installed or {}).get("fingerprint") != (target or {}).get("fingerprint"):
        raise ValueError(
            "Season Transition configuration restore could not be verified"
        )
