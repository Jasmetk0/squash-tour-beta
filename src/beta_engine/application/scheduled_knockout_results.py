"""Derive completed scheduled results and Run-calendar ranking inputs.

No second ledger, publication, transition or Save is performed. Callers must
authenticate the plan and accepted records through their existing owners.
"""
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.application.canonical_tournament_points import build_knockout_player_point_awards
from beta_engine.application.native_canonical_ranked_awards import _scoreline
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import CalendarRankingWeek, CalendarRankingResult
from beta_engine.domain.rankings.points import knockout_loss_point_stage
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.result_authority import KnockoutResultFacts, TournamentMatchResultAuthority, assemble_knockout_result_facts
from beta_engine.domain.tournaments.scheduled_knockout_feeders import ScheduledKnockoutFeederPlan, scheduled_knockout_progress
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition


class ScheduledKnockoutResult(KnockoutResultFacts):
    schema_version: Literal['scheduled_knockout_result.v1'] = 'scheduled_knockout_result.v1'
    run_id: str
    branch_id: str
    event_id: str
    completed_week: RunWeekPosition
    source_plan_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def validate_identities(self):
        ids={p.player_id for p in self.players}
        if (len(ids)!=len(self.players) or self.champion_player_id==self.finalist_player_id
                or not {self.champion_player_id,self.finalist_player_id} <= ids
                or len(set(self.qualification_winner_ids))!=len(self.qualification_winner_ids)
                or not set(self.qualification_winner_ids) <= ids
                or not self.matches or len({m.match_id for m in self.matches})!=len(self.matches)):
            raise ValueError('Invalid scheduled result identities')
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def complete_scheduled_knockout_result(*, plan, matches, positions, runtime_calendar: RunCalendar | None=None):
    plan=ScheduledKnockoutFeederPlan.model_validate_json(plan.model_dump_json())
    clock=runtime_calendar or plan.calendar
    plan.schedule.validate_runtime_calendar(clock)
    final=plan.schedule.main[-1]
    current=KnockoutRoundPosition(week=RunWeekPosition(calendar=clock,
        season_index=final.week.season_index,week=final.week.week),slot=final.slot)
    progress,_due=scheduled_knockout_progress(plan=plan,matches=matches,positions=positions,current=current)
    if not progress.champion_player_id or progress.ready_matches or len(progress.accepted_match_ids)!=len(plan.topology.plans):
        raise ValueError('Scheduled result requires every executable knockout match completed')
    accepted={m.match_id:m for m in matches}
    byes=dict(progress.bye_advances)
    rows=[]
    for bracket in (*plan.draw.qualification_brackets,plan.draw.main):
        for node in bracket.nodes:
            record=accepted.get(node.node_id)
            winner=record.result.winner_player_id if record else byes[node.node_id]
            rows.append(TournamentMatchResultAuthority(match_id=node.node_id,draw_type=bracket.draw_type,
                round_number=node.round_number,bracket_position=node.round_sequence,
                winner_player_id=winner,loser_player_id=record.result.loser_player_id if record else None,
                scoreline=_scoreline(record.result) if record else 'BYE',
                result_fingerprint=record.fingerprint if record else canonical_hash({
                    'schema_version':'scheduled_knockout_bye_result.v1','source_plan':plan.fingerprint,
                    'match':node.node_id,'winner':winner})))
    facts=assemble_knockout_result_facts(draw=plan.draw,matches=tuple(rows))
    return ScheduledKnockoutResult(**facts.model_dump(),run_id=plan.draw.run_id,branch_id=plan.draw.branch_id,
        event_id=plan.draw.event_id,completed_week=accepted[plan.topology.terminal_group_id].week,source_plan_fingerprint=plan.fingerprint)


def scheduled_point_distribution(profile):
    """Translate exact physical Q-round labels to shared sporting stage keys."""
    sections=profile.geometry()['qualification_sections']
    rounds=sections[0]['bracket_capacity'].bit_length()-1
    table={**profile.main_points,'qualification_winner':profile.qualification_points['qualifier']}
    for n in range(1,rounds+1):
        stage=knockout_loss_point_stage(draw_type='qualification',round_number=n,final_round=rounds)
        points=profile.qualification_points[f'round_{n}_loss']
        if stage in table and table[stage]!=points:
            raise ValueError('Distinct Qualification awards cannot collapse into one shared stage')
        table[stage]=points
    return table


def scheduled_knockout_ranking_results(*, plan, matches, positions, runtime_calendar: RunCalendar | None=None):
    plan=ScheduledKnockoutFeederPlan.model_validate_json(plan.model_dump_json())
    clock=runtime_calendar or plan.calendar
    result=complete_scheduled_knockout_result(plan=plan,matches=matches,positions=positions,runtime_calendar=clock)
    # The result is valid at the terminal horizon, but this publication adapter
    # requires a next week. It must not invent an out-of-horizon ranking date.
    if result.completed_week.ordinal+1 >= clock.weeks_per_year*clock.season_count:
        raise ValueError('Scheduled ranking projection requires a following publication week')
    publication=clock.position_at_ordinal(result.completed_week.ordinal+1)
    table=scheduled_point_distribution(plan.profile)
    awards=build_knockout_player_point_awards(result=result,point_authority=FrozenPointAwardAuthority(
        ranking_status='ranked',point_distribution=table,point_distribution_source='saved_atp_knockout_profile.v1'),
        seed=plan.draw_input.draw_seed)
    rows=[]
    for award in awards:
        qualification=(award.ranking_points_awarded if award.reached_stage.startswith('qualification_') else award.qualification_points_awarded or 0)
        rows.append(CalendarRankingResult(edition_id=result.event_id,player_id=award.player_id,
            source_fingerprint=canonical_hash({'result':result.fingerprint,'award':award.award_fingerprint}),
            completed_week=CalendarRankingWeek(season_index=result.completed_week.season_index,week=result.completed_week.week),
            first_publication_week=CalendarRankingWeek(season_index=publication.season_index,week=publication.season_week),
            qualification_points=qualification,main_points=award.ranking_points_awarded-qualification,
            validity_weeks=plan.calendar.weeks_per_year))
    return result,tuple(rows)
