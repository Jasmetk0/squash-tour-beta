"""Version, source, format, mapping and policy contracts for native groups."""
import json
from copy import deepcopy

import pytest

from beta_engine.domain.tournaments.calendar_groups import NativeGroupConfiguration
from beta_engine.domain.tournaments.calendar_tour import CalendarTourEdition
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupRetirementReceipt,
    TournamentGroupStandingsAuthority,
    TournamentGroupStandingsBuilder,
)
from tests.api.test_calendar_native_groups import configuration
from tests.domain.test_calendar_tour_contract import approved_authority
from tests.domain.test_tournament_group_standings_authority import (
    played,
    receipt,
    schedule_three,
)

pytestmark = pytest.mark.pr_critical


def group_edition():
    old = approved_authority()[0].edition.model_dump(mode='json')
    return {**old, 'schema_version': 'calendar_tournament_edition.v3',
            'point_table': {'champion': 100, 'finalist': 60, 'semifinal': 30},
            'group_configuration': configuration()}


@pytest.mark.parametrize('mutate', [
    lambda c: c.update(schema_version='calendar_tournament_edition.unknown'),
    lambda c: c.update(main_entrant_count=9),
    lambda c: c['group_configuration'].update(format_kind='unknown'),
    lambda c: c['group_configuration']['groups'].update(advancing_per_group=3),
    lambda c: c['group_configuration']['groups']['knockout_crossings'].pop(),
    lambda c: c['group_configuration']['groups']['knockout_crossings'][0].update(bottom={'group_index':1,'finishing_position':1}),
    lambda c: c['group_configuration']['groups'].update(group_rules_policy_fingerprint='f'*64),
    lambda c: c['group_configuration']['rules'].update(scoring_policy_id='invented'),
    lambda c: c.update(point_table={'champion': 100, 'finalist': 60}),
    lambda c: c['point_table'].update(semifinal=200),
    lambda c: c['group_configuration'].update(played_group_win_points=-1),
    lambda c: c['group_configuration']['groups'].update(match_best_of=7),
])
def test_invalid_native_group_capacity_crossing_policy_and_format_fail_closed(mutate):
    body = group_edition()
    mutate(body)
    with pytest.raises(ValueError):
        CalendarTourEdition.model_validate_json(json.dumps(body))


def test_historical_knockout_shape_seed_and_fingerprint_do_not_gain_group_fields():
    authority = approved_authority()[0]
    body = authority.edition.model_dump(mode='json')
    assert 'group_configuration' not in body and 'simulation_seed' not in body
    assert authority.edition == CalendarTourEdition.model_validate_json(json.dumps(body))
    for schema in ('calendar_tournament_edition.v1', 'calendar_tournament_edition.v2'):
        forged = group_edition()
        forged['schema_version'] = schema
        with pytest.raises(ValueError, match='Historical knockout'):
            CalendarTourEdition.model_validate_json(json.dumps(forged))


def test_group_policy_source_and_effective_season_are_explicit():
    good = configuration()
    parsed = NativeGroupConfiguration.model_validate_json(json.dumps(good))
    assert parsed == NativeGroupConfiguration.model_validate_json(parsed.model_dump_json())
    changed = deepcopy(good)
    changed['rules']['effective_from_season_index'] = 1
    with pytest.raises(ValueError, match='stored effective policy'):
        NativeGroupConfiguration.model_validate_json(json.dumps(changed))


def test_new_retirement_receipt_preserves_legacy_rejection_and_excludes_ratio_data():
    from beta_engine.domain.matches.models import MatchTerminationReason
    schedule = schedule_three()
    retired = played('A-B', 'A', 'B', 'A', (1, 0), termination=MatchTerminationReason.RETIREMENT)
    with pytest.raises(ValueError, match='RET table points'):
        receipt(schedule, retired, '1')
    new = TournamentGroupStandingsBuilder.receipt_from_result(
        scheduled_match=next(m for m in schedule.matches if m.match_id == 'A-B'),
        result=retired, result_fingerprint='1'*64, retirement_policy=True,
    )
    assert isinstance(new, TournamentGroupRetirementReceipt) and not new.games
    receipts = (new, receipt(schedule, played('A-C', 'A', 'C', 'A', (2, 0)), '2'),
                receipt(schedule, played('B-C', 'B', 'C', 'B', (2, 0)), '3'))
    standings = TournamentGroupStandingsBuilder.build(schedule=schedule, receipts=receipts,
        command_id='new-RET-standings', schema_version='tournament_group_standings_authority.v3')
    a = next(r for r in standings.groups[0].rows if r.player_id == 'A')
    assert (a.wins, a.group_points, a.games_won, a.games_lost, a.played_matches) == (2, 8, 2, 0, 2)
    restored = TournamentGroupStandingsAuthority.model_validate_json(standings.model_dump_json())
    assert restored == standings
    body = standings.model_dump(mode='json')
    body['schema_version'] = 'tournament_group_standings_authority.v2'
    with pytest.raises(ValueError, match='Historical group standings'):
        TournamentGroupStandingsAuthority.model_validate_json(json.dumps(body))


def test_browser_database_paths_reject_connection_url_input(tmp_path):
    from scripts.native_groups_global_slots_browser import local_database_path

    assert local_database_path(tmp_path / 'normal directory') == tmp_path / 'normal directory'
    for name in ('database?mode=memory', 'database#fragment', 'database\nextra', 'database\rextra'):
        with pytest.raises(ValueError, match='URL delimiters'):
            local_database_path(tmp_path / name)
    with pytest.raises(FileNotFoundError):
        local_database_path(tmp_path / 'missing.sqlite', must_exist=True)
    with pytest.raises(ValueError, match='existing local file'):
        local_database_path(tmp_path, must_exist=True)
    source = tmp_path / 'source.sqlite'
    source.touch()
    assert local_database_path(source, must_exist=True) == source
