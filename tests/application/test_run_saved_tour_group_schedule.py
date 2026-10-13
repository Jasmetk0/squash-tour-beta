"""Archived group matches are bound to original Format/Topology, not a guessed bracket."""
import pytest

from beta_engine.application.run_saved_tour_group_schedule import (
    resolve_saved_tour_group_schedule,
)
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleBuilder,
)
from tests.domain.test_group_match_schedule_authority import (
    build_format, build_topology,
)

pytestmark = pytest.mark.pr_critical


def _component(group_count=2, group_size=3):
    format_ = build_format(group_count=group_count, group_size=group_size)
    topology = build_topology(format_)
    schedule = TournamentGroupMatchScheduleBuilder.build(
        format_authority=format_, topology_authority=topology, command_id="schedule",
    )
    rows = {}
    for key, authority, command in (
        ("format_authorities", format_, format_.configured_by_command_id),
        ("topology_authorities", topology, topology.generated_by_command_id),
        ("group_match_schedules", schedule, schedule.generated_by_command_id),
    ):
        rows[key] = [{
            "run_id": "run", "branch_id": "branch", "event_id": "EVENT",
            "command_id": command, "authority_fingerprint": authority.fingerprint,
            "payload_json": authority.model_dump_json(),
            **({
                "format_authority_fingerprint": schedule.format_authority_fingerprint,
                "topology_authority_fingerprint": schedule.topology_authority_fingerprint,
            } if key == "group_match_schedules" else {}),
            **({
                "format_authority_fingerprint": topology.format_authority_fingerprint,
            } if key == "topology_authorities" else {}),
        }]
    return rows, schedule


def _read(component, *, event_id="EVENT", result=None):
    return resolve_saved_tour_group_schedule(
        component, run_id="run", branch_id="branch", event_id=event_id,
        published_result=result,
    )


def test_genuine_saved_two_group_match_day_schedule_and_no_synthetic_results():
    rows, scheduled = _component(group_count=2, group_size=3)
    projected = _read(rows)
    assert projected.group_count == 2 and projected.group_size == 3
    assert projected.match_day_count == 3 and len(projected.matches) == 6
    assert projected.authority_fingerprint == scheduled.fingerprint
    assert sorted({m.group_index for m in projected.matches}) == [1, 2]
    assert sorted({m.match_day_ordinal for m in projected.matches}) == [1, 2, 3]
    assert all(m.best_of in (3, 5) and m.top_player_id != m.bottom_player_id
               for m in projected.matches)
    assert projected.matches == tuple(sorted(
        projected.matches,
        key=lambda m: (m.match_day_ordinal, m.match_order, m.group_index, m.match_id),
    ))
    assert _read(rows, event_id="other") is None
    assert _read(None) is None
    assert _read({}) is None


def test_foreign_duplicate_or_corrupt_saved_group_schedule_fails_closed():
    rows, _ = _component(group_count=1, group_size=4)
    row = rows["group_match_schedules"][0]
    with pytest.raises(ValueError, match="another Run/Branch"):
        _read({**rows, "group_match_schedules": [{**row, "branch_id": "fork"}]})
    with pytest.raises(ValueError, match="Ambiguous"):
        _read({**rows, "group_match_schedules": [row, row]})
    with pytest.raises(ValueError, match="requires its original"):
        _read({"group_match_schedules": [row]})
    with pytest.raises(ValueError, match="identity/fingerprint"):
        _read({**rows, "group_match_schedules": [
            {**row, "authority_fingerprint": "0" * 64},
        ]})
    with pytest.raises(ValueError, match="provenance mismatch"):
        _read({**rows, "group_match_schedules": [
            {**row, "topology_authority_fingerprint": "0" * 64},
        ]})


def test_saved_group_schedule_without_canonical_publication_does_not_invent_scores():
    rows, _ = _component(group_count=2, group_size=4)
    assert _read(rows).matches
    # Nothing from the Current Admin/Viewer results is queried by this read.
    assert "scoreline" not in _read(rows).model_dump_json()
