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
from beta_engine.domain.tournaments.post_draw_wild_card_repair import (
    TournamentPostDrawWildCardRepairAuthorityBuilder,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserFillAuthorityBuilder,
    TournamentLuckyLoserVacancyAuthorityBuilder,
)
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
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
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthorityStore,
)


class TournamentDrawRevisionConflict(ValueError):
    pass


def _fp(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _source_bound_pre_q_backfill(
    *,
    previous_draw_input,
    replacement_source_authority,
) -> str | None:
    selected = replacement_source_authority.selected_player_id
    if selected is None:
        raise ValueError("Q-promotion source lacks selected player")
    if selected not in set(previous_draw_input.qualification_player_ids):
        return None

    blocked = (
        set(replacement_source_authority.unavailable_player_ids)
        | set(previous_draw_input.direct_main_player_ids)
        | set(previous_draw_input.wild_card_player_ids)
        | set(previous_draw_input.qualification_player_ids)
        | set(previous_draw_input.lucky_loser_player_ids)
    )
    for candidate in replacement_source_authority.external_reserve_player_ids:
        if candidate not in blocked:
            return candidate
    return None


class TournamentDrawRevisionStore:
    def __init__(self, session: Session):
        self.session = session

    def _replacement_cutoff_authorities(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        withdrawn_player_ids: tuple[str, ...],
    ):
        authorities = TournamentPlayerReplacementCutoffAuthorityStore(
            self.session
        ).resolve_many(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_ids=withdrawn_player_ids,
        )
        walkover = [
            authority
            for authority in authorities
            if authority.status == "walkover_required"
        ]
        if walkover:
            players = ", ".join(authority.player_id for authority in walkover)
            raise TournamentDrawRevisionConflict(
                "Replacement cutoff has passed; W/O authority is required for: "
                + players
            )
        eliminated = [
            authority
            for authority in authorities
            if authority.status == "already_eliminated"
        ]
        if eliminated:
            players = ", ".join(authority.player_id for authority in eliminated)
            raise TournamentDrawRevisionConflict(
                "Withdrawal cannot repair an already eliminated tournament path: "
                + players
            )
        return authorities

    def _qualification_start_authority(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        qualification_player_ids: tuple[str, ...],
    ):
        if not qualification_player_ids:
            raise TournamentDrawRevisionConflict(
                "Lucky Loser vacancy requires Qualification participants"
            )
        authorities = TournamentPlayerReplacementCutoffAuthorityStore(
            self.session
        ).resolve_many(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_ids=qualification_player_ids,
        )
        candidates = []
        for authority in authorities:
            evidence = authority.first_real_match
            if evidence is None:
                continue
            candidates.append((evidence, authority.player_id))
        if not candidates:
            raise TournamentDrawRevisionConflict(
                "Lucky Loser does not exist before Qualification starts"
            )
        evidence, player_id = min(
            candidates,
            key=lambda item: (
                item[0].week_ordinal,
                item[0].slot_ordinal,
                item[0].group_id,
                item[0].match_id,
                item[1],
            ),
        )
        return TournamentPlayerReplacementCutoffAuthorityBuilder.build(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id=player_id,
            played_matches=(evidence,),
        )

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
        initial_draw_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        previous_draw_input = initial_draw_input
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

            if revision.repair_kind == "frozen_ordinary_fallback":
                authority = revision.replacement_source_authority
                if authority is None:
                    raise ValueError(
                        "Stored frozen ordinary fallback lacks source authority"
                    )
                if revision.successor_field != previous_field:
                    raise ValueError(
                        "Frozen ordinary fallback unexpectedly changed Entry Field"
                    )
                if authority.predecessor_draw_fingerprint != predecessor.fingerprint:
                    raise ValueError(
                        "Frozen ordinary fallback source predecessor does not replay"
                    )
                if (
                    authority.predecessor_draw_input_fingerprint
                    != previous_draw_input.fingerprint
                ):
                    raise ValueError(
                        "Frozen ordinary fallback source Draw Input does not replay"
                    )
                slot = predecessor.main.slots[authority.physical_slot_index - 1]
                if slot.player_id != authority.withdrawn_player_id:
                    raise ValueError(
                        "Frozen ordinary fallback source physical slot does not replay"
                    )
                rebuilt_input = (
                    TournamentDrawInputAuthorityBuilder.build_frozen_ordinary_fallback(
                        previous=previous_draw_input,
                        command_id=revision.command_id,
                        withdrawn_player_id=authority.withdrawn_player_id,
                        replacement_source_authority_fingerprint=authority.fingerprint,
                        replacement_player_id=(
                            authority.selected_player_id
                            if authority.source == "external_reserve"
                            else None
                        ),
                        vacated_main_seed_number=slot.seed_number,
                        create_bye=authority.source == "bye",
                    )
                )
                if rebuilt_input != revision.successor_draw_input:
                    raise ValueError(
                        "Frozen ordinary fallback Draw Input does not replay"
                    )
                rebuilt_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_ordinary_fallback(
                        predecessor=predecessor,
                        successor_field=previous_field,
                        successor_draw_input=rebuilt_input,
                        process_authority=process,
                        main_process_window_ordinal=(
                            revision.main_process_window_ordinal
                        ),
                        sequence=revision.sequence,
                        command_id=revision.command_id,
                        replacement_source_authority=authority,
                    )
                )
                if rebuilt_revision != revision:
                    raise ValueError(
                        "Frozen ordinary fallback Draw revision does not replay"
                    )
                out.append(revision)
                previous_draw_input = revision.successor_draw_input
                predecessor = revision.successor_draw
                continue

            if revision.repair_kind == "lucky_loser_fill":
                authority = revision.lucky_loser_fill_authority
                if authority is None:
                    raise ValueError("Stored Lucky Loser fill lacks authority")
                if revision.successor_field != previous_field:
                    raise ValueError(
                        "Lucky Loser fill unexpectedly changed Tournament Entry Field"
                    )
                prior_fill = next(
                    (
                        prior.lucky_loser_fill_authority
                        for prior in reversed(out)
                        if prior.repair_kind == "lucky_loser_fill"
                        and prior.lucky_loser_fill_authority is not None
                    ),
                    None,
                )
                if prior_fill is not None:
                    order_authority = prior_fill.order_authority
                else:
                    order_authority = TournamentLuckyLoserOrderAuthorityStore(
                        self.session
                    ).resolve_for_draw(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=event_id,
                        draw=predecessor,
                    )
                rebuilt_authority = TournamentLuckyLoserFillAuthorityBuilder.build(
                    predecessor=predecessor,
                    predecessor_draw_input=previous_draw_input,
                    command_id=revision.command_id,
                    order_authority=order_authority,
                    unavailable_player_ids=authority.unavailable_player_ids,
                )
                if rebuilt_authority != authority:
                    raise ValueError("Lucky Loser fill authority does not replay")
                rebuilt_input = TournamentDrawInputAuthorityBuilder.build_lucky_loser_fill(
                    previous=previous_draw_input,
                    command_id=revision.command_id,
                    placeholder_id=authority.placeholder_id,
                    player_id=authority.selected_candidate.player_id,
                )
                if rebuilt_input != revision.successor_draw_input:
                    raise ValueError("Lucky Loser fill Draw Input does not replay")
                rebuilt_revision = TournamentDrawRevisionBuilder.build_frozen_lucky_loser_fill(
                    predecessor=predecessor,
                    successor_field=previous_field,
                    successor_draw_input=rebuilt_input,
                    process_authority=process,
                    main_process_window_ordinal=(
                        revision.main_process_window_ordinal
                    ),
                    sequence=revision.sequence,
                    command_id=revision.command_id,
                    lucky_loser_fill_authority=rebuilt_authority,
                )
                if rebuilt_revision != revision:
                    raise ValueError("Lucky Loser fill Draw revision does not replay")
                out.append(revision)
                previous_draw_input = revision.successor_draw_input
                predecessor = revision.successor_draw
                continue

            if revision.repair_kind == "lucky_loser_vacancy":
                authority = revision.lucky_loser_vacancy_authority
                if authority is None:
                    raise ValueError("Stored Lucky Loser vacancy lacks authority")
                if revision.successor_field != previous_field:
                    raise ValueError(
                        "Lucky Loser vacancy unexpectedly changed Tournament Entry Field"
                    )
                q_start = self._qualification_start_authority(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    qualification_player_ids=(
                        initial_draw_input.qualification_player_ids
                    ),
                )
                ordinal = 1 + sum(
                    1
                    for prior in out
                    if prior.repair_kind == "lucky_loser_vacancy"
                )
                rebuilt_authority = (
                    TournamentLuckyLoserVacancyAuthorityBuilder.build(
                        predecessor=predecessor,
                        predecessor_draw_input=previous_draw_input,
                        command_id=revision.command_id,
                        withdrawn_player_id=authority.withdrawn_player_id,
                        lucky_loser_ordinal=ordinal,
                        withdrawn_player_cutoff_authority=(
                            authority.withdrawn_player_cutoff_authority
                        ),
                        qualification_start_authority=q_start,
                        qualification_origin_player_ids=(
                            initial_draw_input.qualification_player_ids
                        ),
                        replacement_source_authority=(
                            revision.replacement_source_authority
                        ),
                    )
                )
                if rebuilt_authority != authority:
                    raise ValueError(
                        "Lucky Loser vacancy authority does not replay"
                    )
                rebuilt_input = (
                    TournamentDrawInputAuthorityBuilder.build_lucky_loser_vacancy(
                        previous=previous_draw_input,
                        command_id=revision.command_id,
                        withdrawn_player_id=authority.withdrawn_player_id,
                        placeholder_id=authority.placeholder_id,
                        vacated_main_seed_number=authority.vacated_main_seed_number,
                        replacement_source_authority_fingerprint=(
                            revision.replacement_source_authority.fingerprint
                            if revision.replacement_source_authority is not None
                            else None
                        ),
                    )
                )
                if rebuilt_input != revision.successor_draw_input:
                    raise ValueError(
                        "Lucky Loser successor Draw Input does not replay"
                    )
                rebuilt_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_lucky_loser_vacancy(
                        predecessor=predecessor,
                        successor_field=previous_field,
                        successor_draw_input=rebuilt_input,
                        process_authority=process,
                        main_process_window_ordinal=(
                            revision.main_process_window_ordinal
                        ),
                        sequence=revision.sequence,
                        command_id=revision.command_id,
                        lucky_loser_vacancy_authority=rebuilt_authority,
                        replacement_source_authority=(
                            revision.replacement_source_authority
                        ),
                    )
                )
                if rebuilt_revision != revision:
                    raise ValueError(
                        "Lucky Loser Draw revision does not replay"
                    )
                out.append(revision)
                previous_draw_input = revision.successor_draw_input
                predecessor = revision.successor_draw
                continue

            if revision.repair_kind == "frozen_wild_card_repair":
                authority = revision.wild_card_repair_authority
                if authority is None:
                    raise ValueError("Stored frozen WC repair lacks authority")
                if revision.successor_field != previous_field:
                    raise ValueError(
                        "Frozen WC repair unexpectedly changed Tournament Entry Field"
                    )
                base_wc = TournamentWildCardAuthorityStore(self.session).get(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                )
                if base_wc is None:
                    raise ValueError(
                        "Frozen WC repair references missing base WC authority"
                    )
                rebuilt_wc = TournamentPostDrawWildCardRepairAuthorityBuilder.build(
                    predecessor=predecessor,
                    predecessor_draw_input=previous_draw_input,
                    base_wild_card_authority=base_wc,
                    command_id=revision.command_id,
                    withdrawn_player_id=authority.withdrawn_player_id,
                    unavailable_player_ids=authority.unavailable_player_ids,
                    replacement_cutoff_authority=(
                        authority.replacement_cutoff_authority
                    ),
                )
                if rebuilt_wc != authority:
                    raise ValueError(
                        "Frozen WC repair authority does not replay from frozen evidence"
                    )
                rebuilt_input = (
                    TournamentDrawInputAuthorityBuilder.build_post_draw_wild_card_repair(
                        previous=previous_draw_input,
                        command_id=revision.command_id,
                        withdrawn_player_id=authority.withdrawn_player_id,
                        replacement_player_id=authority.replacement_player_id,
                        repair_authority_fingerprint=authority.fingerprint,
                        qualification_replacement_player_id=(
                            authority.replacement_player_id
                            if authority.replacement_source == "qualification"
                            else None
                        ),
                        qualification_backfill_player_id=(
                            authority.qualification_backfill_player_id
                            if authority.replacement_source == "qualification"
                            else None
                        ),
                        main_vacated_seed_number=authority.vacated_main_seed_number,
                        qualification_vacated_seed_number=(
                            authority.vacated_qualification_seed_number
                        ),
                        qualification_full_redraw_reseed=(
                            revision.qualification_repair_action == "full_redraw"
                        ),
                    )
                )
                if rebuilt_input != revision.successor_draw_input:
                    raise ValueError(
                        "Frozen WC successor Draw Input does not replay"
                    )
                rebuilt_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_wild_card_repair(
                        predecessor=predecessor,
                        successor_field=previous_field,
                        successor_draw_input=rebuilt_input,
                        process_authority=process,
                        main_process_window_ordinal=(
                            revision.main_process_window_ordinal
                        ),
                        qualification_process_window_ordinal=(
                            revision.qualification_process_window_ordinal
                        ),
                        repair_draw_seed=revision.repair_draw_seed,
                        sequence=revision.sequence,
                        command_id=revision.command_id,
                        wild_card_repair_authority=rebuilt_wc,
                    )
                )
                if rebuilt_revision != revision:
                    raise ValueError(
                        "Frozen WC Draw revision does not replay from frozen evidence"
                    )
                out.append(revision)
                previous_draw_input = revision.successor_draw_input
                predecessor = revision.successor_draw
                continue

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
                        "Phase-aware Draw repair unexpectedly changed Draw seed"
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
                    replacement_cutoff_authorities=(
                        revision.replacement_cutoff_authorities
                    ),
                )
            elif revision.repair_kind == "seed_cascade_phase":
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
                        replacement_cutoff_authorities=(
                            revision.replacement_cutoff_authorities
                        ),
                    )
                )
            else:
                rebuilt_revision = (
                    TournamentDrawRevisionBuilder.build_draw_frozen_phase(
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
                        replacement_cutoff_authorities=(
                            revision.replacement_cutoff_authorities
                        ),
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
        cutoff_authorities = self._replacement_cutoff_authorities(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_ids=requested,
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
            "replacement_cutoff_authority_fingerprints": [
                authority.fingerprint for authority in cutoff_authorities
            ],
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
            replacement_cutoff_authorities=cutoff_authorities,
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
        cutoff_authorities = self._replacement_cutoff_authorities(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_ids=requested,
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
            "replacement_cutoff_authority_fingerprints": [
                authority.fingerprint for authority in cutoff_authorities
            ],
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
            replacement_cutoff_authorities=cutoff_authorities,
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



    def apply_frozen_ordinary_fallback(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        main_process_window_ordinal: int,
        replacement_source_authority,
    ) -> TournamentDrawRevision:
        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        history = self.history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        if retry is not None:
            revision = next(
                (item for item in history if item.command_id == command_id),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Frozen ordinary fallback command exists outside validated history"
                )
            if (
                retry.event_id != event_id
                or revision.repair_kind != "frozen_ordinary_fallback"
                or revision.main_process_window_ordinal
                != main_process_window_ordinal
                or revision.replacement_source_authority
                != replacement_source_authority
            ):
                raise TournamentDrawRevisionConflict(
                    "Frozen ordinary fallback command already has a different request"
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
                "Frozen ordinary fallback requires canonical Draw authority"
            )
        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if original_input is None or process is None:
            raise ValueError(
                "Frozen ordinary fallback requires Draw Input and process authority"
            )
        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )

        field_store = TournamentEntryFieldStore(self.session)
        field_rows = field_store._rows(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not field_rows:
            raise ValueError(
                "Frozen ordinary fallback requires Tournament Entry Field"
            )
        persisted_field, _ = field_store._load_row(field_rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )

        authority = replacement_source_authority
        if authority.source not in {"external_reserve", "bye"}:
            raise TournamentDrawRevisionConflict(
                "Frozen ordinary fallback requires external reserve or BYE source"
            )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.predecessor_draw_fingerprint,
            authority.predecessor_draw_input_fingerprint,
        ) != (
            run_id,
            branch_id,
            event_id,
            predecessor.fingerprint,
            previous_input.fingerprint,
        ):
            raise TournamentDrawRevisionConflict(
                "Frozen ordinary fallback source authority is stale"
            )
        slot = predecessor.main.slots[authority.physical_slot_index - 1]
        if slot.player_id != authority.withdrawn_player_id:
            raise TournamentDrawRevisionConflict(
                "Frozen ordinary fallback physical slot is stale"
            )

        try:
            successor_input = (
                TournamentDrawInputAuthorityBuilder.build_frozen_ordinary_fallback(
                    previous=previous_input,
                    command_id=command_id,
                    withdrawn_player_id=authority.withdrawn_player_id,
                    replacement_source_authority_fingerprint=authority.fingerprint,
                    replacement_player_id=(
                        authority.selected_player_id
                        if authority.source == "external_reserve"
                        else None
                    ),
                    vacated_main_seed_number=slot.seed_number,
                    create_bye=authority.source == "bye",
                )
            )
            revision = (
                TournamentDrawRevisionBuilder.build_frozen_ordinary_fallback(
                    predecessor=predecessor,
                    successor_field=previous_field,
                    successor_draw_input=successor_input,
                    process_authority=process,
                    main_process_window_ordinal=main_process_window_ordinal,
                    sequence=len(history) + 1,
                    command_id=command_id,
                    replacement_source_authority=authority,
                )
            )
        except ValueError as exc:
            raise TournamentDrawRevisionConflict(str(exc)) from exc

        request = {
            "repair_kind": "frozen_ordinary_fallback",
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "replacement_source_authority_fingerprint": authority.fingerprint,
            "main_process_window_ordinal": main_process_window_ordinal,
        }
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

    def draw_frozen_lucky_loser_vacancy(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        withdrawn_player_id: str,
        main_process_window_ordinal: int,
        replacement_source_authority=None,
    ) -> TournamentDrawRevision:
        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        history = self.history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        if retry is not None:
            revision = next(
                (item for item in history if item.command_id == command_id),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Lucky Loser command exists outside validated history"
                )
            authority = revision.lucky_loser_vacancy_authority
            if (
                retry.event_id != event_id
                or revision.repair_kind != "lucky_loser_vacancy"
                or revision.main_process_window_ordinal
                != main_process_window_ordinal
                or authority is None
                or authority.withdrawn_player_id != withdrawn_player_id
                or revision.replacement_source_authority
                != replacement_source_authority
            ):
                raise TournamentDrawRevisionConflict(
                    "Lucky Loser command already has a different request"
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
            raise ValueError("Lucky Loser vacancy requires canonical Draw authority")

        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if original_input is None or process is None:
            raise ValueError(
                "Lucky Loser vacancy requires Draw Input and Draw process authority"
            )
        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )

        field_store = TournamentEntryFieldStore(self.session)
        field_rows = field_store._rows(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not field_rows:
            raise ValueError("Lucky Loser vacancy requires Tournament Entry Field")
        persisted_field, _ = field_store._load_row(field_rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )

        withdrawn_cutoff = self._replacement_cutoff_authorities(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_ids=(withdrawn_player_id,),
        )[0]
        q_start = self._qualification_start_authority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            qualification_player_ids=original_input.qualification_player_ids,
        )
        ordinal = 1 + sum(
            1
            for prior in history
            if prior.repair_kind == "lucky_loser_vacancy"
        )
        try:
            authority = TournamentLuckyLoserVacancyAuthorityBuilder.build(
                predecessor=predecessor,
                predecessor_draw_input=previous_input,
                command_id=command_id,
                withdrawn_player_id=withdrawn_player_id,
                lucky_loser_ordinal=ordinal,
                withdrawn_player_cutoff_authority=withdrawn_cutoff,
                qualification_start_authority=q_start,
                qualification_origin_player_ids=(
                    original_input.qualification_player_ids
                ),
                replacement_source_authority=replacement_source_authority,
            )
            successor_input = (
                TournamentDrawInputAuthorityBuilder.build_lucky_loser_vacancy(
                    previous=previous_input,
                    command_id=command_id,
                    withdrawn_player_id=withdrawn_player_id,
                    placeholder_id=authority.placeholder_id,
                    vacated_main_seed_number=authority.vacated_main_seed_number,
                    replacement_source_authority_fingerprint=(
                        replacement_source_authority.fingerprint
                        if replacement_source_authority is not None
                        else None
                    ),
                )
            )
            revision = (
                TournamentDrawRevisionBuilder.build_frozen_lucky_loser_vacancy(
                    predecessor=predecessor,
                    successor_field=previous_field,
                    successor_draw_input=successor_input,
                    process_authority=process,
                    main_process_window_ordinal=main_process_window_ordinal,
                    sequence=len(history) + 1,
                    command_id=command_id,
                    lucky_loser_vacancy_authority=authority,
                    replacement_source_authority=replacement_source_authority,
                )
            )
        except ValueError as exc:
            raise TournamentDrawRevisionConflict(str(exc)) from exc

        request = {
            "repair_kind": "lucky_loser_vacancy",
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "withdrawn_player_id": withdrawn_player_id,
            "main_process_window_ordinal": main_process_window_ordinal,
            "lucky_loser_ordinal": authority.lucky_loser_ordinal,
            "qualification_start_fingerprint": (
                authority.qualification_start_authority.fingerprint
            ),
            "replacement_source_authority_fingerprint": (
                replacement_source_authority.fingerprint
                if replacement_source_authority is not None
                else None
            ),
        }
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

    def fill_next_frozen_lucky_loser(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        main_process_window_ordinal: int,
        unavailable_player_ids: tuple[str, ...] = (),
    ) -> TournamentDrawRevision:
        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        history = self.history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        expected_unavailable = tuple(sorted(set(unavailable_player_ids)))
        if retry is not None:
            revision = next(
                (item for item in history if item.command_id == command_id),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Lucky Loser fill command exists outside validated history"
                )
            authority = revision.lucky_loser_fill_authority
            if (
                retry.event_id != event_id
                or revision.repair_kind != "lucky_loser_fill"
                or revision.main_process_window_ordinal
                != main_process_window_ordinal
                or authority is None
                or authority.unavailable_player_ids != expected_unavailable
            ):
                raise TournamentDrawRevisionConflict(
                    "Lucky Loser fill command already has a different request"
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
            raise ValueError("Lucky Loser fill requires canonical Draw authority")

        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if original_input is None or process is None:
            raise ValueError(
                "Lucky Loser fill requires Draw Input and Draw process authority"
            )
        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )

        field_store = TournamentEntryFieldStore(self.session)
        field_rows = field_store._rows(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not field_rows:
            raise ValueError("Lucky Loser fill requires Tournament Entry Field")
        persisted_field, _ = field_store._load_row(field_rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )

        prior_fill = next(
            (
                item.lucky_loser_fill_authority
                for item in reversed(history)
                if item.repair_kind == "lucky_loser_fill"
                and item.lucky_loser_fill_authority is not None
            ),
            None,
        )
        if prior_fill is not None:
            order_authority = prior_fill.order_authority
        else:
            order_authority = TournamentLuckyLoserOrderAuthorityStore(
                self.session
            ).resolve_for_draw(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                draw=predecessor,
            )

        try:
            authority = TournamentLuckyLoserFillAuthorityBuilder.build(
                predecessor=predecessor,
                predecessor_draw_input=previous_input,
                command_id=command_id,
                order_authority=order_authority,
                unavailable_player_ids=expected_unavailable,
            )
            successor_input = TournamentDrawInputAuthorityBuilder.build_lucky_loser_fill(
                previous=previous_input,
                command_id=command_id,
                placeholder_id=authority.placeholder_id,
                player_id=authority.selected_candidate.player_id,
            )
            revision = TournamentDrawRevisionBuilder.build_frozen_lucky_loser_fill(
                predecessor=predecessor,
                successor_field=previous_field,
                successor_draw_input=successor_input,
                process_authority=process,
                main_process_window_ordinal=main_process_window_ordinal,
                sequence=len(history) + 1,
                command_id=command_id,
                lucky_loser_fill_authority=authority,
            )
        except ValueError as exc:
            raise TournamentDrawRevisionConflict(str(exc)) from exc

        request = {
            "repair_kind": "lucky_loser_fill",
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "main_process_window_ordinal": main_process_window_ordinal,
            "placeholder_id": authority.placeholder_id,
            "selected_player_id": authority.selected_candidate.player_id,
            "order_authority_fingerprint": authority.order_authority.fingerprint,
            "unavailable_player_ids": list(expected_unavailable),
        }
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

    def draw_frozen_wild_card_withdrawal(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
        withdrawn_player_id: str,
        main_process_window_ordinal: int,
        qualification_process_window_ordinal: int | None = None,
        repair_draw_seed: int | None = None,
        unavailable_reserve_player_ids: tuple[str, ...] = (),
    ) -> TournamentDrawRevision:
        draw_store = TournamentDrawAuthorityStore(self.session)
        draw_store._scope(run_id, branch_id, writing=True)

        history = self.history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        retry = self.session.scalar(
            select(TournamentDrawRevisionModel).where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.command_id == command_id,
            )
        )
        if retry is not None:
            revision = next(
                (item for item in history if item.command_id == command_id),
                None,
            )
            if revision is None:
                raise ValueError(
                    "Frozen WC repair command exists outside validated history"
                )
            authority = revision.wild_card_repair_authority
            expected_unavailable = tuple(
                sorted(set(unavailable_reserve_player_ids))
            )
            if (
                retry.event_id != event_id
                or revision.repair_kind != "frozen_wild_card_repair"
                or revision.main_process_window_ordinal
                != main_process_window_ordinal
                or revision.qualification_process_window_ordinal
                != qualification_process_window_ordinal
                or revision.repair_draw_seed != repair_draw_seed
                or authority is None
                or authority.withdrawn_player_id != withdrawn_player_id
                or authority.unavailable_player_ids != expected_unavailable
            ):
                raise TournamentDrawRevisionConflict(
                    "Frozen WC repair command already has a different request"
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
            raise ValueError("Frozen WC repair requires canonical Draw authority")

        original_input = TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        process = TournamentDrawProcessAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        base_wc = TournamentWildCardAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if original_input is None or process is None or base_wc is None:
            raise ValueError(
                "Frozen WC repair requires Draw Input, Draw process and WC authority"
            )
        previous_input = (
            history[-1].successor_draw_input if history else original_input
        )

        field_store = TournamentEntryFieldStore(self.session)
        field_rows = field_store._rows(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not field_rows:
            raise ValueError("Frozen WC repair requires Tournament Entry Field")
        persisted_field, _ = field_store._load_row(field_rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )

        cutoff = self._replacement_cutoff_authorities(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_ids=(withdrawn_player_id,),
        )[0]
        unavailable = tuple(sorted(set(unavailable_reserve_player_ids)))
        try:
            wc_repair = TournamentPostDrawWildCardRepairAuthorityBuilder.build(
                predecessor=predecessor,
                predecessor_draw_input=previous_input,
                base_wild_card_authority=base_wc,
                command_id=command_id,
                withdrawn_player_id=withdrawn_player_id,
                unavailable_player_ids=unavailable,
                replacement_cutoff_authority=cutoff,
            )
        except ValueError as exc:
            raise TournamentDrawRevisionConflict(str(exc)) from exc

        qualification_phase = None
        if wc_repair.replacement_source == "qualification":
            if qualification_process_window_ordinal is None:
                raise TournamentDrawRevisionConflict(
                    "Qualification RWC promotion requires Q process-window evidence"
                )
            qualification_phase = process.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            )
            if qualification_phase == "full_redraw":
                if repair_draw_seed is None:
                    raise TournamentDrawRevisionConflict(
                        "Qualification RWC full redraw requires repair draw seed"
                    )
            elif repair_draw_seed is not None:
                raise TournamentDrawRevisionConflict(
                    "Qualification RWC repair outside full redraw cannot use draw seed"
                )
        else:
            if qualification_process_window_ordinal is not None:
                raise TournamentDrawRevisionConflict(
                    "External RWC repair cannot carry Q process-window evidence"
                )
            if repair_draw_seed is not None:
                raise TournamentDrawRevisionConflict(
                    "External RWC repair cannot introduce draw seed"
                )

        successor_input = (
            TournamentDrawInputAuthorityBuilder.build_post_draw_wild_card_repair(
                previous=previous_input,
                command_id=command_id,
                withdrawn_player_id=withdrawn_player_id,
                replacement_player_id=wc_repair.replacement_player_id,
                repair_authority_fingerprint=wc_repair.fingerprint,
                qualification_replacement_player_id=(
                    wc_repair.replacement_player_id
                    if wc_repair.replacement_source == "qualification"
                    else None
                ),
                qualification_backfill_player_id=(
                    wc_repair.qualification_backfill_player_id
                    if wc_repair.replacement_source == "qualification"
                    else None
                ),
                main_vacated_seed_number=wc_repair.vacated_main_seed_number,
                qualification_vacated_seed_number=(
                    wc_repair.vacated_qualification_seed_number
                ),
                qualification_full_redraw_reseed=(
                    qualification_phase == "full_redraw"
                ),
            )
        )
        sequence = len(history) + 1
        revision = TournamentDrawRevisionBuilder.build_frozen_wild_card_repair(
            predecessor=predecessor,
            successor_field=previous_field,
            successor_draw_input=successor_input,
            process_authority=process,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=(
                qualification_process_window_ordinal
            ),
            repair_draw_seed=repair_draw_seed,
            sequence=sequence,
            command_id=command_id,
            wild_card_repair_authority=wc_repair,
        )
        request = {
            "repair_kind": "frozen_wild_card_repair",
            "predecessor_draw_fingerprint": predecessor.fingerprint,
            "withdrawn_player_id": withdrawn_player_id,
            "main_process_window_ordinal": main_process_window_ordinal,
            "qualification_process_window_ordinal": (
                qualification_process_window_ordinal
            ),
            "repair_draw_seed": repair_draw_seed,
            "unavailable_reserve_player_ids": list(unavailable),
            "wild_card_repair_authority_fingerprint": wc_repair.fingerprint,
        }
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

    def draw_frozen_phase_withdrawal(
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
                "Draw-Freeze phase withdrawal requires at least one player"
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
                or revision.repair_kind != "draw_frozen_phase"
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
                "Draw-Freeze phase repair requires canonical Draw authority"
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
                "Draw-Freeze phase repair requires Draw Input, Draw process "
                "and ranking authority"
            )
        if original_input.capacity.wild_card_slots:
            raise ValueError(
                "Draw-Freeze phase repair with WC/RWC requires "
                "dedicated WC repair authority"
            )

        field_store = TournamentEntryFieldStore(self.session)
        rows = field_store._rows(
            run_id=run_id, branch_id=branch_id, event_id=event_id
        )
        if not rows:
            raise ValueError(
                "Draw-Freeze phase repair requires canonical Tournament Entry Field"
            )
        persisted_field, applications = field_store._load_row(rows[-1])
        previous_field = (
            history[-1].successor_field if history else persisted_field
        )
        cutoff_authorities = self._replacement_cutoff_authorities(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_ids=requested,
        )
        successor_field = TournamentEntryFieldResolver.repair_pre_draw(
            authority=ranking,
            applications=applications,
            previous=previous_field,
            withdrawn_player_ids=requested,
        )
        if successor_field == previous_field:
            raise TournamentDrawRevisionConflict(
                "Draw-Freeze phase withdrawal contains no new active-field change"
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
            "repair_kind": "draw_frozen_phase",
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
            "replacement_cutoff_authority_fingerprints": [
                authority.fingerprint for authority in cutoff_authorities
            ],
        }
        revision = TournamentDrawRevisionBuilder.build_draw_frozen_phase(
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
            replacement_cutoff_authorities=cutoff_authorities,
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
