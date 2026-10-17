"""Owned 57-attribute knockout input using the existing explicit provisional adapter.

The source is current Saved population facts, not invented historical development.
No legacy RankingWeek or world-week sporting row is manufactured here.
"""
from typing import Literal
from pydantic import Field, model_validator
from beta_engine.domain.matches.models import MatchParticipantContext
from beta_engine.domain.players.models import Player
from beta_engine.domain.players.sporting import PlayerSportingRecord, PlayerSportingBootstrapPolicy
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.players.calendar_match_state import checkpoint_fingerprint
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy, project_player, projected_engine_player,
)


class CalendarCanonicalPlayerSource(FrozenInput):
    player: Player
    source_generation_fingerprint: str = Field(min_length=1)
    potential_ability: int = Field(ge=0, le=99)

    @property
    def player_id(self): return self.player.player_id
    @property
    def attributes(self): return self.player
    @property
    def hidden_career_traits(self): return self.player.hidden_career_traits


class CalendarCanonicalMatchSource(FrozenInput):
    schema_version: Literal['calendar_canonical_match_source.v1'] = 'calendar_canonical_match_source.v1'
    source_initial_world_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    bootstrap_policy: PlayerSportingBootstrapPolicy = PlayerSportingBootstrapPolicy()
    projection_policy: CanonicalMatchInputProjectionPolicy = CanonicalMatchInputProjectionPolicy()
    players: tuple[CalendarCanonicalPlayerSource, ...] = Field(min_length=4, max_length=4)
    records: tuple[PlayerSportingRecord, ...] = Field(min_length=4, max_length=4)
    annual_development_applied: Literal[False] = False

    @model_validator(mode='after')
    def verify_source(self):
        ids=tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError('Canonical match source requires four sorted distinct players')
        if (self.bootstrap_policy != PlayerSportingBootstrapPolicy()
                or self.projection_policy != CanonicalMatchInputProjectionPolicy()):
            raise ValueError('Unknown canonical match adapter calibration version')
        expected=tuple(derive_bootstrap_record(p,self.bootstrap_policy) for p in self.players)
        if self.records != expected:
            raise ValueError('Canonical 57 records do not derive from frozen source facts/policy')
        return self

    @classmethod
    def from_population(cls, world, entrant_ids, engine_player):
        roster={p.player_id:p for p in world.players}
        if len(set(entrant_ids)) != 4 or not set(entrant_ids) <= set(roster):
            raise ValueError('Canonical source entrants differ from Saved population')
        players=tuple(CalendarCanonicalPlayerSource(
            player=engine_player(roster[pid]),
            source_generation_fingerprint=roster[pid].source_generation_fingerprint,
            potential_ability=roster[pid].potential_ability,
        ) for pid in sorted(entrant_ids))
        policy=PlayerSportingBootstrapPolicy()
        return cls(source_initial_world_fingerprint=world.fingerprint, players=players,
                   bootstrap_policy=policy, records=tuple(derive_bootstrap_record(p,policy) for p in players))

    @property
    def fingerprint(self): return canonical_hash(self.model_dump(mode='json'))

    def project(self, player_id, states):
        source=next(p for p in self.players if p.player_id == player_id)
        record=next(p for p in self.records if p.player_id == player_id)
        state=next(p for p in states if p.player_id == player_id)
        record=record.model_copy(update=dict(current_form=state.current_form,
            match_sharpness=state.match_sharpness,long_term_fatigue=state.long_term_fatigue))
        return project_player(record,
            source_sporting_fingerprint=canonical_hash({'canonical_source': self.fingerprint,
                'checkpoint': checkpoint_fingerprint(states)}),
            policy=self.projection_policy, profile_source_fingerprint=source.source_generation_fingerprint,
            profile_provenance='Saved population; explicit provisional 7-to-57 bootstrap; no annual development',
            age=source.player.age,name=source.player.name,nationality=source.player.nationality,
            play_style=source.player.play_style,archetype=source.player.archetype,
            hidden_career_traits=source.player.hidden_career_traits)


def canonical_participant(projection):
    return MatchParticipantContext(player=projected_engine_player(projection),
        form_modifier=projection.form_modifier,sharpness_modifier=projection.sharpness_modifier,
        fatigue_modifier=projection.fatigue_modifier)
