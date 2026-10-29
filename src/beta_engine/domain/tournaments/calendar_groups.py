"""Versioned native adapter to the shared group sporting authorities.

This module owns no second round robin, tie-break or crossing algorithm. Plans
are rebuilt from the frozen Entry/format/topology and actual global-slot results.
"""
from types import SimpleNamespace
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupFormatConfiguration,
    TournamentGroupRulesPolicy,
)
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupMatchScheduleBuilder,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
    TournamentGroupStandingsBuilder,
    TournamentGroupStandingsUnresolvedTie,
    TournamentGroupTieResolutionDecision,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
    TournamentHybridKnockoutBracketBuilder,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsBuilder,
)
from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthority,
    hybrid_phase_point_components,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentTopologyAuthority,
    TournamentTopologyAuthorityBuilder,
)
from beta_engine.domain.tournaments.calendar_group_withdrawals import (
    NativeGroupWalkover, group_resolved_matches, group_withdrawals,
)


class NativeGroupConfiguration(FrozenInput):
    schema_version: Literal['native_group_configuration.v1'] = 'native_group_configuration.v1'
    format_kind: Literal['groups', 'groups_knockout']
    rules: TournamentGroupRulesPolicy
    groups: TournamentGroupFormatConfiguration
    knockout_best_of: Literal[3, 5] = 5
    played_group_win_points: int = Field(ge=0, le=1000000)

    @model_validator(mode='after')
    def validate_rules(self):
        if (self.groups.group_rules_policy_fingerprint != self.rules.fingerprint
            or self.groups.group_rules_effective_from_season_index != self.rules.effective_from_season_index):
            raise ValueError('Group rules source differs from its stored effective policy')
        if self.groups.rules_source_kind == 'season_policy' and self.groups.match_best_of != self.rules.default_match_best_of:
            raise ValueError('Season group format differs from its rules; use an explicit Edition override')
        # The existing authority validates exact, complete, unique crossings.
        TournamentFormatAuthority(
            run_id=self.rules.run_id, branch_id=self.rules.branch_id,
            event_id='configuration-validation', target_season_index=self.rules.effective_from_season_index,
            configured_by_command_id=self.rules.adopted_by_command_id,
            entry_field_fingerprint='0' * 64, format_kind=self.format_kind,
            group_configuration=self.groups,
        )
        return self


def knockout_stages(count):
    return ('champion',) + tuple(
        {2: 'finalist', 4: 'semifinal', 8: 'quarterfinal'}.get(n, f'round_of_{n}')
        for n in (2 ** i for i in range(1, count.bit_length()))
    )


class NativeGroupDraw(FrozenInput):
    schema_version: Literal['native_group_draw.v1'] = 'native_group_draw.v1'
    format: TournamentFormatAuthority
    topology: TournamentTopologyAuthority
    schedule: TournamentGroupMatchScheduleAuthority

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))

    @property
    def main(self):
        # Compatibility read projection only; the topology is the actual draw.
        return SimpleNamespace(slots=self.topology.group_slots)


def build_group_draw(authority, command_id, seed):
    config = authority.edition.group_configuration
    rules = config.rules
    if (rules.run_id, rules.branch_id) != (authority.field.run_id, authority.field.branch_id):
        raise ValueError('Group rules have a foreign Run/Branch owner')
    if rules.effective_from_season_index > authority.edition.week.season_index:
        raise ValueError('Group rules are not effective in the Edition season')
    fmt = TournamentFormatAuthority(
        run_id=authority.field.run_id, branch_id=authority.field.branch_id,
        event_id=authority.edition.edition_id, target_season_index=authority.edition.week.season_index,
        configured_by_command_id=command_id, entry_field_fingerprint=authority.field.fingerprint,
        format_kind=config.format_kind, group_configuration=config.groups,
    )
    topology = TournamentTopologyAuthorityBuilder.build_groups(
        format_authority=fmt, entry_field=authority.field,
        participant_order_player_ids=authority.field.direct_main_player_ids,
        command_id=command_id, topology_seed=seed,
    )
    schedule = TournamentGroupMatchScheduleBuilder.build(
        format_authority=fmt, topology_authority=topology, command_id=command_id,
    )
    return NativeGroupDraw(format=fmt, topology=topology, schedule=schedule)


class NativeGroupTieDecision(FrozenInput):
    edition_id: str
    command_id: str
    operator_label: str = Field(min_length=1)
    decision: TournamentGroupTieResolutionDecision


def group_decisions(slots, edition_id):
    # Forks may reference the same original administrative record in an inherited
    # slot. Keep its original identity, and reject a contradictory second value.
    records = {}
    for slot in slots:
        for record in getattr(slot, 'group_tie_decisions', ()):
            if record.edition_id != edition_id:
                continue
            prior = records.get(record.command_id)
            if prior is not None and prior != record:
                raise ValueError('Group tie decision identity has conflicting evidence')
            records[record.command_id] = record
    return tuple(record.decision for record in records.values())


