"""Persistence and Saved Revision support for first Tour-entry trigger evidence."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.infrastructure.db.models import (
    PlayerTourEntryTriggerModel,
    RunBranchModel,
    RunContainerModel,
)

PLAYER_TOUR_ENTRY_COMPONENT_KEY = "player_tour_entry_triggers"


class PlayerTourEntryTriggerConflict(ValueError):
    """Persisted first-entry authority conflicts with an existing player trigger."""


def _component_fingerprint(triggers: tuple[PlayerTourEntryTrigger, ...]) -> str:
    body = [item.model_dump(mode="json") for item in triggers]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical(
    triggers: tuple[PlayerTourEntryTrigger, ...] | list[PlayerTourEntryTrigger],
) -> tuple[PlayerTourEntryTrigger, ...]:
    return tuple(
        sorted(
            triggers,
            key=lambda item: (
                item.trigger_week.ordinal,
                item.decision_slot_ordinal,
                item.player_id,
            ),
        )
    )


def _load(row: PlayerTourEntryTriggerModel) -> PlayerTourEntryTrigger:
    trigger = PlayerTourEntryTrigger.model_validate_json(row.payload_json)
    if (
        trigger.run_id,
        trigger.branch_id,
        trigger.player_id,
        trigger.trigger_week.ordinal,
        trigger.decision_slot_ordinal,
        trigger.fingerprint,
    ) != (
        row.run_id,
        row.branch_id,
        row.player_id,
        row.trigger_week_ordinal,
        row.decision_slot_ordinal,
        row.fingerprint,
    ):
        raise ValueError("Stored player Tour-entry trigger is corrupt")
    return trigger


def _insert(session: Session, trigger: PlayerTourEntryTrigger) -> None:
    session.add(
        PlayerTourEntryTriggerModel(
            run_id=trigger.run_id,
            branch_id=trigger.branch_id,
            player_id=trigger.player_id,
            trigger_week_ordinal=trigger.trigger_week.ordinal,
            decision_slot_ordinal=trigger.decision_slot_ordinal,
            fingerprint=trigger.fingerprint,
            payload_json=trigger.model_dump_json(),
        )
    )
    session.flush()


class PlayerTourEntryTriggerStore:
    """Append-only one-time first Tour-entry authority per Run/Branch/player."""

    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Player Tour-entry Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status != "active"):
            raise ValueError("Player Tour-entry Run/Branch scope is not writable")

    def get(
        self,
        *,
        run_id: str,
        branch_id: str,
        player_id: str,
    ) -> PlayerTourEntryTrigger | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            PlayerTourEntryTriggerModel,
            (run_id, branch_id, player_id),
        )
        return None if row is None else _load(row)

    def list(
        self,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[PlayerTourEntryTrigger, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(PlayerTourEntryTriggerModel)
            .where(
                PlayerTourEntryTriggerModel.run_id == run_id,
                PlayerTourEntryTriggerModel.branch_id == branch_id,
            )
            .order_by(
                PlayerTourEntryTriggerModel.trigger_week_ordinal,
                PlayerTourEntryTriggerModel.decision_slot_ordinal,
                PlayerTourEntryTriggerModel.player_id,
            )
        ).all()
        return tuple(_load(row) for row in rows)

    def append(self, trigger: PlayerTourEntryTrigger) -> PlayerTourEntryTrigger:
        self._scope(trigger.run_id, trigger.branch_id, writing=True)
        existing = self.session.get(
            PlayerTourEntryTriggerModel,
            (trigger.run_id, trigger.branch_id, trigger.player_id),
        )
        if existing is not None:
            loaded = _load(existing)
            if loaded == trigger:
                return loaded
            raise PlayerTourEntryTriggerConflict(
                "Player already has a different first Tour-entry trigger"
            )
        _insert(self.session, trigger)
        return trigger


def capture_saved_tour_entry_triggers(
    session: Session,
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> None:
    triggers = PlayerTourEntryTriggerStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    payload["content"][PLAYER_TOUR_ENTRY_COMPONENT_KEY] = {
        "fingerprint": _component_fingerprint(triggers),
        "triggers": [item.model_dump(mode="json") for item in triggers],
    }


def load_saved_tour_entry_triggers(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[PlayerTourEntryTrigger, ...] | None:
    component = payload.get("content", {}).get(PLAYER_TOUR_ENTRY_COMPONENT_KEY)
    if component is None:
        return None
    if not isinstance(component, dict) or set(component) != {"fingerprint", "triggers"}:
        raise ValueError("Invalid Saved Revision player Tour-entry component")
    raw = component["triggers"]
    if not isinstance(raw, list):
        raise ValueError("Saved player Tour-entry triggers must be a list")
    triggers = tuple(
        PlayerTourEntryTrigger.model_validate_json(json.dumps(item)) for item in raw
    )
    if triggers != _canonical(triggers):
        raise ValueError("Saved player Tour-entry triggers are not canonically ordered")
    if len({item.player_id for item in triggers}) != len(triggers):
        raise ValueError("Saved player Tour-entry triggers contain duplicate players")
    if any(
        (item.run_id, item.branch_id) != (run_id, branch_id) for item in triggers
    ):
        raise ValueError("Saved player Tour-entry trigger scope mismatch")
    if _component_fingerprint(triggers) != component["fingerprint"]:
        raise ValueError("Saved player Tour-entry trigger fingerprint mismatch")
    return triggers


def remap_saved_tour_entry_triggers_component(
    payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    application_submission_identity_map: dict[str, tuple[str, str]],
) -> tuple[dict | None, dict[str, str]]:
    """Retarget first Tour-entry triggers backed by valid application submissions."""

    source = load_saved_tour_entry_triggers(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None, {}

    target = []
    fingerprint_map: dict[str, str] = {}
    for trigger in source:
        if trigger.trigger_kind != "valid_tournament_application":
            raise ValueError(
                "Player Tour-entry trigger kind requires a separate target evidence remap"
            )
        try:
            (
                target_source_evidence_id,
                target_source_fingerprint,
            ) = application_submission_identity_map[
                trigger.source_evidence_fingerprint
            ]
        except KeyError as exc:
            raise ValueError(
                "Player Tour-entry trigger references application submission "
                "without a target mapping"
            ) from exc
        if trigger.source_evidence_id != target_source_evidence_id:
            raise ValueError(
                "Player Tour-entry trigger application id differs from mapped submission"
            )
        mapped = trigger.model_copy(
            update={
                "branch_id": target_branch_id,
                "source_evidence_fingerprint": target_source_fingerprint,
            }
        )
        target.append(mapped)
        fingerprint_map[trigger.fingerprint] = mapped.fingerprint

    target_tuple = tuple(target)
    return (
        {
            "fingerprint": _component_fingerprint(target_tuple),
            "triggers": [item.model_dump(mode="json") for item in target_tuple],
        },
        fingerprint_map,
    )


def restore_saved_tour_entry_triggers(
    session: Session,
    *,
    current_payload: dict,
    target_payload: dict,
    run_id: str,
    branch_id: str,
) -> None:
    expected = load_saved_tour_entry_triggers(
        current_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    target = load_saved_tour_entry_triggers(
        target_payload,
        run_id=run_id,
        branch_id=branch_id,
    )
    live = PlayerTourEntryTriggerStore(session).list(
        run_id=run_id,
        branch_id=branch_id,
    )
    if tuple(item.fingerprint for item in live) != tuple(
        item.fingerprint for item in (expected or ())
    ):
        raise ValueError("Live player Tour-entry triggers differ from saved head")

    session.execute(
        delete(PlayerTourEntryTriggerModel).where(
            PlayerTourEntryTriggerModel.run_id == run_id,
            PlayerTourEntryTriggerModel.branch_id == branch_id,
        )
    )
    for trigger in target or ():
        _insert(session, trigger)
