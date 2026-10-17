"""Frozen Saved Health facts consumed by one calendar knockout.

Limitation arithmetic and medical start/retirement decisions remain unsupported;
this contract cannot claim an injured player is numerically treated as healthy.
"""
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot, PlayerMatchHealthProjection, project_player_health,
)
from beta_engine.domain.rankings.official import FrozenInput


class CalendarKnockoutHealthSource(FrozenInput):
    schema_version: Literal['calendar_knockout_health_source.v1'] = 'calendar_knockout_health_source.v1'
    source_health_schema: Literal['calendar_initial_health_state.v1', 'player_health_calendar_state.v2']
    source_health_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_week: RunWeekPosition
    profiles: tuple[PlayerMatchHealthProjection, ...] = Field(min_length=4, max_length=4)
    numeric_effect_applied: Literal[False] = False

    @model_validator(mode='after')
    def valid_source(self):
        ids = tuple(p.player_id for p in self.profiles)
        if ids != tuple(sorted(set(ids))) or self.source_week.ordinal != 0:
            raise ValueError('Knockout Health requires four canonical opening-week participants')
        return self

    @classmethod
    def from_state(cls, state, entrant_ids):
        roster = {p.player_id: p for p in state.players}
        if len(set(entrant_ids)) != 4 or not set(entrant_ids) <= set(roster):
            raise ValueError('Health source does not contain knockout entrants')
        return cls(
            source_health_schema=state.schema_version,
            source_health_fingerprint=state.fingerprint, source_week=state.week,
            profiles=tuple(project_player_health(roster[pid]) for pid in sorted(entrant_ids)),
        )

    def for_players(self, first_id, second_id):
        profiles = {p.player_id: p for p in self.profiles}
        return EffectiveMatchHealthSnapshot(player_profiles=(profiles[first_id], profiles[second_id]))


def calendar_knockout_match_anchor(*, run_id, branch_id, clock, saved_head,
        world_fingerprint, pre_slot_anchor, round_name, slot, context, seed, effective_health=None, canonical_projections=None):
    """Historical neutral anchor stays byte-stable; Health input has a new version."""
    from beta_engine.domain.run_packages import canonical_hash
    body = {
        'schema_version': ('calendar_opening_knockout_match_anchor.v3' if canonical_projections
                           else 'calendar_opening_knockout_match_anchor.v2' if effective_health
                           else 'calendar_opening_knockout_match_anchor.v1'),
        'run_id': run_id, 'branch_id': branch_id,
        'calendar': clock.to_metadata(), 'week': [0, 1],
        'saved_head': saved_head, 'world_fingerprint': world_fingerprint,
        'pre_slot_anchor': pre_slot_anchor, 'round': round_name, 'slot': slot,
        'context': context.model_dump(mode='json'), 'seed': seed,
    }
    if effective_health is not None:
        body['effective_health'] = effective_health.model_dump(mode='json')
    if canonical_projections is not None:
        body['canonical_projections'] = [p.model_dump(mode='json') for p in canonical_projections]
    return canonical_hash(body)
