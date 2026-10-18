"""Calendar-native population checkpoint after a real opening knockout.

This is persisted world authority, not a weekly-development calculation. The
bootstrap remains the explicit existing provisional adapter. Medical authority
remains in Health; no recovery, ageing or time advancement is implied.
"""
from typing import Literal

from pydantic import Field, model_validator, model_serializer

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import CalendarContinuationMatch
from beta_engine.domain.players.calendar_canonical_match import CalendarCanonicalPlayerSource, CalendarCanonicalMatchSource
from beta_engine.domain.players.sporting import PlayerSportingBootstrapPolicy, PlayerSportingRecord
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarSportingCheckpoint(FrozenInput):
    schema_version: Literal['calendar_sporting_checkpoint.v1', 'calendar_sporting_checkpoint.v2'] = 'calendar_sporting_checkpoint.v1'
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    phase: Literal['opening_week_after_knockout', 'opening_week_continued'] = 'opening_week_after_knockout'
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_knockout_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    bootstrap_policy: PlayerSportingBootstrapPolicy = PlayerSportingBootstrapPolicy()
    players: tuple[PlayerSportingRecord, ...] = Field(min_length=4)
    annual_development_applied: Literal[False] = False
    health_effects_applied: Literal[False] = False

    continuations: tuple[CalendarContinuationMatch, ...] = ()

    @model_serializer(mode='wrap')
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version == 'calendar_sporting_checkpoint.v1':
            body.pop('continuations', None)
        return body

    @model_validator(mode='after')
    def validate_checkpoint(self):
        if self.schema_version == 'calendar_sporting_checkpoint.v1':
            if 'continuations' in self.model_fields_set or self.phase != 'opening_week_after_knockout':
                raise ValueError('Historical checkpoint cannot acquire continuation history')
        elif not self.continuations or self.phase != 'opening_week_continued':
            raise ValueError('Continued checkpoint requires actual match history')
        ids = tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError('Calendar sporting checkpoint requires the sorted unique population')
        if (self.week.season_index, self.week.week) != (0, 1):
            raise ValueError('Checkpoint v1 does not advance the opening week')
        if self.bootstrap_policy != PlayerSportingBootstrapPolicy():
            raise ValueError('Unknown calendar sporting bootstrap calibration')
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def build_calendar_sporting_checkpoint(world, knockout, engine_player):
    """Rebuild every record; only played entrants receive verified match effects.

    The caller supplies a validated knockout. Full equality against this result
    authenticates both the untouched population and the four terminal records.
    """
    if (world.schema_version != 'initial_world_state.v2'
            or knockout.schema_version != 'calendar_opening_knockout.v5'
            or world.fingerprint != knockout.source_initial_world_fingerprint
            or (world.run_id, world.branch_id) != (knockout.run_id, knockout.branch_id)):
        raise ValueError('World sporting checkpoint source identity mismatch')
    original, played = world.run_calendar, knockout.week.calendar
    if ((original.weeks_per_year, original.season_start_year_week, original.start_year)
            != (played.weeks_per_year, played.season_start_year_week, played.start_year)
            or original.season_count > played.season_count):
        raise ValueError('World sporting checkpoint cannot reinterpret the population calendar')

    expected_source = CalendarCanonicalMatchSource.from_population(world, knockout.entrant_ids, engine_player)
    if knockout.canonical_source != expected_source:
        raise ValueError('Played canonical inputs differ from the actual Saved population')
    terminal = {p.player_id: p for p in knockout.sporting.terminal}
    policy = knockout.canonical_source.bootstrap_policy
    records = []
    for profile in sorted(world.players, key=lambda p: p.player_id):
        source = CalendarCanonicalPlayerSource(
            player=engine_player(profile),
            source_generation_fingerprint=profile.source_generation_fingerprint,
            potential_ability=profile.potential_ability,
        )
        record = derive_bootstrap_record(source, policy)
        if source.player_id in terminal:
            state = terminal[source.player_id]
            record = record.model_copy(update={
                'current_form': state.current_form,
                'match_sharpness': state.match_sharpness,
                'long_term_fatigue': state.long_term_fatigue,
            })
        records.append(record)
    if not set(terminal) <= {p.player_id for p in records}:
        raise ValueError('Played terminal state contains a player outside the population')
    return CalendarSportingCheckpoint(
        run_id=knockout.run_id, branch_id=knockout.branch_id, week=knockout.week,
        source_saved_head=knockout.source_saved_head,
        source_initial_world_fingerprint=world.fingerprint,
        source_knockout_fingerprint=knockout.fingerprint,
        bootstrap_policy=policy, players=tuple(records),
    )
