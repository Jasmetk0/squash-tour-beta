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


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "foreign_head",
        "late_announcement",
        "missing_player",
        "opening_knockout_id",
        "standalone_exhibition_id",
        "ranked",
        "multiweek",
        "fork",
    ],
)
def test_adoption_is_explicit_prospective_and_operation_scoped(authority, damage):
    from types import SimpleNamespace

    from beta_engine.application.native_canonical_draw_adoption import adopt_saved_draw

    binding = authority.canonical_binding
    source = binding.plan(authority.draw).source
    if damage in {"ranked", "multiweek"}:
        event = source.source_event.model_copy(
            update={
                **(
                    {
                        "ranking_status": type(source.source_event.ranking_status)(
                            "ranked"
                        )
                    }
                    if damage == "ranked"
                    else {"duration_in_season_weeks": 2, "end_season_week": 5}
                ),
            }
        )
        source = source.model_copy(update={"source_event": event})
    plan = freeze_knockout_feeder_plan(
        source=source,
        source_saved_revision_id="saved",
        source_saved_content_hash="a" * 64,
        calendar=binding.calendar,
    )
    week = RunWeekPosition(
        calendar=binding.calendar,
        season_index=0,
        week=3 if damage == "late_announcement" else 2,
    )
    ids = {
        *binding.draw_input.direct_main_player_ids,
        *binding.draw_input.wild_card_player_ids,
        *binding.draw_input.qualification_player_ids,
    }
    cp = SimpleNamespace(
        week=week,
        players=tuple(
            SimpleNamespace(player_id=p)
            for p in sorted(ids)[1 if damage == "missing_player" else 0 :]
        ),
        tournaments=(),
    )
    state = SimpleNamespace(
        run_id="run",
        branch_id="branch",
        schema_version="native_fork_tour.v1"
        if damage == "fork"
        else "calendar_tour_authority.v5",
        editions=(),
        slot_cursor=0,
    )
    cmd = SimpleNamespace(
        command_id="adopt",
        edition_id=None,
        expected_saved_head="foreign" if damage == "foreign_head" else "saved",
        data={
            "season": "2000/2001",
            "event_id": source.draw.event_id,
            "source_plan_fingerprint": plan.fingerprint,
            "schedule": binding.schedule.model_dump(mode="json"),
        },
    )
    exhibition_collision = damage in {"opening_knockout_id", "standalone_exhibition_id"}
    exhibition = SimpleNamespace(
        match_id=source.draw.event_id
        if exhibition_collision
        else "historical-exhibition",
    )
    evidence = (
        exhibition
        if damage == "standalone_exhibition_id"
        else SimpleNamespace(knockout=exhibition)
    )
    context = (binding.calendar, None, None, None, cp, None, evidence)
    if damage:
        message = (
            "Existing exhibition cannot be promoted" if exhibition_collision else None
        )
        with pytest.raises(ValueError, match=message):
            adopt_saved_draw(None, context, state, cmd, replay_plan=plan)
    else:
        assert (
            adopt_saved_draw(None, context, state, cmd, replay_plan=plan) == authority
        )


def test_canonical_slot_cannot_downgrade_to_an_untagged_legacy_match(authority):
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalSlot

    # Deliberately isolate the slot tag guard; this is not sporting evidence.
    plan = authority.canonical_binding.plan(authority.draw)
    item = FrozenSlotMatch.model_construct(
        edition_id=authority.edition.edition_id,
        index=0,
        match_id=plan.topology.plans[0].match_id,
        seed=plan.match_seed(plan.topology.plans[0].match_id),
        source_saved_head="saved",
        sequence=1,
    )
    slot = GlobalSlot.model_construct(
        schema_version="calendar_global_slot.v4",
        run_id="run",
        branch_id="branch",
        week=authority.edition.week,
        number=1,
        players=(),
        authorities=(authority,),
        scheduled=(item,),
    )
    with pytest.raises(ValueError, match="explicitly versioned frozen match"):
        slot.canonical_evidence()


def test_derived_terminal_does_not_silently_collapse_duplicate_ledger_records(
    authority,
):
    from types import SimpleNamespace

    plan = authority.canonical_binding.plan(authority.draw)
    record = SimpleNamespace(
        match_id=plan.topology.plans[0].match_id,
        week=SimpleNamespace(calendar=plan.calendar),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        completed_canonical_result(
            authority, (SimpleNamespace(accepted=(record, record)),)
        )


def test_future_adoption_retains_source_announcement_across_strict_horizon_extension(
    authority,
):
    binding = authority.canonical_binding
    original = binding.source_event.model_dump_json()
    clock = binding.calendar.extend_to(4)
    plan = freeze_knockout_feeder_plan(
        source=binding.plan(authority.draw).source,
        source_saved_revision_id="saved",
        source_saved_content_hash="a" * 64,
        calendar=clock,
    )
    extended = NativeCanonicalDrawBinding.from_plan(plan, binding.schedule)
    projected = canonical_announcement_week(extended)
    assert projected.calendar == clock
    assert projected.ordinal == authority.edition.announcement_week.ordinal
    assert extended.source_event.model_dump_json() == original
    assert (
        extended.source_event.event_level_overrides["native_announcement_week"][
            "calendar"
        ]["season_count"]
        == 3
    )
    assert extended.plan(authority.draw) == plan


@pytest.mark.parametrize(
    "clock",
    [
        RunCalendar(52, 37, 2000, 4),
        RunCalendar(61, 38, 2000, 4),
        RunCalendar(61, 37, 2001, 4),
        RunCalendar(61, 37, 2000, 2),
    ],
)
def test_source_announcement_never_reinterprets_a_foreign_or_shorter_clock(
    authority, clock
):
    with pytest.raises(ValueError, match="different or later Run calendar"):
        canonical_announcement_week(
            authority.canonical_binding.model_copy(update={"calendar": clock})
        )
