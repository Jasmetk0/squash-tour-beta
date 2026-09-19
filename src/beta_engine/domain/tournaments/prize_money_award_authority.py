"""Immutable Run-owned tournament prize-money award authority."""

from __future__ import annotations

import hashlib
import json
from math import ceil, log2
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.models import (
    CalendarEvent,
    PRIZE_MONEY_STAGE_ORDER,
)
from beta_engine.domain.tournaments.result_authority import TournamentResultAuthority


PrizeMoneyConfigurationStatus = Literal["not_configured", "partial", "complete"]
PrizeMoneyPayoutStatus = Literal["not_configured", "unknown", "known", "zero"]
PrizeMoneyZeroReason = Literal["replaced_before_first_real_match"]
PrizeMoneyTotalStatus = Literal["not_configured", "incomplete", "complete"]


class TournamentPlayerPrizeMoneyAwardAuthority(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: str = Field(min_length=1)
    payout_status: PrizeMoneyPayoutStatus
    amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    zero_reason: PrizeMoneyZeroReason | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    source_player_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentPrizeMoneyAwardAuthority(FrozenInput):
    """Canonical per-player tournament payouts in the Edition's original currency."""

    schema_version: Literal[
        "tournament_prize_money_award_authority.v1",
        "tournament_prize_money_award_authority.v2",
    ] = "tournament_prize_money_award_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    tournament_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    edition_prize_money_config_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_currency: str | None = Field(default=None, min_length=3, max_length=3)
    configured_stage_payouts: tuple[tuple[str, int | None], ...]
    required_stage_ids: tuple[str, ...]
    configuration_status: PrizeMoneyConfigurationStatus
    awards: tuple[TournamentPlayerPrizeMoneyAwardAuthority, ...]
    known_awarded_amount: int = Field(ge=0)
    unknown_award_count: int = Field(ge=0)
    total_prize_pool_status: PrizeMoneyTotalStatus
    total_prize_pool_amount: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_authority(self) -> "TournamentPrizeMoneyAwardAuthority":
        if self.original_currency is not None:
            normalized = self.original_currency.upper()
            if (
                self.original_currency != normalized
                or len(normalized) != 3
                or not normalized.isalpha()
            ):
                raise ValueError("Prize-money authority currency must be upper-case ISO-like code")

        stage_order = {stage: index for index, stage in enumerate(PRIZE_MONEY_STAGE_ORDER)}
        configured_ids = tuple(stage for stage, _ in self.configured_stage_payouts)
        if (
            len(configured_ids) != len(set(configured_ids))
            or any(stage not in stage_order for stage in configured_ids)
            or configured_ids
            != tuple(sorted(configured_ids, key=lambda stage: stage_order[stage]))
        ):
            raise ValueError("Prize-money authority stage table ordering is invalid")
        if (
            len(self.required_stage_ids) != len(set(self.required_stage_ids))
            or any(stage not in stage_order for stage in self.required_stage_ids)
            or self.required_stage_ids
            != tuple(sorted(self.required_stage_ids, key=lambda stage: stage_order[stage]))
        ):
            raise ValueError("Prize-money authority required-stage ordering is invalid")

        table = dict(self.configured_stage_payouts)
        known_values = [
            (stage, table[stage])
            for stage in configured_ids
            if table[stage] is not None
        ]
        previous = None
        for stage, amount in known_values:
            assert amount is not None
            if amount < 0:
                raise ValueError("Prize-money authority cannot freeze negative payouts")
            if previous is not None and amount <= previous:
                raise ValueError(
                    "Prize-money authority known payouts must strictly increase by stage"
                )
            previous = amount

        if any(amount is not None for _, amount in self.configured_stage_payouts):
            if self.original_currency is None:
                raise ValueError("Known prize-money payouts require original currency")

        expected_config_status = _configuration_status(
            table=table,
            required_stage_ids=self.required_stage_ids,
        )
        if self.configuration_status != expected_config_status:
            raise ValueError("Prize-money authority configuration status mismatch")

        config_payload = {
            "event_id": self.event_id,
            "original_currency": self.original_currency,
            "configured_stage_payouts": list(self.configured_stage_payouts),
            "required_stage_ids": list(self.required_stage_ids),
        }
        if _hash(config_payload) != self.edition_prize_money_config_fingerprint:
            raise ValueError("Prize-money authority configuration fingerprint mismatch")

        player_ids = tuple(award.player_id for award in self.awards)
        if not player_ids:
            raise ValueError("Prize-money authority requires player awards")
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Prize-money authority has duplicate player awards")

        known_sum = 0
        unknown_count = 0
        for award in self.awards:
            configured = table.get(award.reached_stage)
            if not table:
                expected_status: PrizeMoneyPayoutStatus = "not_configured"
                expected_amount = None
                expected_zero_reason = None
            elif (
                self.schema_version == "tournament_prize_money_award_authority.v2"
                and award.reached_stage == "qualification_winner"
            ):
                # A Qualification winner who is absent from Main at completed
                # tournament close is the canonical "replaced before first real
                # Main match" case. Master §19.1 makes that a known zero payout,
                # not an unknown stage-table value.
                expected_status = "zero"
                expected_amount = 0
                expected_zero_reason = "replaced_before_first_real_match"
            elif configured is None:
                expected_status = "unknown"
                expected_amount = None
                expected_zero_reason = None
            else:
                expected_status = "known"
                expected_amount = configured
                expected_zero_reason = None

            if self.schema_version == "tournament_prize_money_award_authority.v1":
                if award.payout_status == "zero" or award.zero_reason is not None:
                    raise ValueError(
                        "Historical prize-money authority v1 cannot carry zero-payout provenance"
                    )

            if (
                award.payout_status != expected_status
                or award.amount != expected_amount
                or award.zero_reason != expected_zero_reason
                or award.currency != self.original_currency
            ):
                raise ValueError("Prize-money player award differs from frozen stage table")
            if award.amount is not None:
                known_sum += award.amount
            else:
                unknown_count += 1

            award_schema_version = (
                "tournament_player_prize_money_award_authority.v2"
                if award.zero_reason is not None
                else "tournament_player_prize_money_award_authority.v1"
            )
            expected_award_payload = {
                "schema_version": award_schema_version,
                "event_id": self.event_id,
                "player_id": award.player_id,
                "reached_stage": award.reached_stage,
                "payout_status": award.payout_status,
                "amount": award.amount,
                "currency": award.currency,
                "source_tournament_result_fingerprint": self.tournament_result_fingerprint,
                "source_player_result_fingerprint": award.source_player_result_fingerprint,
                "edition_prize_money_config_fingerprint": self.edition_prize_money_config_fingerprint,
            }
            if award.zero_reason is not None:
                expected_award_payload["zero_reason"] = award.zero_reason
            expected_award_fp = _hash(expected_award_payload)
            if award.award_fingerprint != expected_award_fp:
                raise ValueError("Prize-money player award fingerprint mismatch")

        if self.known_awarded_amount != known_sum:
            raise ValueError("Prize-money authority known awarded amount mismatch")
        if self.unknown_award_count != unknown_count:
            raise ValueError("Prize-money authority unknown award count mismatch")

        expected_total_status: PrizeMoneyTotalStatus
        expected_total: int | None
        if not table:
            expected_total_status = "not_configured"
            expected_total = None
        elif self.configuration_status != "complete" or unknown_count:
            expected_total_status = "incomplete"
            expected_total = None
        else:
            expected_total_status = "complete"
            expected_total = known_sum

        if (
            self.total_prize_pool_status != expected_total_status
            or self.total_prize_pool_amount != expected_total
        ):
            raise ValueError("Prize-money authority total prize-pool status mismatch")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def build_tournament_prize_money_award_authority(
    *,
    result: TournamentResultAuthority,
    event: CalendarEvent,
) -> TournamentPrizeMoneyAwardAuthority:
    """Freeze Master §19.1 payouts from result finishing stages + Edition config."""

    if event.event_id != result.event_id:
        raise ValueError("Tournament prize-money event/result identity mismatch")

    stage_order = {stage: index for index, stage in enumerate(PRIZE_MONEY_STAGE_ORDER)}
    configured_stage_payouts = tuple(
        (stage, event.prize_money_table[stage])
        for stage in sorted(
            event.prize_money_table,
            key=lambda stage: stage_order[stage],
        )
    )
    required_stage_ids = _required_prize_money_stages(event)
    config_payload = {
        "event_id": event.event_id,
        "original_currency": event.prize_money_currency,
        "configured_stage_payouts": list(configured_stage_payouts),
        "required_stage_ids": list(required_stage_ids),
    }
    config_fp = _hash(config_payload)
    table = dict(configured_stage_payouts)
    configuration_status = _configuration_status(
        table=table,
        required_stage_ids=required_stage_ids,
    )

    awards: list[TournamentPlayerPrizeMoneyAwardAuthority] = []
    qualification_winner_ids = set(result.qualification_winner_ids)
    for player in sorted(result.players, key=lambda item: item.player_id):
        amount = table.get(player.reached_stage)
        zero_reason: PrizeMoneyZeroReason | None = None
        replaced_before_first_real_match = (
            player.player_id in qualification_winner_ids
            and player.draw_type == "qualification"
            and player.reached_stage == "qualification_winner"
        )
        if not table:
            payout_status: PrizeMoneyPayoutStatus = "not_configured"
            amount = None
        elif replaced_before_first_real_match:
            payout_status = "zero"
            amount = 0
            zero_reason = "replaced_before_first_real_match"
        elif amount is None:
            payout_status = "unknown"
        else:
            payout_status = "known"

        player_fp = _hash(player.model_dump(mode="json"))
        award_schema_version = (
            "tournament_player_prize_money_award_authority.v2"
            if zero_reason is not None
            else "tournament_player_prize_money_award_authority.v1"
        )
        award_payload = {
            "schema_version": award_schema_version,
            "event_id": result.event_id,
            "player_id": player.player_id,
            "reached_stage": player.reached_stage,
            "payout_status": payout_status,
            "amount": amount,
            "currency": event.prize_money_currency,
            "source_tournament_result_fingerprint": result.fingerprint,
            "source_player_result_fingerprint": player_fp,
            "edition_prize_money_config_fingerprint": config_fp,
        }
        if zero_reason is not None:
            award_payload["zero_reason"] = zero_reason
        award_fp = _hash(award_payload)
        awards.append(
            TournamentPlayerPrizeMoneyAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                payout_status=payout_status,
                amount=amount,
                currency=event.prize_money_currency,
                zero_reason=zero_reason,
                source_player_result_fingerprint=player_fp,
                award_fingerprint=award_fp,
            )
        )

    known_sum = sum(award.amount or 0 for award in awards)
    unknown_count = sum(1 for award in awards if award.amount is None)
    if not table:
        total_status: PrizeMoneyTotalStatus = "not_configured"
        total_amount = None
    elif configuration_status != "complete" or unknown_count:
        total_status = "incomplete"
        total_amount = None
    else:
        total_status = "complete"
        total_amount = known_sum

    return TournamentPrizeMoneyAwardAuthority(
        schema_version="tournament_prize_money_award_authority.v2",
        run_id=result.run_id,
        branch_id=result.branch_id,
        event_id=result.event_id,
        completed_week=result.completed_week,
        tournament_result_fingerprint=result.fingerprint,
        edition_prize_money_config_fingerprint=config_fp,
        original_currency=event.prize_money_currency,
        configured_stage_payouts=configured_stage_payouts,
        required_stage_ids=required_stage_ids,
        configuration_status=configuration_status,
        awards=tuple(awards),
        known_awarded_amount=known_sum,
        unknown_award_count=unknown_count,
        total_prize_pool_status=total_status,
        total_prize_pool_amount=total_amount,
    )


