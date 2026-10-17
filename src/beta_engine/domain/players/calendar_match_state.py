"""Operation-owned calendar knockout checkpoints from real played evidence.

This version adopts the existing provisional match-effect calibration. It does
not invent annual development, Health changes, between-round recovery or Tour
entry. Population attributes remain the explicit seven-value compatibility input.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.matches.models import MatchParticipantContext
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy, MatchSportingEffectsPolicy,
    derive_match_effect_values,
)


class CalendarMatchPlayerState(FrozenInput):
    player_id: str = Field(min_length=1)
    current_form: int = Field(ge=0, le=200)
    match_sharpness: int = Field(ge=0, le=100)
    long_term_fatigue: int = Field(ge=0, le=100)


class CalendarMatchStatePolicy(FrozenInput):
    policy_id: Literal['calendar-knockout-state.provisional.v1'] = 'calendar-knockout-state.provisional.v1'
    initial_form: Literal[100] = 100
    initial_sharpness: Literal[100] = 100
    initial_fatigue: Literal[0] = 0
    projection: CanonicalMatchInputProjectionPolicy = CanonicalMatchInputProjectionPolicy()
    effects: MatchSportingEffectsPolicy = MatchSportingEffectsPolicy()
    provenance: str = 'Explicit fresh operation baseline; provisional calibration; no prestart history, annual development or Health effects'

    @model_validator(mode='after')
    def known_calibration(self):
        if (self.projection != CanonicalMatchInputProjectionPolicy()
                or self.effects != MatchSportingEffectsPolicy()):
            raise ValueError('Unknown calibration for calendar knockout state policy v1')
        return self

    def initial_states(self, entrant_ids):
        return tuple(CalendarMatchPlayerState(
            player_id=pid, current_form=self.initial_form,
            match_sharpness=self.initial_sharpness, long_term_fatigue=self.initial_fatigue,
        ) for pid in sorted(entrant_ids))


def participant_with_state(player, state, policy):
    p = policy.projection
    return MatchParticipantContext(
        player=player,
        form_modifier=round((state.current_form - 100) / p.form_modifier_divisor, 6),
        sharpness_modifier=round((state.match_sharpness - 50) / p.sharpness_modifier_divisor, 6),
        fatigue_modifier=round(-state.long_term_fatigue / p.fatigue_modifier_divisor, 6),
    )


class _EffectInput(FrozenInput):
    player_id: str
    legacy_engine_values: tuple[tuple[str, int], ...]
    current_form: int
    match_sharpness: int
    long_term_fatigue: int
    form_modifier: float
    sharpness_modifier: float
    fatigue_modifier: float


class CalendarMatchEffect(FrozenInput):
    match_id: str
    player_id: str
    input_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    result_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_checkpoint_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    form_before: int
    form_delta: int
    form_after: int
    sharpness_before: int
    sharpness_delta: int
    sharpness_after: int
    fatigue_before: int
    fatigue_delta: int
    fatigue_after: int


def checkpoint_fingerprint(states):
    return canonical_hash([s.model_dump(mode='json') for s in states])


def advance_played_slot(states, matches, policy):
    """All matches read one frozen input; install effects only after the slot.

    Sorting output and rejecting duplicate participants makes accumulation
    independent of execution order. No recovery happens implicitly between slots.
    """
    roster = {s.player_id: s for s in states}
    updated = dict(roster)
    effects = []
    touched = set()
    for match in matches:
        projections = []
        for ctx in (match.input_context.player_a, match.input_context.player_b):
            pid = ctx.player.player_id
            if pid in touched or pid not in roster:
                raise ValueError('Calendar slot repeats or invents a participant')
            touched.add(pid)
            state = roster[pid]
            if ctx != participant_with_state(ctx.player, state, policy):
                raise ValueError('Calendar match input does not consume its frozen checkpoint')
            projections.append(_EffectInput(
                **state.model_dump(),
                legacy_engine_values=tuple((name, getattr(ctx.player, name)) for name in (
                    'technique', 'movement', 'physical', 'mental', 'consistency', 'clutch', 'recovery',
                )),
                form_modifier=ctx.form_modifier, sharpness_modifier=ctx.sharpness_modifier,
                fatigue_modifier=ctx.fatigue_modifier,
            ))
        for values in derive_match_effect_values(projections, match.result, policy=policy.effects):
            pid = values['player_id']
            effects.append(CalendarMatchEffect(
                **values, match_id=match.input_context.match_id,
                input_fingerprint=canonical_hash(match.input_context.model_dump(mode='json')),
                result_fingerprint=canonical_hash(match.result.model_dump(mode='json')),
                source_checkpoint_fingerprint=checkpoint_fingerprint(states),
            ))
            updated[pid] = CalendarMatchPlayerState(
                player_id=pid, current_form=values['form_after'],
                match_sharpness=values['sharpness_after'], long_term_fatigue=values['fatigue_after'],
            )
    return (tuple(updated[pid] for pid in sorted(updated)),
            tuple(sorted(effects, key=lambda e: (e.match_id, e.player_id))))


class CalendarKnockoutSportingState(FrozenInput):
    schema_version: Literal['calendar_knockout_sporting.v1'] = 'calendar_knockout_sporting.v1'
    policy: CalendarMatchStatePolicy
    initial: tuple[CalendarMatchPlayerState, ...] = Field(min_length=4, max_length=4)
    after_semifinals: tuple[CalendarMatchPlayerState, ...] = Field(min_length=4, max_length=4)
    terminal: tuple[CalendarMatchPlayerState, ...] = Field(min_length=4, max_length=4)
    effects: tuple[CalendarMatchEffect, ...] = Field(min_length=6, max_length=6)
    health_effects_applied: Literal[False] = False
    annual_development_applied: Literal[False] = False

    @model_validator(mode='after')
    def canonical_roster(self):
        ids = tuple(p.player_id for p in self.initial)
        if ids != tuple(sorted(set(ids))):
            raise ValueError('Calendar checkpoints require a sorted unique roster')
        if any(tuple(p.player_id for p in stage) != ids for stage in (self.after_semifinals, self.terminal)):
            raise ValueError('Calendar checkpoint roster changes within knockout')
        if self.initial != self.policy.initial_states(ids):
            raise ValueError('Calendar initial checkpoint differs from owned baseline policy')
        return self

    def verify_matches(self, matches):
        semis, effects = advance_played_slot(self.initial, matches[:2], self.policy)
        terminal, final_effects = advance_played_slot(semis, matches[2:], self.policy)
        if (semis, terminal, effects + final_effects) != (
            self.after_semifinals, self.terminal, self.effects,
        ):
            raise ValueError('Calendar sporting checkpoints/effects do not rebuild from played evidence')
