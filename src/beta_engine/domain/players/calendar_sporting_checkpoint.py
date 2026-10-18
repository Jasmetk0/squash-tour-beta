"""Calendar-native population checkpoint after a real opening knockout.

Historical v1/v2 retain exact opening-week bytes. Explicit v3 adds an ordered
sporting-only weekly ledger and subsequent exhibitions. It does not own the
Official Week Transition, Health healing or lifecycle. The bootstrap is provisional.
"""
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_canonical_match import (
    CalendarCanonicalMatchSource,
    CalendarCanonicalPlayerSource,
)
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.players.calendar_followup_knockout import CalendarFollowupKnockout
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarSportingWeekAdvance,
)
from beta_engine.domain.players.sporting import (
    PlayerSportingBootstrapPolicy,
    PlayerSportingRecord,
)
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarSportingCheckpoint(FrozenInput):
    schema_version: Literal['calendar_sporting_checkpoint.v1', 'calendar_sporting_checkpoint.v2', 'calendar_sporting_checkpoint.v3', 'calendar_sporting_checkpoint.v4'] = 'calendar_sporting_checkpoint.v1'
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    phase: Literal['opening_week_after_knockout', 'opening_week_continued', 'sporting_week_active'] = 'opening_week_after_knockout'
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_knockout_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    bootstrap_policy: PlayerSportingBootstrapPolicy = PlayerSportingBootstrapPolicy()
    players: tuple[PlayerSportingRecord, ...] = Field(min_length=4)
    annual_development_applied: bool = False
    health_effects_applied: Literal[False] = False

    continuations: tuple[CalendarContinuationMatch, ...] = ()
    week_events: tuple[CalendarSportingWeekAdvance | CalendarContinuationMatch | CalendarFollowupKnockout, ...] = ()

    @model_serializer(mode='wrap')
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version == 'calendar_sporting_checkpoint.v1':
            body.pop('continuations', None)
        if self.schema_version not in {'calendar_sporting_checkpoint.v3', 'calendar_sporting_checkpoint.v4'}:
            body.pop('week_events', None)
        return body

    @model_validator(mode='after')
    def validate_checkpoint(self):
        if self.schema_version == 'calendar_sporting_checkpoint.v1':
            if 'continuations' in self.model_fields_set or self.phase != 'opening_week_after_knockout':
                raise ValueError('Historical checkpoint cannot acquire continuation history')
        elif self.schema_version == 'calendar_sporting_checkpoint.v2' and (not self.continuations or self.phase != 'opening_week_continued'):
            raise ValueError('Continued checkpoint requires actual match history')
        if self.schema_version not in {'calendar_sporting_checkpoint.v3', 'calendar_sporting_checkpoint.v4'}:
            if 'week_events' in self.model_fields_set or self.annual_development_applied:
                raise ValueError('Historical checkpoint cannot acquire weekly development')
        elif (not self.week_events or not isinstance(self.week_events[0], CalendarSportingWeekAdvance)
                or self.phase != 'sporting_week_active' or not self.annual_development_applied):
            raise ValueError('Weekly checkpoint requires an actual ordered sporting advance')
        if (self.schema_version == 'calendar_sporting_checkpoint.v3'
            and any(isinstance(event, CalendarFollowupKnockout) for event in self.week_events)):
            raise ValueError('Historical v3 checkpoint cannot gain a later-week knockout')
        if (self.schema_version == 'calendar_sporting_checkpoint.v4'
            and not any(isinstance(event, CalendarFollowupKnockout) for event in self.week_events)):
            raise ValueError('Checkpoint v4 requires actual later-week knockout evidence')
        ids = tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError('Calendar sporting checkpoint requires the sorted unique population')
        if self.schema_version not in {'calendar_sporting_checkpoint.v3', 'calendar_sporting_checkpoint.v4'} and (self.week.season_index, self.week.week) != (0, 1):
            raise ValueError('Checkpoint v1 does not advance the opening week')
        if self.bootstrap_policy != PlayerSportingBootstrapPolicy():
            raise ValueError('Unknown calendar sporting bootstrap calibration')
        return self

    @property
    def played_continuations(self):
        return self.continuations + tuple(
            match
            for event in self.week_events
            for match in (
                event.matches if isinstance(event, CalendarFollowupKnockout)
                else (event,) if isinstance(event, CalendarContinuationMatch)
                else ()
            )
        )

    @property
    def weekly_advances(self):
        return tuple(e for e in self.week_events if isinstance(e, CalendarSportingWeekAdvance))

    @property
    def tournaments(self):
        return tuple(e for e in self.week_events if isinstance(e, CalendarFollowupKnockout))

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
