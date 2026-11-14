"""A native prospect's career uses its Saved birth identity before any match."""
from types import SimpleNamespace as NS
import pytest
from beta_engine.application.native_career_identity import career_world
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical


def setup_identity():
    clock = RunCalendar(52, 1, 2030, 2)
    state = NS(week=RunWeekPosition(calendar=clock, season_index=0, week=4))
    world = NS(run_id='r', branch_id='b', players=[], fingerprint='f' * 64, initial_turn_pro=None)
    life = NS(run_id='r', branch_id='b', players=[NS(player_id='born', birth_year=2015, birth_year_week=3)])
    records = ({'prospect_id': 'born', 'display_name': 'Born Player', 'country_code': 'CZE',
                'birth_year': 2015, 'birth_year_week': 3},
               {'prospect_id': 'future', 'display_name': 'Future Player', 'country_code': 'CZE',
                'birth_year': 2015, 'birth_year_week': 10})
    source = NS(run_id='r', for_week=lambda n: NS(records=records))
    return world, state, life, source


def test_saved_birth_identity_exists_before_the_first_played_match():
    world, state, life, source = setup_identity()
    scoped = career_world(world, state, life, source)
    assert set(scoped.career_identities) == {'born'}
    assert scoped.career_identities['born'].name == 'Born Player'
    assert scoped.career_birth_ordinals == {'born': 2}
    assert 'future' not in scoped.career_identities


@pytest.mark.parametrize('foreign', ['lifecycle', 'source'])
def test_foreign_saved_identity_sources_fail_closed(foreign):
    world, state, life, source = setup_identity()
    if foreign == 'lifecycle':
        life.branch_id = 'sibling'
    else:
        source.run_id = 'another'
    with pytest.raises(ValueError, match='another'):
        career_world(world, state, life, source)
