"""Fast version/scheduling contracts; production HTTP tests prove sporting writes."""

from types import SimpleNamespace

import pytest

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_global_slots import (
    match_seed,
    next_schedule,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    CalendarTourEdition,
    build_draw,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldResolver
from tests.domain.test_calendar_tour_contract import approved_authority

pytestmark = pytest.mark.pr_critical


def authority(eid, *, start=1):
    old, _ = approved_authority()
    edition = old.edition.model_copy(
        update={
            "schema_version": "calendar_tournament_edition.v2",
            "edition_id": eid,
            "start_slot": start,
            "simulation_seed": 918,
        }
    )
    submissions = tuple(
        s.model_copy(
            update={
                "application_id": f"{eid}:{s.player_id}",
                "event_id": eid,
                "validation_authority_fingerprint": edition.fingerprint,
            }
        )
        for s in old.submissions
    )
    ranking = old.ranking_authority.model_copy(update={"event_id": eid})
    field = TournamentEntryFieldResolver.build_initial(
        authority=ranking,
        applications=tuple(s.to_entry_field_application() for s in submissions),
        capacity=edition.capacity,
    )
    value = old.model_copy(
        update={
            "edition": edition,
            "submissions": submissions,
            "ranking_authority": ranking,
            "field": field,
            "draw": None,
        }
    )
    value = value.model_copy(update={"draw": build_draw(value, "draw", 71)})
    return CalendarEditionAuthority.model_validate_json(value.model_dump_json())


def test_legacy_edition_json_and_hash_are_unchanged_by_the_new_executor():
    old, _ = approved_authority()
    raw = old.edition.model_dump(mode="json")
    assert "simulation_seed" not in raw
    assert raw["schema_version"] == "calendar_tournament_edition.v1"
    restored = CalendarTourEdition.model_validate_json(old.edition.model_dump_json())
    assert restored.fingerprint == canonical_hash(raw)
    assert restored == old.edition


def test_slot_seed_uses_immutable_match_identity_and_not_command_or_collection_position():
    a, b = authority("parallel-a"), authority("parallel-b")
    mids = ("qf1", "qf2", "qf3", "qf4")
    forward = {
        f"{x.edition.edition_id}:{mid}": match_seed(x, f"{x.edition.edition_id}:{mid}")
        for x in (a, b)
        for mid in mids
    }
    reverse = {
        f"{x.edition.edition_id}:{mid}": match_seed(x, f"{x.edition.edition_id}:{mid}")
        for x in (b, a)
        for mid in reversed(mids)
    }
    assert forward == reverse and len(set(forward.values())) == 8
    changed = a.model_copy(
        update={"edition": a.edition.model_copy(update={"simulation_seed": 919})}
    )
    assert match_seed(changed, "parallel-a:qf1") != forward["parallel-a:qf1"]


@pytest.mark.parametrize("start", [1, 14, 1000])
def test_scheduler_uses_the_nearest_real_slot_without_day_or_seven_slot_limits(start):
    a, b = (
        authority("parallel-a", start=start),
        authority("parallel-b", start=start + 1),
    )
    state = SimpleNamespace(week=a.edition.week, editions=(b, a))
    number, due, opened = next_schedule(state, SimpleNamespace(events=()))
    assert number == start + 3 and opened is None
    assert [(item.edition.edition_id, index) for item, index, _ in due] == [
        ("parallel-a", i) for i in range(4)
    ]
    assert all(len(ids) == 2 for _, _, ids in due)


def test_inherited_terminal_record_preserves_original_edition_owner_and_extension_once():
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.rankings.calendar_terminal_result import (
        CalendarInheritedTerminalRankingResult,
    )
    from tests.domain.test_calendar_terminal_result import terminal

    original = terminal(RunCalendar(4, 2, 2040, 1))
    body = original.model_dump(mode="json")
    body.update(
        schema_version="calendar_terminal_edition_result.v2",
        branch_id="independent",
        source_edition_branch_id="branch",
    )
    result = CalendarInheritedTerminalRankingResult.model_validate_json(
        __import__("json").dumps(body)
    )
    assert result.source_edition_branch_id == original.branch_id
    assert (
        result.branch_id == "independent"
        and result.completed_week == original.completed_week
    )
    assert (
        result.for_publication(RunCalendar(4, 2, 2040, 2)).source_fingerprint
        == original.source_fingerprint
    )
    assert "first_publication_week" not in result.model_dump(mode="json")
    body["source_edition_branch_id"] = "independent"
    with pytest.raises(ValueError, match="distinct"):
        CalendarInheritedTerminalRankingResult.model_validate_json(
            __import__("json").dumps(body)
        )
