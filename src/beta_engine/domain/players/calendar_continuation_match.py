"""Sequential exhibitions consuming actual owned sporting records.

No implicit recovery, development, ranking award or Week Transition. Each event
reads one frozen population checkpoint, then applies existing match effects.
"""
from types import SimpleNamespace
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot
from beta_engine.domain.matches.models import MatchContext, MatchResult
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchEffect,
    CalendarMatchPlayerState,
    CalendarMatchStatePolicy,
    advance_played_slot,
)
from beta_engine.domain.players.calendar_sporting_week import age_in_run_years
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    CanonicalPlayerMatchProjection,
    project_player,
)


class CalendarContinuationMatch(FrozenInput):
    schema_version: Literal['calendar_continuation_match.v1', 'calendar_continuation_match.v2', 'calendar_continuation_match.v3'] = 'calendar_continuation_match.v1'
    run_id: str
    branch_id: str
    week: RunWeekPosition
    sequence: int = Field(ge=1)
    command_id: str = Field(min_length=1, max_length=128)
    match_id: str = Field(min_length=1, max_length=100)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    request_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    input_context: MatchContext
    result: MatchResult
    canonical_projections: tuple[CanonicalPlayerMatchProjection, CanonicalPlayerMatchProjection]
    projection_policy: CanonicalMatchInputProjectionPolicy = CanonicalMatchInputProjectionPolicy()
    state_policy: CalendarMatchStatePolicy = CalendarMatchStatePolicy()
    source_health_fingerprint: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    effective_health: EffectiveMatchHealthSnapshot | None = None
    effects: tuple[CalendarMatchEffect, CalendarMatchEffect]
    log_anchor_hash: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def validate_evidence(self):
        ctx, result = self.input_context, self.result
        ids = (ctx.player_a.player.player_id, ctx.player_b.player.player_id)
        if (self.schema_version == 'calendar_continuation_match.v1' and self.week.ordinal != 0) or len(set(ids)) != 2:
            raise ValueError('Continuation needs distinct players and a schema-compatible sporting week')
        if (ctx.match_id != self.match_id or result.match_id != self.match_id
                or (result.player_a_id, result.player_b_id) != ids
                or {result.winner_player_id, result.loser_player_id} != set(ids)
                or (ctx.best_of not in ((3, 5) if self.schema_version == 'calendar_continuation_match.v3' else (5,)) or (ctx.games_to, ctx.win_by) != (11, 2))):
            raise ValueError('Continuation result/context identity or match rules mismatch')
        if (self.projection_policy != CanonicalMatchInputProjectionPolicy()
                or self.state_policy != CalendarMatchStatePolicy()):
            raise ValueError('Unknown continuation projection/effect calibration')
        if tuple(p.player_id for p in self.canonical_projections) != ids or (
                ctx.player_a, ctx.player_b) != tuple(canonical_participant(p) for p in self.canonical_projections):
            raise ValueError('Continuation does not consume its canonical projections')
        if bool(self.source_health_fingerprint) != (self.effective_health is not None):
            raise ValueError('Continuation Health source and input must be paired')
        if self.effective_health and tuple(p.player_id for p in self.effective_health.player_profiles) != ids:
            raise ValueError('Continuation Health participant order mismatch')
        if not result.rally_log or not result.rally_log.events or result.timeline_log is None or result.stamina_log is None:
            raise ValueError('Continuation requires complete actual MatchEngine logs')
        if (self.log_anchor_hash != continuation_anchor(self)
                or result.rally_log.input_snapshot_hash != self.log_anchor_hash):
            raise ValueError('Continuation source/input is detached from played rally log')
        command = dict(command_id=self.command_id, match_id=self.match_id,
            expected_saved_head=self.source_saved_head,
            expected_checkpoint_fingerprint=self.source_checkpoint_fingerprint,
            player_a_id=ids[0], player_b_id=ids[1], seed=self.seed,
            operator_label=self.operator_label, audit_reason=self.audit_reason)
        if self.request_fingerprint != canonical_hash({'run_id': self.run_id, 'branch_id': self.branch_id, 'command': command}):
            raise ValueError('Continuation command fingerprint mismatch')
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def continuation_anchor(value):
    return canonical_hash({
        'schema_version': ('calendar_continuation_match_anchor.v1' if getattr(value, 'schema_version', 'calendar_continuation_match.v1') == 'calendar_continuation_match.v1' else 'calendar_continuation_match_anchor.v2'),
        'run_id': value.run_id, 'branch_id': value.branch_id,
        'week': value.week.model_dump(mode='json'), 'sequence': value.sequence,
        'request_fingerprint': value.request_fingerprint,
        'source_saved_head': value.source_saved_head,
        'source_checkpoint_fingerprint': value.source_checkpoint_fingerprint,
        'context': value.input_context.model_dump(mode='json'), 'seed': value.seed,
        'canonical_projections': [p.model_dump(mode='json') for p in value.canonical_projections],
        'projection_policy': value.projection_policy.model_dump(mode='json'),
        'state_policy': value.state_policy.model_dump(mode='json'),
        'source_health_fingerprint': value.source_health_fingerprint,
        'effective_health': value.effective_health.model_dump(mode='json') if value.effective_health else None,
    })


