"""Run-level following and Branch-level attention state (no sport, no RNG, no Save).

Follows are a user preference of the Run, shared by all its Branches (Master 27.23).
Notification cards are derived on every read from the authenticated Saved Tour; only
the read/hidden state of a card is stored. Writing here never creates a Saved revision,
a World Event or an Audit Log entry, and it cannot influence a simulation.
"""

from __future__ import annotations

import re

from sqlalchemy import select

from beta_engine.application.calendar_tour_notifications import derive_notifications
from beta_engine.infrastructure.db.models import (
    RunContainerModel,
    RunFollowModel,
    RunNotificationStateModel,
)

KINDS = ("player", "country")
STATES = ("unread", "read", "hidden")


class FollowNotificationService:
    def __init__(self, repository):
        self.repository = repository

    def _require_run(self, session, run_id):
        if session.get(RunContainerModel, run_id) is None:
            raise KeyError("Run does not exist")

    @staticmethod
    def _validate(kind, subject):
        if kind not in KINDS:
            raise ValueError("Only players and countries can be followed")
        if kind == "country" and not re.fullmatch(r"[A-Z]{3}", subject or ""):
            raise ValueError("A followed country needs an uppercase three-letter code")
        if kind == "player" and (not subject or len(subject) > 128 or subject.strip() != subject):
            raise ValueError("Invalid player identifier")

    def list_follows(self, *, run_id):
        with self.repository._session_factory() as session:
            self._require_run(session, run_id)
            rows = session.scalars(
                select(RunFollowModel).where(RunFollowModel.run_id == run_id)
                .order_by(RunFollowModel.subject_kind, RunFollowModel.subject_id)
            ).all()
            return {
                "schema_version": "run_follows.v1", "run_id": run_id,
                "follows": [
                    {"kind": r.subject_kind, "subject_id": r.subject_id,
                     "alerts_enabled": bool(r.alerts_enabled)}
                    for r in rows
                ],
            }

    def set_follow(self, *, run_id, kind, subject_id, alerts_enabled=True):
        """Idempotent upsert; repeating the command changes nothing."""
        self._validate(kind, subject_id)
        with self.repository._session_factory.begin() as session:
            self._require_run(session, run_id)
            row = session.get(RunFollowModel, (run_id, kind, subject_id))
            if row is None:
                session.add(RunFollowModel(
                    run_id=run_id, subject_kind=kind, subject_id=subject_id,
                    alerts_enabled=int(bool(alerts_enabled)),
                ))
            else:
                row.alerts_enabled = int(bool(alerts_enabled))
        return self.list_follows(run_id=run_id)

    def remove_follow(self, *, run_id, kind, subject_id):
        self._validate(kind, subject_id)
        with self.repository._session_factory.begin() as session:
            self._require_run(session, run_id)
            row = session.get(RunFollowModel, (run_id, kind, subject_id))
            if row is not None:
                session.delete(row)
        return self.list_follows(run_id=run_id)

    def _derive(self, run_id, branch_id, follows, as_of_ordinal):
        from beta_engine.application.calendar_tour_service import CalendarTourService
        from beta_engine.application.native_fork_runtime_service import (
            NativeForkRuntimeService,
            is_native_fork,
        )
        from sqlalchemy import text

        if is_native_fork(self.repository, run_id, branch_id):
            return NativeForkRuntimeService(self.repository).report(
                run_id=run_id, branch_id=branch_id, kind="notifications",
                follows=follows, as_of_ordinal=as_of_ordinal,
            )
        service = CalendarTourService(self.repository)
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            ctx, _working, signed = service._context(session, run_id, branch_id)
            _clock, rev, world, *_rest = ctx
            if signed is None or world is None:
                raise ValueError("Notifications require a Saved configured Tour")
            from beta_engine.application.native_career_identity import saved_career_world
            world = saved_career_world(world, signed, rev.saved_revision.payload)
            return {
                **derive_notifications(signed, world, follows, branch_id, as_of_ordinal),
                "saved_head_revision_id": rev.saved_head_revision_id,
            }

    def _follows(self, run_id):
        return [
            (f["kind"], f["subject_id"], f["alerts_enabled"])
            for f in self.list_follows(run_id=run_id)["follows"]
        ]

    def notifications(self, *, run_id, branch_id, as_of_ordinal=None, include_hidden=False):
        derived = self._derive(run_id, branch_id, self._follows(run_id), as_of_ordinal)
        with self.repository._session_factory() as session:
            states = {
                r.notification_key: r
                for r in session.scalars(
                    select(RunNotificationStateModel).where(
                        RunNotificationStateModel.run_id == run_id,
                        RunNotificationStateModel.branch_id == branch_id,
                    )
                )
            }
        cards = []
        for card in derived["cards"]:
            row = states.get(card["notification_key"])
            state = "unread" if row is None else row.state
            seen = 0 if row is None else row.seen_item_count
            if state == "hidden" and not include_hidden:
                continue
            cards.append({
                **card, "state": state,
                # Facts that arrived after the card was read stay visibly new.
                "unread_items": card["item_count"] if state != "read" else max(0, card["item_count"] - seen),
            })
        return {
            **{k: v for k, v in derived.items() if k != "cards"},
            "cards": cards,
            "unread_cards": sum(1 for c in cards if c["state"] == "unread" or c["unread_items"] > 0),
        }

    def set_state(self, *, run_id, branch_id, notification_key, state, seen_item_count=None):
        if state not in STATES:
            raise ValueError("Notification state must be unread, read or hidden")
        derived = self._derive(run_id, branch_id, self._follows(run_id), None)
        card = next((c for c in derived["cards"] if c["notification_key"] == notification_key), None)
        if card is None:
            raise KeyError("Notification is not part of this Branch's current view")
        seen = card["item_count"] if seen_item_count is None else seen_item_count
        if type(seen) is not int or not 0 <= seen <= card["item_count"]:
            raise ValueError("Seen item count does not belong to this notification")
        with self.repository._session_factory.begin() as session:
            row = session.get(RunNotificationStateModel, (run_id, branch_id, notification_key))
            if state == "unread":
                if row is not None:
                    session.delete(row)
            elif row is None:
                session.add(RunNotificationStateModel(
                    run_id=run_id, branch_id=branch_id, notification_key=notification_key,
                    state=state, seen_item_count=seen,
                ))
            else:
                row.state = state
                row.seen_item_count = seen
        return self.notifications(run_id=run_id, branch_id=branch_id, include_hidden=True)
