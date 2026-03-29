"""Deterministic entry decision and acceptance list engine."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country
from beta_engine.domain.entries.models import (
    AcceptanceList,
    AcceptanceStatus,
    EntryDecision,
    EntryTarget,
    EntryTuningConfig,
    TournamentEntry,
)
from beta_engine.domain.players.models import Player
from beta_engine.domain.tournaments.models import CalendarEvent, TournamentTemplate


@dataclass(slots=True)
class EntryEngine:
    rng: DeterministicRng
    tuning: EntryTuningConfig

    def build_acceptance_list(
        self,
        *,
        event: CalendarEvent,
        template: TournamentTemplate,
        players: list[Player],
        countries_by_code: dict[str, Country],
    ) -> AcceptanceList:
        main_applicants: list[TournamentEntry] = []
        qualification_applicants: list[TournamentEntry] = []

        event_rng = self.rng.branch(SeedScope.WEEK, event.season, event.week, event.event_id)
        for player in players:
            country = countries_by_code.get(player.nationality)
            if country is None:
                continue
            decision = self.decide_entry(
                player=player,
                player_country=country,
                event=event,
                template=template,
                event_rng=event_rng,
            )
            if decision.target == EntryTarget.MAIN:
                main_applicants.append(
                    self._entry_from_decision(
                        decision=decision,
                        event=event,
                        template=template,
                        status=AcceptanceStatus.APPLICANT_MAIN,
                    )
                )
            elif decision.target == EntryTarget.QUALIFICATION:
                qualification_applicants.append(
                    self._entry_from_decision(
                        decision=decision,
                        event=event,
                        template=template,
                        status=AcceptanceStatus.APPLICANT_QUALIFICATION,
                    )
                )

        ranked_main = self._sort_entries(main_applicants)
        ranked_qualification = self._sort_entries(qualification_applicants)

        reserved_main_slots = (
            template.qualifier_spots
            + template.wild_cards
            + self.tuning.withdrawal_placeholder_slots
            + self.tuning.late_replacement_placeholder_slots
            + self.tuning.direct_acceptance_slots_buffer
        )
        direct_slots = max(0, template.main_draw_size - reserved_main_slots)

        main_entries: list[TournamentEntry] = []
        for i, entry in enumerate(ranked_main):
            if i < direct_slots:
                main_entries.append(entry.model_copy(update={"status": AcceptanceStatus.DIRECT_ACCEPTANCE}))
            else:
                main_entries.append(entry.model_copy(update={"status": AcceptanceStatus.NOT_ACCEPTED}))

        accepted_qualification = ranked_qualification[: template.qualification_draw_size]
        qualification_entries: list[TournamentEntry] = [
            entry.model_copy(update={"status": AcceptanceStatus.QUALIFICATION_ACCEPTANCE})
            for entry in accepted_qualification
        ]

        main_entries.extend(
            self._placeholder_entries(
                event=event,
                template=template,
                slot=EntryTarget.MAIN,
                status=AcceptanceStatus.QUALIFIER_PLACEHOLDER,
                count=template.qualifier_spots,
                reason="reserved_for_qualifiers",
            )
        )
        main_entries.extend(
            self._placeholder_entries(
                event=event,
                template=template,
                slot=EntryTarget.MAIN,
                status=AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                count=template.wild_cards,
                reason="commissioner_wild_card",
            )
        )
        main_entries.extend(
            self._placeholder_entries(
                event=event,
                template=template,
                slot=EntryTarget.MAIN,
                status=AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
                count=self.tuning.withdrawal_placeholder_slots,
                reason="anticipated_pre_draw_withdrawal",
            )
        )
        main_entries.extend(
            self._placeholder_entries(
                event=event,
                template=template,
                slot=EntryTarget.MAIN,
                status=AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
                count=self.tuning.late_replacement_placeholder_slots,
                reason="late_replacement_or_lucky_loser_hook",
            )
        )

        return AcceptanceList(
            event_id=event.event_id,
            template_id=template.template_id,
            season=event.season,
            week=event.week,
            main_draw_size=template.main_draw_size,
            qualification_draw_size=template.qualification_draw_size,
            qualifier_spots=template.qualifier_spots,
            wild_card_slots=template.wild_cards,
            main_draw_applicants=ranked_main,
            qualification_applicants=ranked_qualification,
            main_draw_entries=self._sort_entries(main_entries),
            qualification_entries=self._sort_entries(qualification_entries),
            pending_week_conflict_resolution=True,
        )

    def decide_entry(
        self,
        *,
        player: Player,
        player_country: Country,
        event: CalendarEvent,
        template: TournamentTemplate,
        event_rng: DeterministicRng,
    ) -> EntryDecision:
        quality_score = self._player_quality(player)
        strength_score = self._tournament_strength(template)
        prestige_score = self._tournament_prestige(template)
        travel_score = self._travel_score(player_country, event)
        age_score = self._age_score(player.age)

        traits = player.hidden_career_traits
        weighted_score = (
            self.tuning.baseline_bias
            + quality_score * self.tuning.player_quality_weight
            + strength_score * self.tuning.tournament_strength_weight
            + prestige_score * self.tuning.prestige_weight
            + travel_score * self.tuning.travel_weight
            + traits.ambition * self.tuning.ambition_weight
            + traits.professionalism * self.tuning.professionalism_weight
            + traits.schedule_aggression * self.tuning.schedule_aggression_weight
            + traits.travel_tolerance * self.tuning.travel_tolerance_weight
            + age_score * self.tuning.age_weight
        )
        entry_probability = self._sigmoid(weighted_score)

        player_rng = event_rng.branch(SeedScope.MATCH, player.player_id)
        roll = player_rng.random()
        if roll > entry_probability:
            target = EntryTarget.NONE
        elif quality_score + traits.ambition * 0.1 >= self.tuning.main_quality_target - self.tuning.main_margin:
            target = EntryTarget.MAIN
        elif quality_score + traits.schedule_aggression * 0.08 >= self.tuning.qualification_quality_target - self.tuning.qualification_margin:
            target = EntryTarget.QUALIFICATION
        else:
            target = EntryTarget.NONE

        return EntryDecision(
            player_id=player.player_id,
            event_id=event.event_id,
            week=event.week,
            target=target,
            entry_score=round(weighted_score, 6),
            entry_probability=round(entry_probability, 6),
            travel_score=round(travel_score, 6),
            quality_score=round(quality_score, 6),
            prestige_score=round(prestige_score, 6),
        )

    def _entry_from_decision(
        self,
        *,
        decision: EntryDecision,
        event: CalendarEvent,
        template: TournamentTemplate,
        status: AcceptanceStatus,
    ) -> TournamentEntry:
        slot = EntryTarget.MAIN if status == AcceptanceStatus.APPLICANT_MAIN else EntryTarget.QUALIFICATION
        return TournamentEntry(
            entry_id=f"{event.event_id}:{decision.player_id}:{slot.value}",
            event_id=event.event_id,
            season=event.season,
            week=event.week,
            player_id=decision.player_id,
            slot=slot,
            status=status,
            tour_level=template.tour_level,
            category=template.category,
            quality_score=decision.quality_score,
            entry_score=decision.entry_score,
            ranking_priority=0,
        )

    def _placeholder_entries(
        self,
        *,
        event: CalendarEvent,
        template: TournamentTemplate,
        slot: EntryTarget,
        status: AcceptanceStatus,
        count: int,
        reason: str,
    ) -> list[TournamentEntry]:
        return [
            TournamentEntry(
                entry_id=f"{event.event_id}:{status.value}:{i + 1}",
                event_id=event.event_id,
                season=event.season,
                week=event.week,
                player_id=None,
                slot=slot,
                status=status,
                tour_level=template.tour_level,
                category=template.category,
                placeholder_reason=reason,
                ranking_priority=10_000 + i,
            )
            for i in range(count)
        ]

    @staticmethod
    def _player_quality(player: Player) -> float:
        total = (
            player.technique
            + player.movement
            + player.physical
            + player.mental
            + player.consistency
            + player.clutch
            + player.recovery
        )
        return total / (7 * 99)

    def _tournament_strength(self, template: TournamentTemplate) -> float:
        level_strength = self.tuning.tour_level_strength.get(template.tour_level, 0.5)
        category_strength = self.tuning.category_strength.get(template.category, 0.5)
        return min(1.0, max(0.0, (level_strength * 0.58 + category_strength * 0.42)))

    def _tournament_prestige(self, template: TournamentTemplate) -> float:
        level_prestige = self.tuning.tour_level_prestige.get(template.tour_level, 0.5)
        category_prestige = self.tuning.category_prestige.get(template.category, 0.5)
        return min(1.0, max(0.0, (level_prestige * 0.4 + category_prestige * 0.6)))

    @staticmethod
    def _travel_score(country: Country, event: CalendarEvent) -> float:
        if country.code == event.host_country:
            return 1.0
        affinity = country.travel_affinity.get(event.region)
        if affinity is not None:
            return min(1.0, max(0.0, affinity))
        if country.travel_region == event.region:
            return 0.72
        return 0.45

    @staticmethod
    def _age_score(age: int) -> float:
        peak_age = 27
        distance = abs(age - peak_age)
        return max(0.0, min(1.0, 1.0 - (distance / 20.0)))

    @staticmethod
    def _sort_entries(entries: list[TournamentEntry]) -> list[TournamentEntry]:
        ranked = sorted(
            entries,
            key=lambda entry: (
                -1.0 if entry.entry_score is None else -entry.entry_score,
                -1.0 if entry.quality_score is None else -entry.quality_score,
                "" if entry.player_id is None else entry.player_id,
                entry.entry_id,
            ),
        )
        normalized: list[TournamentEntry] = []
        for i, entry in enumerate(ranked, start=1):
            normalized.append(entry.model_copy(update={"ranking_priority": i}))
        return normalized

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1.0 / (1.0 + exp(-value))