def continuation_projections(checkpoint, world, ids, policy=None, *, source_fingerprint=None):
    policy = policy or CanonicalMatchInputProjectionPolicy()
    records = {p.player_id: p for p in checkpoint.players}
    profiles = {p.player_id: p for p in world.players}
    if len(set(ids)) != 2 or not set(ids) <= records.keys() or not set(ids) <= profiles.keys():
        raise ValueError('Continuation players must belong to the owned population')
    fp = source_fingerprint if source_fingerprint is not None else checkpoint.fingerprint
    return tuple(project_player(records[pid], source_sporting_fingerprint=fp, policy=policy,
        profile_source_fingerprint=profiles[pid].source_generation_fingerprint,
        profile_provenance=('Saved native population sporting checkpoint; no recovery or annual development' if checkpoint.week.ordinal == 0 else 'Saved native sporting-week checkpoint; provisional annual development and weekly recovery'),
        age=(profiles[pid].age_years_at_season_start if checkpoint.week.ordinal == 0 else int(age_in_run_years(profiles[pid], checkpoint.week))), name=profiles[pid].name,
        nationality=profiles[pid].nationality, play_style=profiles[pid].play_style,
        archetype=profiles[pid].archetype, hidden_career_traits=profiles[pid].hidden_career_traits) for pid in ids)


def continuation_states(checkpoint, ids):
    return tuple(CalendarMatchPlayerState(player_id=p.player_id,
        current_form=p.current_form, match_sharpness=p.match_sharpness,
        long_term_fatigue=p.long_term_fatigue) for p in checkpoint.players if p.player_id in ids)


def continuation_effects(checkpoint, context, result, policy):
    ids = (context.player_a.player.player_id, context.player_b.player.player_id)
    return advance_played_slot(continuation_states(checkpoint, ids),
        (SimpleNamespace(input_context=context, result=result),), policy)


def append_continuation(checkpoint, world, entry, *, _defer_checkpoint_validation=False):
    """Rebuild exact successor, preserving every unaffected player record.

    The only batching caller is append_followup_knockout: every actual match
    still authenticates its frozen predecessor hash, projection and effects;
    that caller validates the *complete* tournament checkpoint once at the end.
    Ordinary standalone replay continues strict validation per match.
    """
    from beta_engine.domain.players.calendar_sporting_checkpoint import (
        CalendarSportingCheckpoint,
    )
    prior = checkpoint.played_continuations
    previous_clock = checkpoint.week.calendar if checkpoint.week_events else (prior[-1].week.calendar if prior else checkpoint.week.calendar)
    current = entry.week.calendar
    predecessor_fingerprint = checkpoint.fingerprint
    if ((entry.run_id, entry.branch_id) != (checkpoint.run_id, checkpoint.branch_id)
            or entry.sequence != len(prior) + 1 or entry.source_checkpoint_fingerprint != predecessor_fingerprint
            or any(e.command_id == entry.command_id or e.match_id == entry.match_id for e in prior)
            or any(e.command_id == entry.command_id for e in checkpoint.weekly_advances)
            or any(e.command_id == entry.command_id for e in checkpoint.tournaments)
            or any(e.command_id == entry.command_id for e in checkpoint.closures)
            or entry.week.ordinal != checkpoint.week.ordinal
            or (checkpoint.week_events and entry.schema_version != 'calendar_continuation_match.v2')
            or (not checkpoint.week_events and entry.schema_version != 'calendar_continuation_match.v1')
            or (current.weeks_per_year, current.season_start_year_week, current.start_year)
                != (previous_clock.weeks_per_year, previous_clock.season_start_year_week, previous_clock.start_year)
            or current.season_count < previous_clock.season_count):
        raise ValueError('Continuation predecessor, identity, order or calendar changed')
    ids = (entry.input_context.player_a.player.player_id, entry.input_context.player_b.player.player_id)
    if entry.canonical_projections != continuation_projections(checkpoint, world, ids, entry.projection_policy, source_fingerprint=predecessor_fingerprint):
        raise ValueError('Continuation projection does not consume its actual preceding 57-attribute checkpoint')
    terminal, effects = continuation_effects(checkpoint, entry.input_context, entry.result, entry.state_policy)
    if entry.effects != effects:
        raise ValueError('Continuation effects do not rebuild from actual match evidence')
    by_id = {s.player_id: s for s in terminal}
    players = tuple(p.model_copy(update={
        'current_form': by_id[p.player_id].current_form,
        'match_sharpness': by_id[p.player_id].match_sharpness,
        'long_term_fatigue': by_id[p.player_id].long_term_fatigue,
    }) if p.player_id in by_id else p for p in checkpoint.players)
    if checkpoint.week_events:
        successor = checkpoint.model_copy(update={
            'players': players, 'week': entry.week, 'week_events': checkpoint.week_events + (entry,),
        })
    else:
        successor = checkpoint.model_copy(update={
            'schema_version': 'calendar_sporting_checkpoint.v2', 'phase': 'opening_week_continued',
            'players': players, 'continuations': prior + (entry,),
        })
    if _defer_checkpoint_validation:
        # Only the seven-match tournament reducer opts in, and it must strictly
        # validate its terminal v4/v6/v7/v8 checkpoint before any write or Save.
        return successor
    return CalendarSportingCheckpoint.model_validate_json(successor.model_dump_json())
