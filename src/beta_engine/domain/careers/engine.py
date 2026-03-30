"""Deterministic MVP career progression and season rollover engine."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.careers.models import (
    CareerProgressionResult,
    NextSeasonPlayerState,
    PlayerDevelopmentDelta,
    PlayerSeasonTransition,
    SeasonHealthInput,
    SeasonRolloverResult,
)
from beta_engine.domain.players import HiddenCareerTraits, Player

_ATTRIBUTES = ("technique", "movement", "physical", "mental", "consistency", "clutch", "recovery")


@dataclass(slots=True)
class CareerProgressionEngine:
    """Evolves players from one season to the next with explainable deltas."""

    rng: DeterministicRng

    def progress_player(
        self,
        *,
        from_season: int,
        to_season: int,
        player: Player,
        health_input: SeasonHealthInput,
    ) -> CareerProgressionResult:
        player_rng = self.rng.branch(SeedScope.SEASON, "career_progression", from_season, to_season, player.player_id)

        age_after = player.age + 1
        age_multiplier = self._age_curve_multiplier(age=age_after)
        trait_growth = self._trait_growth_factor(traits=player.hidden_career_traits)
        pressure = self._health_pressure(health_input=health_input, traits=player.hidden_career_traits)

        deltas: list[PlayerDevelopmentDelta] = []
        updates: dict[str, int] = {}
        for attribute in _ATTRIBUTES:
            before = getattr(player, attribute)
            attribute_noise = player_rng.uniform(-0.75, 0.75)
            tendency = self._attribute_tendency(attribute=attribute, traits=player.hidden_career_traits)
            potential_headroom = max(0.0, (player.hidden_career_traits.potential_ceiling - before) / 30.0)
            raw_delta = (
                age_multiplier
                + trait_growth
                + tendency
                + potential_headroom
                - pressure
                + attribute_noise
            )
            delta = self._quantize_delta(raw_delta=raw_delta, age=age_after)
            after = self._clamp_int(1, 99, before + delta)
            updates[attribute] = after
            deltas.append(
                PlayerDevelopmentDelta(
                    attribute=attribute,
                    before=before,
                    after=after,
                    delta=after - before,
                    reasons=self._delta_reasons(
                        age_after=age_after,
                        traits=player.hidden_career_traits,
                        health_input=health_input,
                        attribute=attribute,
                    ),
                )
            )

        style_change = self._should_evolve_style(player_rng=player_rng, player=player, age=age_after)
        next_player = player.model_copy(
            update={
                "age": age_after,
                **updates,
                "play_style": style_change[0],
                "archetype": style_change[1],
            }
        )

        readiness = self._next_season_readiness(health_input=health_input, traits=player.hidden_career_traits, recovery=updates["recovery"])
        carryover_fatigue = self._carryover_fatigue(health_input=health_input, traits=player.hidden_career_traits, recovery=updates["recovery"])

        transition = PlayerSeasonTransition(
            player_id=player.player_id,
            from_season=from_season,
            to_season=to_season,
            age_before=player.age,
            age_after=age_after,
            season_health_input=health_input,
            development_deltas=deltas,
            style_changed=style_change[2],
            style_change_reason=style_change[3],
            notes=[
                f"age_band={self._age_band(age_after)}",
                f"growth_curve={player.hidden_career_traits.growth_curve}",
            ],
        )

        return CareerProgressionResult(
            transition=transition,
            next_state=NextSeasonPlayerState(
                player=next_player,
                readiness=readiness,
                carryover_fatigue=carryover_fatigue,
            ),
        )

    def rollover_season(
        self,
        *,
        season: int,
        players: list[Player],
        health_inputs_by_player_id: dict[str, SeasonHealthInput] | None = None,
    ) -> SeasonRolloverResult:
        to_season = season + 1
        transitions: list[PlayerSeasonTransition] = []
        next_players: list[Player] = []
        next_states: dict[str, NextSeasonPlayerState] = {}
        health_inputs = health_inputs_by_player_id or {}

        for player in sorted(players, key=lambda p: p.player_id):
            progression = self.progress_player(
                from_season=season,
                to_season=to_season,
                player=player,
                health_input=health_inputs.get(player.player_id, SeasonHealthInput()),
            )
            transitions.append(progression.transition)
            next_players.append(progression.next_state.player)
            next_states[player.player_id] = progression.next_state

        return SeasonRolloverResult(
            from_season=season,
            to_season=to_season,
            transitions=transitions,
            next_players=next_players,
            next_states_by_player_id=next_states,
            placeholders=[
                "Retirements not yet modeled; all players retained.",
                "Rookie intake not yet modeled; next-season pool uses progressed incumbents only.",
            ],
        )

    @staticmethod
    def _delta_reasons(
        *,
        age_after: int,
        traits: HiddenCareerTraits,
        health_input: SeasonHealthInput,
        attribute: str,
    ) -> list[str]:
        reasons = [f"age_band={CareerProgressionEngine._age_band(age_after)}", f"growth_curve={traits.growth_curve}"]
        if traits.potential_ceiling >= 90:
            reasons.append("elite_potential")
        if traits.professionalism >= 0.75:
            reasons.append("high_professionalism")
        if traits.ambition >= 0.75:
            reasons.append("high_ambition")
        if health_input.wear_load >= 0.45:
            reasons.append("high_wear")
        if health_input.injury_events > 0:
            reasons.append("injury_carryover")
        if attribute == "recovery" and traits.resilience >= 0.75:
            reasons.append("resilience_support")
        return reasons

    @staticmethod
    def _age_band(age: int) -> str:
        if age <= 22:
            return "youth"
        if age <= 29:
            return "prime"
        return "decline_risk"

    @staticmethod
    def _age_curve_multiplier(*, age: int) -> float:
        if age <= 20:
            return 1.1
        if age <= 24:
            return 0.7
        if age <= 29:
            return 0.1
        if age <= 33:
            return -0.4
        return -0.9

    @staticmethod
    def _trait_growth_factor(*, traits: HiddenCareerTraits) -> float:
        growth_curve_bonus = {
            "early": 0.55,
            "balanced": 0.2,
            "late": 0.15,
            "steady": 0.1,
            "volatile": 0.0,
        }.get(traits.growth_curve, 0.05)
        return (
            growth_curve_bonus
            + (traits.professionalism - 0.5) * 0.8
            + (traits.ambition - 0.5) * 0.55
            + (traits.resilience - 0.5) * 0.35
        )

    @staticmethod
    def _attribute_tendency(*, attribute: str, traits: HiddenCareerTraits) -> float:
        if attribute == "mental":
            return (traits.professionalism - 0.5) * 0.3
        if attribute == "clutch":
            return (traits.ambition - 0.5) * 0.3
        if attribute == "recovery":
            return (traits.resilience - traits.injury_proneness) * 0.35
        if attribute == "physical":
            return -(traits.injury_proneness - 0.5) * 0.25
        return 0.0

    @staticmethod
    def _health_pressure(*, health_input: SeasonHealthInput, traits: HiddenCareerTraits) -> float:
        wear = health_input.wear_load * 1.1
        fatigue = health_input.fatigue_load * 0.75
        injury = min(0.65, health_input.injury_events * 0.16)
        proneness = traits.injury_proneness * 0.4
        resilience_buffer = traits.resilience * 0.35
        return max(0.0, wear + fatigue + injury + proneness - resilience_buffer)

    @staticmethod
    def _quantize_delta(*, raw_delta: float, age: int) -> int:
        base = int(round(raw_delta))
        if age >= 34:
            return max(-3, min(1, base))
        if age >= 30:
            return max(-2, min(2, base))
        return max(-2, min(3, base))

    @staticmethod
    def _next_season_readiness(*, health_input: SeasonHealthInput, traits: HiddenCareerTraits, recovery: int) -> float:
        value = (
            0.86
            - health_input.fatigue_load * 0.32
            - health_input.wear_load * 0.28
            - min(0.24, health_input.injury_events * 0.08)
            - traits.injury_proneness * 0.12
            + traits.resilience * 0.14
            + (recovery / 99.0) * 0.08
        )
        return CareerProgressionEngine._clamp_float(value)

    @staticmethod
    def _carryover_fatigue(*, health_input: SeasonHealthInput, traits: HiddenCareerTraits, recovery: int) -> float:
        value = (
            health_input.fatigue_load * 0.6
            + health_input.wear_load * 0.45
            + min(0.25, health_input.injury_events * 0.07)
            + traits.injury_proneness * 0.14
            - traits.resilience * 0.2
            - (recovery / 99.0) * 0.12
        )
        return CareerProgressionEngine._clamp_float(value)

    @staticmethod
    def _should_evolve_style(*, player_rng: DeterministicRng, player: Player, age: int) -> tuple[str, str, bool, str | None]:
        chance = 0.005
        if age <= 21 and player.hidden_career_traits.growth_curve == "late":
            chance += 0.007
        roll = player_rng.random()
        if roll >= chance:
            return player.play_style, player.archetype, False, None

        return (
            player.play_style,
            player.archetype,
            True,
            "MVP placeholder: rare style evolution trigger fired; profile retained until full style evolution model exists.",
        )

    @staticmethod
    def _clamp_float(value: float) -> float:
        return max(0.0, min(1.0, round(value, 4)))

    @staticmethod
    def _clamp_int(minimum: int, maximum: int, value: int) -> int:
        return max(minimum, min(maximum, value))