def group_standings(authority, matches, decisions=()):
    schedule = authority.draw.schedule
    if any(m.match_id not in matches for m in schedule.matches):
        return None
    receipts = tuple(TournamentGroupStandingsBuilder.receipt_from_result(
        scheduled_match=m, result=matches[m.match_id].result,
        result_fingerprint=matches[m.match_id].fingerprint,
        retirement_policy=True,
    ) for m in schedule.matches)
    return TournamentGroupStandingsBuilder.build(
        schedule=schedule, receipts=receipts, command_id='native-group-standings',
        admin_tie_resolutions=decisions, schema_version='tournament_group_standings_authority.v3',
    )


def group_bracket(authority, standings):
    if standings is None or authority.edition.group_configuration.format_kind == 'groups':
        return None
    entrants = TournamentHybridKnockoutEntrantsBuilder.build(
        topology=authority.draw.topology, standings=standings,
        command_id='native-group-advancement',
    )
    return TournamentHybridKnockoutBracketBuilder.build(
        entrants=entrants, command_id='native-hybrid-bracket',
    )


def group_plan(authority, matches, decisions=()):
    """(id, global slot, participants, best of) from existing authorities."""
    if not authority.draw:
        return ()
    schedule = authority.draw.schedule
    config = authority.edition.group_configuration
    result = [(m.match_id, authority.edition.start_slot + 2 + m.match_day_ordinal,
               (m.top_player_id, m.bottom_player_id), m.effective_match_format.format.best_of)
              for m in schedule.matches]
    if any(mid not in matches for mid, *_ in result):
        return tuple(result)
    standings = group_standings(authority, matches, decisions)
    bracket = group_bracket(authority, standings)
    if bracket:
        for m in bracket.matches:
            pids = tuple(s.removeprefix('player:') if s.startswith('player:')
                         else matches[s.removeprefix('winner:')].result.winner_player_id
                         if s.removeprefix('winner:') in matches else None
                         for s in m.participant_sources)
            result.append((m.match_id, authority.edition.start_slot + 2 + schedule.match_day_count + m.round_number,
                           pids, config.knockout_best_of))
    return tuple(result)


def group_progress(authority, slots):
    if not authority.draw:
        return {'standings': None, 'tie_case': None, 'bracket': None}
    matches = group_resolved_matches(slots)
    extra = {}
    withdrawals = tuple(r for r in group_withdrawals(slots) if r.edition_id == authority.edition.edition_id)
    if withdrawals:
        extra['withdrawals'] = [r.model_dump(mode='json') for r in withdrawals]
        extra['walkovers'] = [m.model_dump(mode='json') for m in matches.values()
            if isinstance(m, NativeGroupWalkover) and m.edition_id == authority.edition.edition_id]
    config = authority.edition.group_configuration
    if config.format_kind == 'groups' and not config.played_group_win_points and not authority.tournament_fingerprint:
        blocked_groups = {r.group_index for r in withdrawals}
        eligible = []
        for player in authority.draw.topology.group_slots:
            scheduled = tuple(m for m in authority.draw.schedule.matches if player.player_id in (
                m.top_player_id, m.bottom_player_id))
            if (player.group_index not in blocked_groups and any(m.match_id in matches for m in scheduled)
                and any(m.match_id not in matches for m in scheduled)):
                eligible.append(player.player_id)
        if eligible:
            extra['withdrawal_available_player_ids'] = eligible
    try:
        standings = group_standings(authority, matches, group_decisions(slots, authority.edition.edition_id))
        bracket = group_bracket(authority, standings)
        result = {'standings': standings.model_dump(mode='json') if standings else None,
                  'tie_case': None, 'bracket': bracket.model_dump(mode='json') if bracket else None}
        return {**result, **extra}
    except TournamentGroupStandingsUnresolvedTie as exc:
        return {'standings': None, 'tie_case': exc.case.model_dump(mode='json'), 'bracket': None, **extra}


class NativeGroupPointPolicy(FrozenInput):
    schema_version: Literal['native_group_ranking_policy.v1'] = 'native_group_ranking_policy.v1'
    played_group_win_points: int = Field(ge=0)
    knockout_stage_points: tuple[tuple[str, int], ...] = ()
    validity_weeks: int = Field(ge=1)

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def group_point_policy(authority):
    config = authority.edition.group_configuration
    table = tuple(sorted(authority.edition.point_table.items()))
    if config.format_kind == 'groups_knockout':
        # Reuse the shared explicit hybrid policy, including its composition ID.
        TournamentHybridRankingPolicyAuthority(
            run_id=config.rules.run_id, branch_id=config.rules.branch_id,
            event_id=authority.edition.edition_id, configured_by_command_id=authority.created_command_id,
            played_group_win_points=config.played_group_win_points, knockout_stage_points=table,
        )
    return NativeGroupPointPolicy(played_group_win_points=config.played_group_win_points,
                                 knockout_stage_points=table, validity_weeks=authority.edition.validity_weeks)


