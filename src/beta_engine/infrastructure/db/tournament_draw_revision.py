"""Persistence for append-only canonical Tournament Draw revisions."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_revision_authority import (
    TournamentDrawRevision,
    TournamentDrawRevisionBuilder,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldResolver
from beta_engine.infrastructure.db.models import TournamentDrawRevisionModel
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
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
        if not rows:
            return ()

        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        previous_draw_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        field_store = TournamentEntryFieldStore(self.session)
        field_rows = field_store._rows(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if (
            process is None
            or ranking is None
            or previous_draw_input is None
            or not field_rows
        ):
            raise ValueError("Draw revision history has missing frozen dependencies")
        previous_field, applications = field_store._load_row(field_rows[-1])

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
            if (
                predecessor is None
                or revision.predecessor_draw_fingerprint != predecessor.fingerprint
            ):
                raise ValueError(
                    "Tournament Draw revision predecessor chain is corrupt"
                )

            rebuilt_field = TournamentEntryFieldResolver.repair_pre_draw(
                authority=ranking,
                applications=applications,
                previous=previous_field,
                withdrawn_player_ids=revision.withdrawn_player_ids,
            )
            if rebuilt_field != revision.successor_field:
                raise ValueError(
                    "Tournament Draw revision field does not replay from frozen ranking"
                )

            if revision.repair_kind == "full_redraw":
                if revision.repair_draw_seed is None:
                    raise ValueError("Stored full redraw lacks repair draw seed")
                replay_draw_seed = revision.repair_draw_seed
            else:
                if (
                    revision.successor_draw_input.draw_seed
                    != previous_draw_input.draw_seed
                ):
                    raise ValueError(
                        "Seed-cascade phase repair unexpectedly changed Draw seed"
                    )
                replay_draw_seed = previous_draw_input.draw_seed

            rebuilt_input = TournamentDrawInputAuthorityBuilder.build(
                authority=ranking,
                field=rebuilt_field,
                field_sequence=revision.successor_draw_input.field_sequence,
                command_id=revision.command_id,
                draw_seed=replay_draw_seed,
                main_seed_count=None,
                qualification_seed_count=None,
                schema_version="tournament_draw_input_authority.v2",
            )
            if rebuilt_input != revision.successor_draw_input:
                raise ValueError(
                    "Tournament Draw revision input does not replay from repaired field"
                )

            if revision.repair_kind == "full_redraw":
                rebuilt_revision = TournamentDrawRevisionBuilder.build_full_redraw(
                    predecessor=predecessor,
                    successor_field=rebuilt_field,
                    successor_draw_input=rebuilt_input,
                    process_authority=process,
                    affected_draw_types=revision.affected_draw_types,
                    main_process_window_ordinal=(
                        revision.main_process_window_ordinal
                    ),
                    qualification_process_window_ordinal=(
                        revision.qualification_process_window_ordinal
                    ),
                    repair_draw_seed=revision.repair_draw_seed,
                    withdrawn_player_ids=revision.withdrawn_player_ids,
                    sequence=revision.sequence,
                    command_id=revision.command_id,
                )
            else:
                rebuilt_revision = (
                    TournamentDrawRevisionBuilder.build_seed_cascade_phase(
                        predecessor=predecessor,
                        successor_field=rebuilt_field,
                        successor_draw_input=rebuilt_input,
                        process_authority=process,
                        affected_draw_types=revision.affected_draw_types,
                        main_process_window_ordinal=(
                            revision.main_process_window_ordinal
                        ),
                        qualification_process_window_ordinal=(
                            revision.qualification_process_window_ordinal
                        ),
                        withdrawn_player_ids=revision.withdrawn_player_ids,
                        sequence=revision.sequence,
                        command_id=revision.command_id,
                        repair_draw_seed=revision.repair_draw_seed,
                    )
                )
            if rebuilt_revision != revision:
                raise ValueError(
                    "Tournament Draw revision does not replay from frozen dependencies"
                )
            out.append(revision)
            previous_field = revision.successor_field
            previous_draw_input = revision.successor_draw_input
            predecessor = revision.successor_draw
        return tuple(out)

    def active_draw(self, *, run_id: str, branch_id: str, event_id: str):
        history = self.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
        if history:
            return history[-1].successor_draw
        return TournamentDrawAuthorityStore(self.session).get_initial(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )

    def full_redraw_withdrawal(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        withdrawn_player_ids: tuple[str, ...],
        repair_draw_seed: int,
        main_process_window_ordinal: int | None = None,
        qualification_process_window_ordinal: int | None = None,
        repair_draw_seed: int | None = None,
    ) -> TournamentDrawRevision:
        requested = tuple(sorted(set(withdrawn_player_ids)))
        if not requested:
            raise ValueError("Full redraw withdrawal requires at least one player")

        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        history = self.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
        if retry is not None:
            revision = next(
                (
                    item
                    for item in history
                    if item.command_id == command_id
                ),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Tournament Draw revision command exists outside validated history"
                )
            if (
                retry.event_id != event_id
                or revision.withdrawn_player_ids != requested
                or revision.repair_draw_seed != repair_draw_seed
                or revision.main_process_window_ordinal != main_process_window_ordinal
                or revision.qualification_process_window_ordinal
                != qualification_process_window_ordinal
                or revision.repair_draw_seed != repair_draw_seed
            ):
                raise TournamentDrawRevisionConflict(
                    "Tournament Draw revision command already has a different request"
                )
            return revision

        predecessor = (
            history[-1].successor_draw
            if history
            else draw_store.get_initial(
                run_id=run_id, branch_id=branch_id, event_id=event_id
            )
        )
        if predecessor is None:
            raise ValueError("Full redraw requires canonical Draw authority")

        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if original_input is None or process is None or ranking is None:
            raise ValueError(
                "Full redraw requires Draw Input, Draw process and ranking authority"
            )
        if original_input.capacity.wild_card_slots:
            raise ValueError(
                "Full redraw with WC/RWC requires the dedicated post-draw WC repair slice"
            )

        field_store = TournamentEntryFieldStore(self.session)
        rows = field_store._rows(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if not rows:
            raise ValueError("Full redraw requires canonical Tournament Entry Field")
        persisted_field, applications = field_store._load_row(rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )
        successor_field = TournamentEntryFieldResolver.repair_pre_draw(
            authority=ranking,
            applications=applications,
            previous=previous_field,
            withdrawn_player_ids=requested,
        )
        if successor_field == previous_field:
            raise TournamentDrawRevisionConflict(
                "Full redraw withdrawal contains no new active-field change"
            )

        sequence = len(history) + 1
        successor_input = TournamentDrawInputAuthorityBuilder.build(
            authority=ranking,
            field=successor_field,
            field_sequence=original_input.field_sequence + sequence,
            command_id=command_id,
            draw_seed=repair_draw_seed,
            main_seed_count=None,
            qualification_seed_count=None,
            schema_version="tournament_draw_input_authority.v2",
        )

        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )
        affected = []
        if previous_input.direct_main_player_ids != successor_input.direct_main_player_ids:
            affected.append("main")
        if (
            previous_input.qualification_player_ids
            != successor_input.qualification_player_ids
        ):
            affected.append("qualification")
        affected_draw_types = tuple(affected)
        if not affected_draw_types:
            raise TournamentDrawRevisionConflict(
                "Withdrawal did not change active Main or Qualification field"
            )

        request = {
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "process_authority_fingerprint": process.fingerprint,
            "withdrawn_player_ids": list(requested),
            "repair_draw_seed": repair_draw_seed,
            "main_process_window_ordinal": main_process_window_ordinal,
            "qualification_process_window_ordinal": qualification_process_window_ordinal,
            "affected_draw_types": list(affected_draw_types),
            "successor_field_fingerprint": successor_field.fingerprint,
        }
        request_fp = _fp(request)
        revision = TournamentDrawRevisionBuilder.build_full_redraw(
            predecessor=predecessor,
            successor_field=successor_field,
            successor_draw_input=successor_input,
            process_authority=process,
            affected_draw_types=affected_draw_types,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=qualification_process_window_ordinal,
            repair_draw_seed=repair_draw_seed,
            withdrawn_player_ids=requested,
            sequence=sequence,
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

    def seed_cascade_phase_withdrawal(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        withdrawn_player_ids: tuple[str, ...],
        main_process_window_ordinal: int | None = None,
        qualification_process_window_ordinal: int | None = None,
        repair_draw_seed: int | None = None,
    ) -> TournamentDrawRevision:
        requested = tuple(sorted(set(withdrawn_player_ids)))
        if not requested:
            raise ValueError(
                "Seed-cascade phase withdrawal requires at least one player"
            )

        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        history = self.history(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if retry is not None:
            revision = next(
                (
                    item
                    for item in history
                    if item.command_id == command_id
                ),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Tournament Draw revision command exists outside validated history"
                )
            if (
                retry.event_id != event_id
                or revision.repair_kind != "seed_cascade_phase"
                or revision.withdrawn_player_ids != requested
                or revision.main_process_window_ordinal
                != main_process_window_ordinal
                or revision.qualification_process_window_ordinal
                != qualification_process_window_ordinal
                or revision.repair_draw_seed != repair_draw_seed
            ):
                raise TournamentDrawRevisionConflict(
                    "Tournament Draw revision command already has a different request"
                )
            return revision

        predecessor = (
            history[-1].successor_draw
            if history
            else draw_store.get_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
        )
        if predecessor is None:
            raise ValueError(
                "Seed-cascade phase repair requires canonical Draw authority"
            )

        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        ranking = TournamentRankingSnapshotAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if original_input is None or process is None or ranking is None:
            raise ValueError(
                "Seed-cascade phase repair requires Draw Input, Draw process "
                "and ranking authority"
            )
        if original_input.capacity.wild_card_slots:
            raise ValueError(
                "Seed-cascade phase repair with WC/RWC requires "
                "dedicated WC repair authority"
            )

        field_store = TournamentEntryFieldStore(self.session)
        rows = field_store._rows(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if not rows:
            raise ValueError(
                "Seed-cascade phase repair requires canonical "
                "Tournament Entry Field"
            )
        persisted_field, applications = field_store._load_row(rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )
        successor_field = TournamentEntryFieldResolver.repair_pre_draw(
            authority=ranking,
            applications=applications,
            previous=previous_field,
            withdrawn_player_ids=requested,
        )
        if successor_field == previous_field:
            raise TournamentDrawRevisionConflict(
                "Seed-cascade phase withdrawal contains no new active-field change"
            )

        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )
        sequence = len(history) + 1
        successor_input = TournamentDrawInputAuthorityBuilder.build(
            authority=ranking,
            field=successor_field,
            field_sequence=original_input.field_sequence + sequence,
            command_id=command_id,
            draw_seed=previous_input.draw_seed,
            main_seed_count=None,
            qualification_seed_count=None,
            schema_version="tournament_draw_input_authority.v2",
        )
        affected = []
        if (
            previous_input.direct_main_player_ids
            != successor_input.direct_main_player_ids
            or previous_input.wild_card_player_ids
            != successor_input.wild_card_player_ids
        ):
            affected.append("main")
        if (
            previous_input.qualification_player_ids
            != successor_input.qualification_player_ids
        ):
            affected.append("qualification")
        affected_draw_types = tuple(affected)
        if not affected_draw_types:
            raise TournamentDrawRevisionConflict(
                "Withdrawal did not change active Main or Qualification field"
            )

        request = {
            "repair_kind": "seed_cascade_phase",
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "process_authority_fingerprint": process.fingerprint,
            "withdrawn_player_ids": list(requested),
            "main_process_window_ordinal": main_process_window_ordinal,
            "qualification_process_window_ordinal": (
                qualification_process_window_ordinal
            ),
            "repair_draw_seed": repair_draw_seed,
            "affected_draw_types": list(affected_draw_types),
            "successor_field_fingerprint": successor_field.fingerprint,
        }
        revision = TournamentDrawRevisionBuilder.build_seed_cascade_phase(
            predecessor=predecessor,
            successor_field=successor_field,
            successor_draw_input=successor_input,
            process_authority=process,
            affected_draw_types=affected_draw_types,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=(
                qualification_process_window_ordinal
            ),
            withdrawn_player_ids=requested,
            sequence=sequence,
            command_id=command_id,
            repair_draw_seed=repair_draw_seed,
        )
        self.session.add(
            TournamentDrawRevisionModel(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                sequence=revision.sequence,
                command_id=command_id,
                request_fingerprint=_fp(request),
                revision_fingerprint=revision.fingerprint,
                predecessor_draw_fingerprint=(
                    revision.predecessor_draw_fingerprint
                ),
                successor_draw_fingerprint=revision.successor_draw.fingerprint,
                payload_json=revision.model_dump_json(),
            )
        )
        self.session.flush()
        return revision

