"""Branch-scoped player prize-money history derived from owned tournament sources."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import RunBranchModel
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)


PlayerPrizeMoneyHistoryStatus = Literal[
    "known",
    "unknown",
    "not_configured",
    "historical_unavailable",
]
PlayerPrizeMoneyCoverageStatus = Literal["complete", "partial"]


class PrizeMoneyCurrencyTotal(BaseModel):
    model_config = ConfigDict(frozen=True)

    currency: str = Field(min_length=3, max_length=3)
    amount: int = Field(ge=0)
    payout_count: int = Field(ge=0)


class PlayerPrizeMoneyHistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    edition_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    reached_stage: str = Field(min_length=1)
    payout_status: PlayerPrizeMoneyHistoryStatus
    amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    owned_source_schema_version: str = Field(min_length=1)
    owned_source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prize_authority_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )


class PlayerPrizeMoneySeasonSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    season_index: int = Field(ge=0)
    event_count: int = Field(ge=0)
    known_payout_count: int = Field(ge=0)
    unknown_payout_count: int = Field(ge=0)
    not_configured_count: int = Field(ge=0)
    historical_unavailable_count: int = Field(ge=0)
    known_totals_by_currency: tuple[PrizeMoneyCurrencyTotal, ...] = ()


class PlayerPrizeMoneyHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    coverage_status: PlayerPrizeMoneyCoverageStatus
    reporting_currency_status: Literal["requires_historical_fx_authority"] = (
        "requires_historical_fx_authority"
    )
    entries: tuple[PlayerPrizeMoneyHistoryEntry, ...] = ()
    season_summaries: tuple[PlayerPrizeMoneySeasonSummary, ...] = ()
    career_known_totals_by_currency: tuple[PrizeMoneyCurrencyTotal, ...] = ()
    known_payout_count: int = Field(ge=0)
    unknown_payout_count: int = Field(ge=0)
    not_configured_count: int = Field(ge=0)
    historical_unavailable_count: int = Field(ge=0)


class PlayerPrizeMoneyHistoryService:
    """Project immutable prize history without inventing cross-currency totals."""

    def __init__(self, session_factory):
        self._factory = session_factory

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        player_id: str,
    ) -> PlayerPrizeMoneyHistory:
        with self._factory() as session:
            branch = session.get(RunBranchModel, branch_id)
            if branch is None or branch.run_id != run_id:
                raise KeyError(
                    f"Run/Branch scope {run_id}/{branch_id} was not found"
                )

            sources = OwnedTournamentRankingSourceStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            if any(source is None for source in sources):
                raise ValueError(
                    "Owned tournament history contains a missing source"
                )

            entries: list[PlayerPrizeMoneyHistoryEntry] = []
            for source in sources:
                assert source is not None
                reached_stage = self._player_reached_stage(
                    source=source,
                    player_id=player_id,
                )
                if reached_stage is None:
                    continue

                if source.canonical_prize_awards is None:
                    entries.append(
                        PlayerPrizeMoneyHistoryEntry(
                            edition_id=source.binding.edition_id,
                            event_id=source.binding.event_id,
                            completed_week=source.binding.completed_week,
                            reached_stage=reached_stage,
                            payout_status="historical_unavailable",
                            amount=None,
                            currency=None,
                            owned_source_schema_version=source.schema_version,
                            owned_source_fingerprint=source.fingerprint,
                            prize_authority_fingerprint=None,
                        )
                    )
                    continue

                prize_authority = source.canonical_prize_awards
                player_award = next(
                    (
                        award
                        for award in prize_authority.awards
                        if award.player_id == player_id
                    ),
                    None,
                )
                if player_award is None:
                    raise ValueError(
                        "Prize-money authority omits a tournament-result player"
                    )
                if player_award.reached_stage != reached_stage:
                    raise ValueError(
                        "Prize-money history finishing stage differs from result"
                    )

                entries.append(
                    PlayerPrizeMoneyHistoryEntry(
                        edition_id=source.binding.edition_id,
                        event_id=source.binding.event_id,
                        completed_week=source.binding.completed_week,
                        reached_stage=reached_stage,
                        payout_status=player_award.payout_status,
                        amount=player_award.amount,
                        currency=player_award.currency,
                        owned_source_schema_version=source.schema_version,
                        owned_source_fingerprint=source.fingerprint,
                        prize_authority_fingerprint=prize_authority.fingerprint,
                    )
                )

        ordered_entries = tuple(
            sorted(
                entries,
                key=lambda item: (
                    item.completed_week.ordinal,
                    item.event_id,
                    item.edition_id,
                ),
            )
        )
        season_summaries = self._season_summaries(ordered_entries)
        career_totals = self._currency_totals(ordered_entries)

        known_count = sum(
            1 for entry in ordered_entries if entry.payout_status == "known"
        )
        unknown_count = sum(
            1 for entry in ordered_entries if entry.payout_status == "unknown"
        )
        not_configured_count = sum(
            1
            for entry in ordered_entries
            if entry.payout_status == "not_configured"
        )
        historical_unavailable_count = sum(
            1
            for entry in ordered_entries
            if entry.payout_status == "historical_unavailable"
        )

        return PlayerPrizeMoneyHistory(
            run_id=run_id,
            branch_id=branch_id,
            player_id=player_id,
            coverage_status=(
                "partial" if historical_unavailable_count else "complete"
            ),
            entries=ordered_entries,
            season_summaries=season_summaries,
            career_known_totals_by_currency=career_totals,
            known_payout_count=known_count,
            unknown_payout_count=unknown_count,
            not_configured_count=not_configured_count,
            historical_unavailable_count=historical_unavailable_count,
        )

    @staticmethod
    def _player_reached_stage(*, source, player_id: str) -> str | None:
        if source.canonical_result is not None:
            player = next(
                (
                    item
                    for item in source.canonical_result.players
                    if item.player_id == player_id
                ),
                None,
            )
            return player.reached_stage if player is not None else None

        if source.result is not None:
            player = next(
                (
                    item
                    for item in source.result.player_results
                    if item.player_id == player_id
                ),
                None,
            )
            return player.reached_stage if player is not None else None
        raise ValueError("Owned tournament source has no readable result authority")

    @classmethod
    def _season_summaries(
        cls,
        entries: tuple[PlayerPrizeMoneyHistoryEntry, ...],
    ) -> tuple[PlayerPrizeMoneySeasonSummary, ...]:
        grouped: dict[int, list[PlayerPrizeMoneyHistoryEntry]] = defaultdict(list)
        for entry in entries:
            grouped[entry.completed_week.season_index].append(entry)

        summaries: list[PlayerPrizeMoneySeasonSummary] = []
        for season_index in sorted(grouped):
            season_entries = tuple(grouped[season_index])
            summaries.append(
                PlayerPrizeMoneySeasonSummary(
                    season_index=season_index,
                    event_count=len(season_entries),
                    known_payout_count=sum(
                        1
                        for entry in season_entries
                        if entry.payout_status == "known"
                    ),
                    unknown_payout_count=sum(
                        1
                        for entry in season_entries
                        if entry.payout_status == "unknown"
                    ),
                    not_configured_count=sum(
                        1
                        for entry in season_entries
                        if entry.payout_status == "not_configured"
                    ),
                    historical_unavailable_count=sum(
                        1
                        for entry in season_entries
                        if entry.payout_status == "historical_unavailable"
                    ),
                    known_totals_by_currency=cls._currency_totals(season_entries),
                )
            )
        return tuple(summaries)

    @staticmethod
    def _currency_totals(
        entries: tuple[PlayerPrizeMoneyHistoryEntry, ...],
    ) -> tuple[PrizeMoneyCurrencyTotal, ...]:
        amount_by_currency: dict[str, int] = defaultdict(int)
        count_by_currency: dict[str, int] = defaultdict(int)
        for entry in entries:
            if (
                entry.payout_status != "known"
                or entry.amount is None
                or entry.currency is None
            ):
                continue
            amount_by_currency[entry.currency] += entry.amount
            count_by_currency[entry.currency] += 1

        return tuple(
            PrizeMoneyCurrencyTotal(
                currency=currency,
                amount=amount_by_currency[currency],
                payout_count=count_by_currency[currency],
            )
            for currency in sorted(amount_by_currency)
        )