class NativeGroupAward(FrozenInput):
    player_id: str
    reached_stage: str
    main_points: int = Field(ge=0)
    group_points: int = Field(ge=0)
    knockout_points: int = Field(ge=0)
    source_policy_fingerprint: str


class NativeGroupTournamentResult(FrozenInput):
    schema_version: Literal['calendar_group_tournament_result.v1', 'calendar_group_tournament_result.v2'] = 'calendar_group_tournament_result.v1'
    run_id: str
    branch_id: str
    tournament_id: str
    command_id: str
    source_saved_head: str
    source_checkpoint_fingerprint: str
    week: RunWeekPosition
    seed: int
    entrant_ids: tuple[str, ...]
    matches: tuple[CalendarContinuationMatch, ...]
    walkovers: tuple[NativeGroupWalkover, ...] = Field(default=(), exclude_if=lambda value: not value)
    edition_authority_fingerprint: str
    prepared_policy: NativeGroupPointPolicy
    prepared_awards: tuple[NativeGroupAward, ...]
    standings: TournamentGroupStandingsAuthority
    knockout_bracket: TournamentHybridKnockoutBracketAuthority | None
    winner_player_id: str | None
    scope: Literal['configured_tour_groups'] = 'configured_tour_groups'

    @model_validator(mode='after')
    def versioned_nonplayed(self):
        if self.walkovers and self.schema_version != 'calendar_group_tournament_result.v2':
            raise ValueError('Historical group result cannot acquire nonplayed matches')
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))

    @property
    def sporting_fingerprint(self):
        body = self.model_dump(mode='json')
        body.pop('prepared_awards')
        return canonical_hash(body)


def completed_group_result(authority, slots, *, owner=None):
    eid = authority.edition.edition_id
    accepted = group_resolved_matches(slots)
    decisions = group_decisions(slots, eid)
    try:
        plan = group_plan(authority, accepted, decisions)
        if not plan or any(mid not in accepted for mid, *_ in plan):
            return None
        standings = group_standings(authority, accepted, decisions)
    except TournamentGroupStandingsUnresolvedTie:
        return None
    if standings is None:
        return None
    bracket = group_bracket(authority, standings)
    stages = {}
    if bracket:
        for m in bracket.matches:
            result = accepted[m.match_id].result
            stages[result.loser_player_id] = knockout_stages(bracket.entrant_count)[bracket.round_count - m.round_number + 1]
        stages[accepted[bracket.terminal_match_id].result.winner_player_id] = 'champion'
    policy = group_point_policy(authority)
    awards = []
    for group in standings.groups:
        for row in group.rows:
            if policy.played_group_win_points and row.walkovers_received:
                raise ValueError('Group W/O Official Ranking reward requires an explicit decided policy')
            played_wins = sum(r.result_kind in {'played', 'retirement'} and r.winner_player_id == row.player_id for r in standings.source_results)
            stage = stages.get(row.player_id, f'group_position_{row.position}')
            components = hybrid_phase_point_components(policy=policy, played_group_wins=played_wins,
                knockout_reached_stage=stages.get(row.player_id))
            group_points = components[0].points_awarded
            knockout_points = components[1].points_awarded if len(components) == 2 else 0
            if bracket is None and len(standings.groups) == 1:
                stage = {1: 'champion', 2: 'finalist'}.get(row.position, stage)
            awards.append(NativeGroupAward(player_id=row.player_id, reached_stage=stage,
                main_points=group_points + knockout_points,
                group_points=group_points, knockout_points=knockout_points,
                source_policy_fingerprint=policy.fingerprint))
    first = next(slot for slot in slots if any(s.edition_id == eid for s in slot.scheduled))
    source = next(s.source_saved_head for s in first.scheduled if s.edition_id == eid)
    winner = (accepted[bracket.terminal_match_id].result.winner_player_id if bracket else
              standings.groups[0].rows[0].player_id if len(standings.groups) == 1 else None)
    walkovers = tuple(accepted[mid] for mid, *_ in plan if isinstance(accepted[mid], NativeGroupWalkover))
    return NativeGroupTournamentResult(
        schema_version='calendar_group_tournament_result.v2' if walkovers else 'calendar_group_tournament_result.v1',
        run_id=first.run_id, branch_id=owner or first.branch_id,
        tournament_id=eid, command_id='global-tournament:' + authority.execution_fingerprint,
        source_saved_head=source, source_checkpoint_fingerprint=first.source_checkpoint_fingerprint,
        week=first.week, seed=authority.edition.simulation_seed,
        entrant_ids=tuple(s.player_id for s in authority.draw.topology.group_slots),
        matches=tuple(accepted[mid] for mid, *_ in plan if not isinstance(accepted[mid], NativeGroupWalkover)),
        walkovers=walkovers,
        edition_authority_fingerprint=authority.execution_fingerprint,
        prepared_policy=policy, prepared_awards=tuple(sorted(awards, key=lambda a: a.player_id)),
        standings=standings, knockout_bracket=bracket, winner_player_id=winner,
    )
