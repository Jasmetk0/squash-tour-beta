"""Versioned native contracts retain exact source and fail closed at boundaries."""

import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.calendar_global_slots import (
    FrozenCanonicalSlotMatch,
    FrozenSlotMatch,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    CalendarTourEdition,
)
from beta_engine.domain.tournaments.canonical_knockout_feeders import (
    freeze_knockout_feeder_plan,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.native_canonical_knockout import (
    NativeCanonicalDrawBinding,
    NativeCanonicalRoundSchedule,
    canonical_announcement_week,
    canonical_edition_plan,
    completed_canonical_result,
)
from tests.infrastructure import test_fax_reference_player_draw as fax

pytestmark = [pytest.mark.smoke, pytest.mark.pr_critical]


@pytest.fixture(scope="module")
def fax_source(tmp_path_factory):
    return fax.fax_source.__wrapped__(tmp_path_factory)


@pytest.fixture
def authority(fax_source):
    clock = RunCalendar(61, 37, 2000, 3)
    event = next(e for e in fax_source[0].events if e.main_draw_size == 32).model_copy(
        update={
            "ranking_status": type(fax_source[0].events[0].ranking_status)("unranked"),
            "duration_in_season_weeks": 1,
            "season_week": 4,
            "start_season_week": 4,
            "end_season_week": 4,
            "year_week": 40,
            "event_level_overrides": {
                **next(
                    e for e in fax_source[0].events if e.main_draw_size == 32
                ).event_level_overrides,
                "native_announcement_week": RunWeekPosition(
                    calendar=clock, season_index=0, week=3
                ).model_dump(mode="json"),
            },
        }
    )
    inp = fax.in_memory_input(event, fax.ranking_snapshot(fax.PLAYERS))
    draw = TournamentDrawAuthorityBuilder.build(draw_input=inp, command_id="draw")
    source = fax.package_draw(event, inp, draw)
    plan = freeze_knockout_feeder_plan(
        source=source,
        source_saved_revision_id="saved",
        source_saved_content_hash="a" * 64,
        calendar=clock,
    )
    binding = NativeCanonicalDrawBinding.from_plan(
        plan,
        NativeCanonicalRoundSchedule(qualification=(1, 2, 3), main=(4, 5, 6, 7, 8)),
    )
    edition = CalendarTourEdition(
        schema_version="calendar_tournament_edition.v4",
        edition_id=event.event_id,
        name=event.event_name,
        week=RunWeekPosition(calendar=clock, season_index=0, week=event.season_week),
        announcement_week=canonical_announcement_week(binding),
        start_slot=1,
        main_entrant_count=32,
        ranked=False,
        point_table={},
        validity_weeks=61,
        simulation_seed=inp.draw_seed,
    )
    return CalendarEditionAuthority(
        edition=edition,
        created_command_id="adopt",
        created_saved_head="saved",
        played_saved_head="saved",
        canonical_binding=binding,
        draw=draw,
        draw_seed=inp.draw_seed,
        draw_command_id="draw",
    )


def revalidate(authority):
    return CalendarEditionAuthority.model_validate_json(authority.model_dump_json())


def test_native_schedule_uses_real_nodes_and_never_simulates_byes(authority):
    assert revalidate(authority) == authority
    plan = canonical_edition_plan(authority, {})
    source = authority.canonical_binding.plan(authority.draw)
    assert len(plan) == 51
    assert not set(source.topology.bye_match_ids).intersection(p[0] for p in plan)
    assert len([p for p in plan if p[1] == 1 and p[2]]) == 8
    assert all(
        not p[2] for p in plan if p[1] >= 4
    )  # Main waits for all real Q winners.
    assert completed_canonical_result(authority, ()) is None
    assert FrozenSlotMatch.model_fields["index"].metadata[-1].le == 6
    assert FrozenCanonicalSlotMatch.model_fields["index"].metadata[-1].le > 6


@pytest.mark.parametrize(
    "q,m",
    [
        ((1, 1, 2), (4, 5, 6, 7, 8)),
        ((1, 3, 2), (4, 5, 6, 7, 8)),
        ((1, 2, 3), (3, 4, 5, 6, 7)),
        ((), (1, 2)),
        ((0, 2, 3), (4, 5, 6, 7, 8)),
    ],
)
def test_schedule_rejects_implicit_or_nonchronological_rounds(q, m):
    with pytest.raises(ValueError):
        NativeCanonicalRoundSchedule(qualification=q, main=m)


@pytest.mark.parametrize(
    "damage",
    [
        "draw_seed",
        "saved_id",
        "saved_hash",
        "announcement",
        "ranked",
        "old_version",
        "duration",
        "schedule",
        "input",
        "draw",
        "name",
        "seed",
        "start_slot",
        "validity",
    ],
)
def test_exact_saved_binding_cannot_be_reinterpreted(authority, damage):
    raw = authority.model_dump(mode="json")
    if damage == "draw_seed":
        raw["draw_seed"] += 1
    elif damage == "saved_id":
        raw["played_saved_head"] = "another"
    elif damage == "saved_hash":
        raw["canonical_binding"]["saved_content_hash"] = "b" * 64
    elif damage == "announcement":
        raw["edition"]["announcement_week"]["week"] = 2
    elif damage == "ranked":
        raw["edition"]["ranked"] = True
    elif damage == "old_version":
        raw["edition"]["schema_version"] = "calendar_tournament_edition.v2"
    elif damage == "duration":
        raw["canonical_binding"]["source_event"]["duration_in_season_weeks"] = 2
    elif damage == "schedule":
        raw["canonical_binding"]["schedule"]["qualification"] = [1, 2]
    elif damage == "input":
        raw["canonical_binding"]["draw_input"]["draw_seed"] += 1
    elif damage == "name":
        raw["edition"]["name"] = "different"
    elif damage == "seed":
        raw["edition"]["simulation_seed"] += 1
    elif damage == "start_slot":
        raw["edition"]["start_slot"] += 1
    elif damage == "validity":
        raw["edition"]["validity_weeks"] += 1
    else:
        raw["draw"]["generated_by_command_id"] = "different"
    with pytest.raises(ValueError):
        CalendarEditionAuthority.model_validate_json(json.dumps(raw))


def test_missing_source_announcement_is_not_invented(authority):
    binding = authority.canonical_binding.model_copy(
        update={
            "source_event": authority.canonical_binding.source_event.model_copy(
                update={"event_level_overrides": {}}
            )
        }
    )
    with pytest.raises(ValueError, match="no date is inferred"):
        canonical_announcement_week(binding)
    # DTO strictness rejects unchecked Python list/bool inputs too.
    with pytest.raises(ValidationError):
        NativeCanonicalRoundSchedule(qualification=(True, 2, 3), main=(4, 5, 6, 7, 8))
