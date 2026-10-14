"""PR-critical contract for the real Admin hybrid Format authority boundary.

The real Chromium job separately verifies the production HTTP/SQLite journey.
"""
import pytest
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupFormatConfiguration,
    TournamentGroupCrossingMatch,
    TournamentGroupCrossingSource,
)

pytestmark = pytest.mark.pr_critical


def _hybrid_format(*, crossing=None, group_count=2, group_size=2, advancing=1):
    if crossing is None:
        crossing = (
            TournamentGroupCrossingMatch(
                match_index=1,
                top=TournamentGroupCrossingSource(group_index=1, finishing_position=1),
                bottom=TournamentGroupCrossingSource(group_index=2, finishing_position=1),
            ),
        )
    return TournamentFormatAuthority(
        run_id="run", branch_id="branch", event_id="event",
        target_season_index=0, configured_by_command_id="reviewed-hybrid",
        entry_field_fingerprint="a"*64, format_kind="groups_knockout",
        group_configuration=TournamentGroupFormatConfiguration(
            group_count=group_count, group_size=group_size,
            seeded_slots_per_group=0, group_seed_placements=(),
            match_best_of=3, rules_source_kind="season_policy",
            group_rules_policy_fingerprint="b"*64,
            group_rules_effective_from_season_index=0,
            advancing_per_group=advancing, knockout_crossings=crossing,
        ),
    )


def test_explicit_hybrid_first_round_is_canonical_and_immutable():
    value = _hybrid_format()
    assert value.group_configuration is not None
    assert value.group_configuration.advancing_per_group == 1
    assert value.group_configuration.knockout_crossings[0].top.group_index == 1
    assert value.group_configuration.knockout_crossings[0].bottom.group_index == 2
    assert len(value.fingerprint) == 64
    assert TournamentFormatAuthority.model_validate_json(value.model_dump_json()) == value


def test_hybrid_cannot_miss_or_reuse_advancers_or_allocate_odd_knockout():
    a = TournamentGroupCrossingSource(group_index=1, finishing_position=1)
    b = TournamentGroupCrossingSource(group_index=2, finishing_position=1)
    with pytest.raises(ValueError, match="cannot pair one group position"):
        TournamentGroupCrossingMatch(match_index=1, top=a, bottom=a)
    with pytest.raises(ValueError, match="crossing count"):
        _hybrid_format(crossing=())
    with pytest.raises(ValueError, match="power of two"):
        _hybrid_format(group_count=3)
    with pytest.raises(ValueError, match="non-advancing group position"):
        _hybrid_format(crossing=(TournamentGroupCrossingMatch(
            match_index=1, top=a, bottom=TournamentGroupCrossingSource(
                group_index=1, finishing_position=2
            )
        ),))
    with pytest.raises(ValueError, match="cannot exceed group size"):
        _hybrid_format(advancing=3)


def test_hybrid_browser_is_explicit_opt_in_and_does_not_use_ordinary_group_result_fixtures():
    from pathlib import Path
    body=(Path(__file__).resolve().parents[2]
          / "scripts/admin_saved_group_browser_smoke.py").read_text()
    assert 'parser.add_argument("--hybrid-preparation"' in body
    assert 'browser_click(page, "Choose groups + knockout"' in body
    assert 'select_option("1:1")' in body
    assert 'select_option("2:1")' in body
    assert 'format/configure' not in body
