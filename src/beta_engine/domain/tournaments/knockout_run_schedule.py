"""Explicit cross-week knockout chronology on a Run-owned calendar.

This plans rounds and canonical match identities, never players, outcomes,
Entry eligibility or civil-day/rest calibration. Legacy same-week schemas stay.
"""
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.canonical_knockout_topology import project_canonical_draw_nodes


class KnockoutRoundPosition(FrozenInput):
    week: RunWeekPosition
    slot: int = Field(ge=1, strict=True)

    @property
    def chronological_key(self):
        return self.week.ordinal, self.slot


class KnockoutRunSchedule(FrozenInput):
    schema_version: Literal['knockout_run_round_schedule.v1'] = 'knockout_run_round_schedule.v1'
    calendar: RunCalendar
    qualification: tuple[KnockoutRoundPosition, ...] = ()
    main: tuple[KnockoutRoundPosition, ...] = Field(min_length=1)

    @classmethod
    def on_one_week(cls, *, week, qualification, main):
        """Read an old explicit same-week schedule without changing its bytes."""
        return cls(calendar=week.calendar,
                   qualification=tuple(KnockoutRoundPosition(week=week,slot=s) for s in qualification),
                   main=tuple(KnockoutRoundPosition(week=week,slot=s) for s in main))

    @model_validator(mode='after')
    def validate_chronology(self):
        rounds = (*self.qualification, *self.main)
        if any(r.week.calendar != self.calendar for r in rounds):
            raise ValueError('Every knockout round must use the exact Run calendar')
        if len({r.week.season_index for r in rounds}) != 1:
            raise ValueError('A knockout tournament cannot cross the Run season boundary')
        keys = tuple(r.chronological_key for r in rounds)
        if keys != tuple(sorted(set(keys))):
            raise ValueError('Q/Main rounds must be unique and strictly chronological')
        return self

    def validate_capacities(self, *, main_capacity: int, qualification_capacities: tuple[int, ...]):
        def rounds(capacity):
            if type(capacity) is not int or capacity < 2 or capacity > 128 or capacity & (capacity-1):
                raise ValueError('Round schedule requires a power-of-two bracket capacity in 2..128')
            return capacity.bit_length()-1
        if len(self.main) != rounds(main_capacity):
            raise ValueError('Schedule must cover every physical Main round')
        if qualification_capacities:
            if any(len(self.qualification) != rounds(c) for c in qualification_capacities):
                raise ValueError('Schedule must cover every physical Qualification round')
        elif self.qualification:
            raise ValueError('Qualification rounds require Qualification brackets')

    def validate_runtime_calendar(self, calendar: RunCalendar):
        """Keep this frozen schedule; only the consuming Run horizon may grow."""
        if calendar == self.calendar:
            return
        try:
            extended = self.calendar.extend_to(calendar.season_count)
        except ValueError as error:
            raise ValueError('Knockout runtime calendar may only extend the frozen source horizon') from error
        if calendar != extended:
            raise ValueError('Knockout runtime calendar may only extend the frozen source horizon')

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def plan_knockout_run_matches(*, draw, schedule: KnockoutRunSchedule):
    """Use canonical feeder identities; exclude BYEs from executable matches."""
    schedule.validate_capacities(
        main_capacity=draw.main.bracket_size,
        qualification_capacities=tuple(b.bracket_size for b in draw.qualification_brackets),
    )
    topology = project_canonical_draw_nodes(draw=draw)
    executable = {p.group_id for p in topology.plans}
    rows = []
    for bracket in (*draw.qualification_brackets, draw.main):
        rounds = schedule.qualification if bracket.draw_type == 'qualification' else schedule.main
        for node in bracket.nodes:
            if node.node_id not in executable:
                continue
            position = rounds[node.round_number-1]
            rows.append({'match_id': node.node_id, 'draw_type': bracket.draw_type,
                         'round_number': node.round_number,
                         'position': position.model_dump(mode='json')})
    rows.sort(key=lambda r: (r['position']['week']['season_index'], r['position']['week']['week'],
                             r['position']['slot'], r['match_id']))
    payload = {'schema_version': 'knockout_run_match_schedule.v1',
               'draw_fingerprint': draw.fingerprint, 'schedule_fingerprint': schedule.fingerprint,
               'matches': rows, 'bye_match_ids': list(topology.bye_match_ids),
               'sporting_execution_ready': False}
    return {**payload, 'fingerprint': canonical_hash(payload)}
