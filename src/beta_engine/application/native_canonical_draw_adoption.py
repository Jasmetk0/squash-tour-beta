"""Explicit adoption of one immutable source Draw into the existing native ledger."""

import json

from pydantic import Field

from beta_engine.application.saved_fax_knockout_feeders import (
    SavedFaxKnockoutFeederService,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    CalendarTourEdition,
)
from beta_engine.domain.tournaments.native_canonical_knockout import (
    NativeCanonicalDrawBinding,
    NativeCanonicalRoundSchedule,
    canonical_announcement_week,
    saved_ranked_point_table,
    validate_ranked_publication_week,
)


class SavedDrawAdoptionInput(FrozenInput):
    season: str = Field(min_length=1)
    event_id: str = Field(min_length=3)
    source_plan_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    schedule: NativeCanonicalRoundSchedule


def adopt_saved_draw(repository, ctx, state, command, *, replay_plan=None):
    clock, _revision, _world, _health, cp, _saved, evidence = ctx
    if state.schema_version == "native_fork_tour.v1":
        raise ValueError(
            "Canonical Draw adoption requires a Branch-owned root; inherited native remapping is unsupported"
        )
    if command.edition_id is not None or set(command.data) != {
        "season",
        "event_id",
        "source_plan_fingerprint",
        "schedule",
    }:
        raise ValueError(
            "Saved Draw adoption requires only its exact source identity and explicit round schedule"
        )
    data = SavedDrawAdoptionInput.model_validate_json(json.dumps(command.data))
    plan = (
        replay_plan
        if replay_plan is not None
        else SavedFaxKnockoutFeederService(repository).prepare(
            run_id=state.run_id,
            branch_id=state.branch_id,
            season=data.season,
            event_id=data.event_id,
            expected_saved_revision_id=command.expected_saved_head,
        )
    )
    source = plan.source
    if (
        source.draw.run_id,
        source.draw.branch_id,
        source.draw.event_id,
        str(source.source_event.season),
        plan.source_saved_revision_id,
        plan.fingerprint,
    ) != (
        state.run_id,
        state.branch_id,
        data.event_id,
        data.season,
        command.expected_saved_head,
        data.source_plan_fingerprint,
    ):
        raise ValueError("Saved Draw adoption differs from its authenticated source")
    binding = NativeCanonicalDrawBinding.from_plan(
        plan,
        data.schedule,
    )
    event = source.source_event
    week = RunWeekPosition(
        calendar=clock,
        season_index=int(str(event.season).split("/")[0]) - clock.start_year,
        week=event.season_week,
    )
    if (
        clock != plan.calendar
        or week.ordinal < cp.week.ordinal
        or canonical_announcement_week(binding).ordinal <= cp.week.ordinal
        or (
            week.ordinal == cp.week.ordinal
            and binding.schedule.qualification[0] <= state.slot_cursor
        )
    ):
        raise ValueError(
            "Canonical Draw requires the exact Run clock and a future announcement before play"
        )
    if any(
        a.edition.edition_id == event.event_id for a in state.editions
    ) or event.event_id in {t.tournament_id for t in cp.tournaments}:
        raise ValueError("Canonical Edition already exists in sporting history")
    # Opening exhibition evidence is separate from checkpoint.tournaments.
    if event.event_id == getattr(evidence, "knockout", evidence).match_id:
        raise ValueError(
            "Existing exhibition cannot be promoted to a Canonical Edition"
        )
    participants = {
        *source.draw_input.direct_main_player_ids,
        *source.draw_input.wild_card_player_ids,
        *source.draw_input.qualification_player_ids,
    }
    if not participants <= {p.player_id for p in cp.players}:
        raise ValueError(
            "Canonical Draw contains participants absent from the owned sporting checkpoint"
        )
    ranked = event.ranking_status == "ranked"
    if ranked:
        validate_ranked_publication_week(week)
    edition = CalendarTourEdition(
        schema_version="calendar_tournament_edition.v4",
        edition_id=event.event_id,
        name=event.event_name,
        week=week,
        announcement_week=canonical_announcement_week(binding),
        start_slot=binding.schedule.qualification[0],
        main_entrant_count=event.main_draw_size,
        ranked=ranked,
        point_table=saved_ranked_point_table(event) if ranked else {},
        validity_weeks=clock.weeks_per_year,
        simulation_seed=source.draw_input.draw_seed,
    )
    return CalendarEditionAuthority(
        edition=edition,
        canonical_binding=binding,
        created_command_id=command.command_id,
        created_saved_head=plan.source_saved_revision_id,
        played_saved_head=plan.source_saved_revision_id,
        draw=source.draw,
        draw_seed=source.draw_input.draw_seed,
        draw_command_id=source.draw.generated_by_command_id,
    )
