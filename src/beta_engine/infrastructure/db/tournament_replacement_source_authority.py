"""Resolve the canonical Main Draw replacement source from persisted authority."""

from __future__ import annotations

from sqlalchemy import select

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentDrawStartEvidence,
    TournamentReplacementSourceAuthority,
    TournamentReplacementSourceAuthorityBuilder,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult
from beta_engine.infrastructure.db.models import (
    SimulationEventGroupModel,
    TournamentDrawRevisionModel,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthorityStore,
    TournamentLuckyLoserOrderUnavailable,
)
from beta_engine.infrastructure.db.tournament_replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)


class TournamentReplacementSourceUnavailable(ValueError):
    pass


class TournamentReplacementSourceAuthorityStore:
    """Resolve one current Main vacancy source without mutating the Draw."""

    def __init__(self, session):
        self.session = session

    def _latest_revision(self, *, run_id: str, branch_id: str, event_id: str):
        row = self.session.scalar(
            select(TournamentDrawRevisionModel)
            .where(
                TournamentDrawRevisionModel.run_id == run_id,
                TournamentDrawRevisionModel.branch_id == branch_id,
                TournamentDrawRevisionModel.event_id == event_id,
            )
            .order_by(TournamentDrawRevisionModel.sequence.desc())
        )
        if row is None:
            return None
        from beta_engine.domain.tournaments.draw_revision_authority import (
            TournamentDrawRevision,
        )
        return TournamentDrawRevision.model_validate_json(row.payload_json)

    def _current_draw_input(self, *, run_id: str, branch_id: str, event_id: str):
        revision = self._latest_revision(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if revision is not None:
            return revision.successor_draw_input
        return TournamentDrawInputAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )

    def _current_field(self, *, run_id: str, branch_id: str, event_id: str):
        revision = self._latest_revision(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if revision is not None:
            return revision.successor_field
        field_store = TournamentEntryFieldStore(self.session)
        rows = field_store._rows(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if not rows:
            return None
        field, _ = field_store._load_row(rows[-1])
        return field

    def _first_start_evidence(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        node_ids: set[str],
        real_only: bool,
    ) -> TournamentDrawStartEvidence | None:
        if not node_ids:
            return None
        rows = self.session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
            )
        ).all()
        candidates = []
        for row in rows:
            if row.match_id not in node_ids:
                continue
            loaded = AuthoritativeSlotMatchExecutor._load_group(row)
            if loaded.authoritative_input.event_id != event_id:
                continue
            if real_only and isinstance(loaded.result, TournamentWalkoverResult):
                continue
            candidates.append(row)
        if not candidates:
            return None
        first = min(
            candidates,
            key=lambda row: (
                row.week_ordinal,
                row.slot_id,
                row.group_id,
                row.match_id,
            ),
        )
        return TournamentDrawStartEvidence(
            match_id=first.match_id,
            result_fingerprint=first.result_fingerprint,
        )

    def resolve(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        withdrawn_player_id: str,
        unavailable_player_ids: tuple[str, ...] = (),
    ) -> TournamentReplacementSourceAuthority:
        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        draw_input = self._current_draw_input(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None or draw_input is None:
            raise TournamentReplacementSourceUnavailable(
                "Replacement source requires canonical Draw and Draw Input"
            )

        cutoff = TournamentPlayerReplacementCutoffAuthorityStore(
            self.session
        ).resolve(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id=withdrawn_player_id,
        )

        q_node_ids = {
            node.node_id
            for bracket in draw.qualification_brackets
            for node in bracket.nodes
        }
        main_node_ids = {node.node_id for node in draw.main.nodes}
        qualification_start = self._first_start_evidence(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            node_ids=q_node_ids,
            real_only=True,
        )
        main_start = self._first_start_evidence(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            node_ids=main_node_ids,
            real_only=False,
        )

        wc = TournamentWildCardAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )

        ll_order = None
        if qualification_start is not None:
            try:
                ll_order = TournamentLuckyLoserOrderAuthorityStore(
                    self.session
                ).resolve_for_draw(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id=event_id,
                    draw=draw,
                )
            except TournamentLuckyLoserOrderUnavailable:
                ll_order = None

        if wc is not None:
            external_reserves = wc.adjusted_below_qualification_cut_player_ids
        else:
            field = self._current_field(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if field is None:
                raise TournamentReplacementSourceUnavailable(
                    "Replacement source requires Tournament Entry Field"
                )
            external_reserves = field.below_qualification_cut_player_ids

        try:
            return TournamentReplacementSourceAuthorityBuilder.build(
                predecessor=draw,
                predecessor_draw_input=draw_input,
                withdrawn_player_id=withdrawn_player_id,
                replacement_cutoff_authority=cutoff,
                qualification_start_evidence=qualification_start,
                main_start_evidence=main_start,
                base_wild_card_authority=wc,
                lucky_loser_order_authority=ll_order,
                external_reserve_player_ids=external_reserves,
                unavailable_player_ids=tuple(
                    sorted(set(unavailable_player_ids))
                ),
            )
        except ValueError as exc:
            raise TournamentReplacementSourceUnavailable(str(exc)) from exc
