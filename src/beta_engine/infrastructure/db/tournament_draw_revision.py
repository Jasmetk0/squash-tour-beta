"""Persistence for append-only canonical Tournament Draw revisions."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_revision_authority import (
    TournamentDrawRevision,
    TournamentDrawRevisionBuilder,
)
from beta_engine.infrastructure.db.models import (
    TournamentDrawRevisionModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)


class TournamentDrawRevisionConflict(ValueError):
    pass


def _fp(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentDrawRevisionStore:
    def __init__(self, session: Session):
        self.session = session

    def history(self, *, run_id: str, branch_id: str, event_id: str):
        rows = self.session.scalars(
            select(TournamentDrawRevisionModel)
            .where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.event_id == event_id,
            )
            .order_by(TournamentDrawRevisionModel.sequence)
        ).all()
        out = []
        predecessor = TournamentDrawAuthorityStore(self.session).get_initial(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if predecessor is None and rows:
            raise ValueError("Draw revision history references missing initial Draw")
        for expected, row in enumerate(rows, start=1):
            if row.sequence != expected:
                raise ValueError("Tournament Draw revision sequence has a gap")
            revision = TournamentDrawRevision.model_validate_json(row.payload_json)
            if (
                revision.sequence,
                revision.command_id,
                revision.predecessor_draw_fingerprint,
                revision.successor_draw.fingerprint,
                revision.fingerprint,
            ) != (
                row.sequence,
                row.command_id,
                row.predecessor_draw_fingerprint,
                row.successor_draw_fingerprint,
                row.revision_fingerprint,
            ):
                raise ValueError("Stored Tournament Draw revision is corrupt")
            if predecessor is None or revision.predecessor_draw_fingerprint != predecessor.fingerprint:
                raise ValueError("Tournament Draw revision predecessor chain is corrupt")
            out.append(revision)
            predecessor = revision.successor_draw
        return tuple(out)

    def active_draw(self, *, run_id: str, branch_id: str, event_id: str):
        history = self.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
        if history:
            return history[-1].successor_draw
        return TournamentDrawAuthorityStore(self.session).get_initial(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )

    def full_redraw(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        draw_type: str,
        process_window_ordinal: int,
        repair_draw_seed: int,
    ) -> TournamentDrawRevision:
        history = self.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
        predecessor = (
            history[-1].successor_draw
            if history
            else TournamentDrawAuthorityStore(self.session).get_initial(
                run_id=run_id, branch_id=branch_id, event_id=event_id
            )
        )
        if predecessor is None:
            raise ValueError("Full redraw requires canonical Draw authority")
        draw_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if draw_input is None or process is None:
            raise ValueError("Full redraw requires Draw Input and Draw process authority")

        request = {
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "process_authority_fingerprint": process.fingerprint,
            "draw_type": draw_type,
            "process_window_ordinal": process_window_ordinal,
            "repair_draw_seed": repair_draw_seed,
        }
        request_fp = _fp(request)
        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        if retry is not None:
            if retry.request_fingerprint != request_fp or retry.event_id != event_id:
                raise TournamentDrawRevisionConflict(
                    "Tournament Draw revision command already has a different request"
                )
            return TournamentDrawRevision.model_validate_json(retry.payload_json)

        revision = TournamentDrawRevisionBuilder.build_full_redraw(
            predecessor=predecessor,
            draw_input=draw_input,
            process_authority=process,
            draw_type=draw_type,
            process_window_ordinal=process_window_ordinal,
            repair_draw_seed=repair_draw_seed,
            sequence=len(history) + 1,
            command_id=command_id,
        )
        self.session.add(
            TournamentDrawRevisionModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                sequence=revision.sequence,
                command_id=command_id,
                request_fingerprint=request_fp,
                revision_fingerprint=revision.fingerprint,
                predecessor_draw_fingerprint=revision.predecessor_draw_fingerprint,
                successor_draw_fingerprint=revision.successor_draw.fingerprint,
                payload_json=revision.model_dump_json(),
            )
        )
        self.session.flush()
        return revision