def _required_prize_money_stages(event: CalendarEvent) -> tuple[str, ...]:
    """Return physical finishing stages for the Edition's actual draw geometry."""

    main: list[str] = ["champion"]
    if event.main_draw_size >= 2:
        main.append("finalist")
    if event.main_draw_size >= 4:
        main.append("semifinal")
    if event.main_draw_size >= 8:
        main.append("quarterfinal")
    for size, stage in (
        (16, "round_of_16"),
        (32, "round_of_32"),
        (64, "round_of_64"),
        (128, "round_of_128"),
    ):
        if event.main_draw_size >= size:
            main.append(stage)

    qualification: list[str] = []
    if event.qualification_draw_size > 0:
        section_count = max(1, event.qualifier_spots)
        section_capacity = max(
            1,
            ceil(event.qualification_draw_size / section_count),
        )
        rounds = max(1, ceil(log2(section_capacity)))
        qualification.append("qualification_final")
        if rounds >= 2:
            qualification.append("qualification_semifinal")
        if rounds >= 3:
            qualification.append("qualification_round")

    order = {stage: index for index, stage in enumerate(PRIZE_MONEY_STAGE_ORDER)}
    return tuple(
        sorted(
            {*qualification, *main},
            key=lambda stage: order[stage],
        )
    )


def _configuration_status(
    *,
    table: dict[str, int | None],
    required_stage_ids: tuple[str, ...],
) -> PrizeMoneyConfigurationStatus:
    if not table:
        return "not_configured"
    if all(
        stage in table and table[stage] is not None
        for stage in required_stage_ids
    ):
        return "complete"
    return "partial"


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
