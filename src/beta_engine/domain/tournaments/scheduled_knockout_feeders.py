"""Scheduled Q/Main readiness from existing accepted match records.

Source/Saved authentication, Entry, week transitions, frozen slot snapshots and
publication remain the caller's authority. This stateless consumer owns no
second result ledger, invokes no implicit transitions and never auto-Saves.
"""
import json
from typing import Literal, Mapping

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.canonical_knockout_feeders import _project_draw_progress
from beta_engine.domain.tournaments.canonical_knockout_topology import project_canonical_draw_nodes
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority, TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition, KnockoutRunSchedule, plan_knockout_run_matches


class ScheduledKnockoutFeederPlan(FrozenInput):
    schema_version: Literal['scheduled_knockout_feeder_plan.v1'] = 'scheduled_knockout_feeder_plan.v1'
    source_saved_revision_id: str = Field(min_length=1)
    source_saved_content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_profile_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    profile_payload_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    profile: ATPKnockoutProfile
    draw_input: TournamentDrawInputAuthority
    draw: TournamentDrawAuthority
    schedule: KnockoutRunSchedule

    @property
    def calendar(self):
        return self.schedule.calendar

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))

    @property
    def topology(self):
        return project_canonical_draw_nodes(draw=self.draw)

    @model_validator(mode='after')
    def validate_source(self):
        if canonical_hash(self.profile.model_dump(mode='json')) != self.profile_payload_fingerprint:
            raise ValueError('Frozen scheduled sporting profile changed')
        if self.draw_input.schema_version not in {'tournament_draw_input_authority.v3','tournament_draw_input_authority.v12'}:
            raise ValueError('Scheduled initial knockout requires an unrepaired canonical Draw Input')
        inputs = TournamentDrawInputAuthority.model_validate_json(self.draw_input.model_dump_json())
        expected_capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
            main_entrant_count=self.profile.main_entrants,qualification_draw_size=self.profile.qualification_entrants,
            qualifier_spots=self.profile.qualifier_spots,wild_card_slots=self.profile.wild_cards)
        if (inputs.capacity != expected_capacity or inputs.event_id != self.profile.occurrence_id
                or inputs.main_seed_count != self.profile.seeds_count):
            raise ValueError('Scheduled Draw changes the copied sporting profile capacity or seeds')
        if (len(inputs.direct_main_player_ids) != expected_capacity.direct_main_slots
                or len(inputs.wild_card_player_ids) != self.profile.wild_cards
                or len(inputs.qualification_player_ids) != self.profile.qualification_entrants):
            raise ValueError('Scheduled initial Draw requires the complete source-sized field')
        expected = TournamentDrawAuthorityBuilder.build(draw_input=inputs,command_id=self.draw.generated_by_command_id)
        if expected != self.draw:
            raise ValueError('Scheduled knockout Draw differs from its committed input')
        self.schedule.validate_capacities(main_capacity=self.draw.main.bracket_size,
            qualification_capacities=tuple(b.bracket_size for b in self.draw.qualification_brackets))
        return self

    def match_seed(self, match_id):
        if match_id not in {p.match_id for p in self.topology.plans}:
            raise ValueError('Scheduled seed requires an executable match, never a BYE')
        return int(canonical_hash({'schema_version':'scheduled_knockout_match_seed.v1',
            'root':self.draw_input.draw_seed,'event':self.draw.event_id,
            'season_index':self.schedule.main[0].week.season_index,'match':match_id})[:15],16)


def scheduled_knockout_progress(*, plan: ScheduledKnockoutFeederPlan, matches,
                                positions: Mapping[str, KnockoutRoundPosition], current: KnockoutRoundPosition):
    """Select due matches after validating accepted results and their slot dates.

    ``positions`` comes from the existing frozen slot ledger, not from inferred
    match sequence numbers. Record order cannot decide a feeder winner.
    The current position carries the consuming owner's Run clock. Historical
    slots retain their exact clocks when that Run's horizon has been extended.
    """
    plan.validate_source()
    plan.schedule.validate_runtime_calendar(current.week.calendar)
    rows = plan_knockout_run_matches(draw=plan.draw,schedule=plan.schedule)['matches']
    expected = {r['match_id']: KnockoutRoundPosition.model_validate_json(json.dumps(r['position'])) for r in rows}
    ids = [m.match_id for m in matches]
    if len(ids) != len(set(ids)) or set(positions) != set(ids) or not set(ids) <= set(expected):
        raise ValueError('Scheduled knockout has duplicate, foreign or missing slot evidence')
    round_calendars = {}
    for m in matches:
        actual = positions[m.match_id]
        plan.schedule.validate_runtime_calendar(actual.week.calendar)
        if actual.week.calendar.season_count > current.week.calendar.season_count:
            raise ValueError('Accepted knockout clock exceeds the consuming Run horizon')
        if actual.chronological_key != expected[m.match_id].chronological_key or m.week != actual.week:
            raise ValueError('Accepted knockout match differs from its frozen round schedule')
        if actual.chronological_key > current.chronological_key:
            raise ValueError('Scheduled knockout cannot consume future match evidence')
        clock = round_calendars.setdefault(actual.chronological_key, actual.week.calendar)
        if clock != actual.week.calendar:
            raise ValueError('One frozen knockout round cannot contain different Run clocks')
    horizons = [clock.season_count for _, clock in sorted(round_calendars.items())]
    if horizons != sorted(horizons):
        raise ValueError('Accepted knockout rounds cannot shrink the Run horizon')
    if any(mid not in positions and pos.chronological_key < current.chronological_key for mid,pos in expected.items()):
        raise ValueError('An earlier knockout round is incomplete')
    progress = _project_draw_progress(plan=plan,draw=plan.draw,
        source_season_index=plan.schedule.main[0].week.season_index,matches=matches,
        runtime_calendar=current.week.calendar)
    due = tuple(m for m in progress.ready_matches
                if expected[m.match_id].chronological_key == current.chronological_key)
    return progress, due
