"""One source-driven command for Main Draw replacement after Main Draw Freeze."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentReplacementSource,
    TournamentReplacementSourceAuthority,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    TournamentDrawRevisionConflict,
    TournamentDrawRevisionStore,
)
from beta_engine.infrastructure.db.tournament_replacement_source_authority import (
    TournamentReplacementSourceAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_walkover_authority import (
    TournamentWalkoverAuthorityStore,
)


class AuthoritativeFrozenMainReplacementConflict(ValueError):
    pass


@dataclass(frozen=True)
class AuthoritativeFrozenMainReplacementResult:
    source: TournamentReplacementSource
    source_authority: TournamentReplacementSourceAuthority | None
    draw_revisions: tuple[object, ...] = ()
    walkover_result: object | None = None


def _child_command_id(command_id: str, suffix: str) -> str:
    if not command_id or len(command_id) > 128:
        raise ValueError("Replacement orchestration requires a valid command ID")
    candidate = f"{command_id}:{suffix}"
    if len(candidate) <= 128:
        return candidate
    digest = hashlib.sha256(candidate.encode()).hexdigest()[:12]
    room = 128 - len(suffix) - len(digest) - 2
    return f"{command_id[:room]}:{suffix}:{digest}"


class AuthoritativeFrozenMainReplacement:
    """Dispatch one frozen-Main vacancy through the canonical source chain."""

    def __init__(self, session):
        self.session = session

    def _retry_from_history(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        command_id: str,
    ) -> AuthoritativeFrozenMainReplacementResult | None:
        history = TournamentDrawRevisionStore(self.session).history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        by_command = {item.command_id: item for item in history}
        rwc = by_command.get(_child_command_id(command_id, "rwc"))
        if rwc is not None:
            return AuthoritativeFrozenMainReplacementResult(
                source="reserve_wild_card",
                source_authority=None,
                draw_revisions=(rwc,),
            )
        q = by_command.get(_child_command_id(command_id, "q"))
        if q is not None:
            return AuthoritativeFrozenMainReplacementResult(
                source="qualification_promotion",
                source_authority=None,
                draw_revisions=(q,),
            )
        fallback = by_command.get(_child_command_id(command_id, "fallback"))
        if fallback is not None:
            authority = fallback.replacement_source_authority
            if authority is None:
                raise ValueError(
                    "Persisted replacement fallback lacks source authority"
                )
            return AuthoritativeFrozenMainReplacementResult(
                source=authority.source,
                source_authority=authority,
                draw_revisions=(fallback,),
            )
        vacancy = by_command.get(_child_command_id(command_id, "ll-vacancy"))
        fill = by_command.get(_child_command_id(command_id, "ll-fill"))
        if fill is not None:
            revisions = tuple(
                item for item in (vacancy, fill) if item is not None
            )
            return AuthoritativeFrozenMainReplacementResult(
                source="lucky_loser",
                source_authority=None,
                draw_revisions=revisions,
            )
        if vacancy is not None:
            return AuthoritativeFrozenMainReplacementResult(
                source="lucky_loser_pending",
                source_authority=None,
                draw_revisions=(vacancy,),
            )
        return None

    def execute(
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
        unavailable_player_ids: tuple[str, ...] = (),
        walkover_week: RankingWeek | None = None,
        walkover_slot_id: str | None = None,
        walkover_group_id: str | None = None,
    ) -> AuthoritativeFrozenMainReplacementResult:
        retry = self._retry_from_history(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id=command_id,
        )
        if retry is not None:
            return retry

        source = TournamentReplacementSourceAuthorityStore(self.session).resolve(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            withdrawn_player_id=withdrawn_player_id,
            unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
        )
        draw = TournamentDrawAuthorityStore(self.session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if draw is None:
            raise AuthoritativeFrozenMainReplacementConflict(
                "Replacement orchestration requires canonical active Draw"
            )
        target = draw.main.slots[source.physical_slot_index - 1]
        if target.player_id != withdrawn_player_id:
            raise AuthoritativeFrozenMainReplacementConflict(
                "Replacement source target no longer matches active Main slot"
            )

        revisions = TournamentDrawRevisionStore(self.session)

        if source.source == "walkover":
            if (
                walkover_week is None
                or walkover_slot_id is None
                or walkover_group_id is None
            ):
                raise AuthoritativeFrozenMainReplacementConflict(
                    "W/O source requires authoritative week, slot and group target"
                )
            result = TournamentWalkoverAuthorityStore(self.session).commit(
                run_id=run_id,
                branch_id=branch_id,
                week=walkover_week,
                event_id=event_id,
                command_id=_child_command_id(command_id, "wo"),
                withdrawn_player_id=withdrawn_player_id,
                slot_id=walkover_slot_id,
                group_id=walkover_group_id,
            )
            return AuthoritativeFrozenMainReplacementResult(
                source=source.source,
                source_authority=source,
                walkover_result=result,
            )

        if source.source == "reserve_wild_card":
            selected = source.selected_player_id
            q_players = {
                slot.player_id
                for bracket in draw.qualification_brackets
                for slot in bracket.slots
                if slot.player_id is not None
            }
            cross_q = selected in q_players
            revision = revisions.draw_frozen_wild_card_withdrawal(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=_child_command_id(command_id, "rwc"),
                withdrawn_player_id=withdrawn_player_id,
                main_process_window_ordinal=main_process_window_ordinal,
                qualification_process_window_ordinal=(
                    qualification_process_window_ordinal if cross_q else None
                ),
                repair_draw_seed=repair_draw_seed if cross_q else None,
                unavailable_reserve_player_ids=tuple(
                    sorted(set(unavailable_player_ids))
                ),
            )
            authority = revision.wild_card_repair_authority
            if (
                authority is None
                or authority.replacement_player_id != source.selected_player_id
            ):
                raise AuthoritativeFrozenMainReplacementConflict(
                    "RWC mutation selected a different source player"
                )
            return AuthoritativeFrozenMainReplacementResult(
                source=source.source,
                source_authority=source,
                draw_revisions=(revision,),
            )

        if target.entry_status == "wild_card":
            raise AuthoritativeFrozenMainReplacementConflict(
                "Ordinary WC-slot fallback after RWC exhaustion is not canonical yet"
            )

        if source.source == "qualification_promotion":
            if unavailable_player_ids:
                raise AuthoritativeFrozenMainReplacementConflict(
                    "Source-aware unavailable Q-list skips require the later "
                    "pre-Q promotion slice"
                )
            revision = revisions.draw_frozen_phase_withdrawal(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=_child_command_id(command_id, "q"),
                withdrawn_player_ids=(withdrawn_player_id,),
                main_process_window_ordinal=main_process_window_ordinal,
                qualification_process_window_ordinal=(
                    qualification_process_window_ordinal
                ),
                repair_draw_seed=repair_draw_seed,
            )
            selected = source.selected_player_id
            if selected is None or all(
                slot.player_id != selected
                for slot in revision.successor_draw.main.slots
            ):
                raise AuthoritativeFrozenMainReplacementConflict(
                    "Q-promotion mutation selected a different source player"
                )
            return AuthoritativeFrozenMainReplacementResult(
                source=source.source,
                source_authority=source,
                draw_revisions=(revision,),
            )

        if source.source in {"lucky_loser_pending", "lucky_loser"}:
            vacancy = revisions.draw_frozen_lucky_loser_vacancy(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=_child_command_id(command_id, "ll-vacancy"),
                withdrawn_player_id=withdrawn_player_id,
                main_process_window_ordinal=main_process_window_ordinal,
            )
            if source.source == "lucky_loser_pending":
                return AuthoritativeFrozenMainReplacementResult(
                    source=source.source,
                    source_authority=source,
                    draw_revisions=(vacancy,),
                )
            fill = revisions.fill_next_frozen_lucky_loser(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=_child_command_id(command_id, "ll-fill"),
                main_process_window_ordinal=main_process_window_ordinal,
                unavailable_player_ids=tuple(
                    sorted(set(unavailable_player_ids))
                ),
            )
            authority = fill.lucky_loser_fill_authority
            if (
                authority is None
                or authority.selected_candidate.player_id
                != source.selected_player_id
            ):
                raise AuthoritativeFrozenMainReplacementConflict(
                    "Lucky Loser fill selected a different source player"
                )
            return AuthoritativeFrozenMainReplacementResult(
                source=source.source,
                source_authority=source,
                draw_revisions=(vacancy, fill),
            )

        if source.source in {"external_reserve", "bye"}:
            revision = revisions.apply_frozen_ordinary_fallback(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=_child_command_id(command_id, "fallback"),
                main_process_window_ordinal=main_process_window_ordinal,
                replacement_source_authority=source,
            )
            return AuthoritativeFrozenMainReplacementResult(
                source=source.source,
                source_authority=source,
                draw_revisions=(revision,),
            )

        raise AuthoritativeFrozenMainReplacementConflict(
            f"Unsupported replacement source: {source.source}"
        )
