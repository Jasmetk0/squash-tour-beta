"""Prepare the sourced 2025 Next Gen format for the native squash Tour."""

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from beta_engine.application.atp_earth_run_calendar_preview import preview_atp_earth_weeks_on_run
from beta_engine.application.atp_saved_snapshot_week_preview import (
    audit_saved_atp_tour_bindings,
    build_saved_atp_reference_week_mapping,
)
from beta_engine.application.atp_saved_tour_source import read_saved_atp_source
from beta_engine.application.calendar_tour_service import CalendarTourCommand, CalendarTourService
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.calendar_groups import NativeGroupConfiguration
from beta_engine.domain.tournaments.calendar_tour import CalendarTourEdition
from beta_engine.domain.tournaments.format_authority import TournamentGroupRulesPolicy


NEXT_GEN_2025_ID = "atp_2025_next_gen_atp_finals"


class ATPNextGenEditionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1, max_length=100)
    expected_saved_head: str = Field(min_length=1)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_tour_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_slot: int = Field(ge=1, strict=True)
    seed: int = Field(strict=True)
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=800)


def preview_atp_next_gen_edition(repository, *, run_id: str, branch_id: str,
                                 request: ATPNextGenEditionPreviewRequest):
    """Return the ordinary Tour preview pinned to the exact Saved ATP source."""
    with repository._session_factory() as session:
        session.execute(text("BEGIN"))
        calendar, revision, state = read_saved_atp_source(
            session, run_id=run_id, branch_id=branch_id,
        )
        if request.expected_saved_head != revision.revision_id:
            raise ValueError("Saved ATP source changed; refresh the Tour")
        mapping = build_saved_atp_reference_week_mapping(state)
        source = preview_atp_earth_weeks_on_run(
            calendar=calendar, mapping=mapping, years=(2025,), occurrence_id=NEXT_GEN_2025_ID,
        )["events"][0]
        binding = audit_saved_atp_tour_bindings(
            state, selected_occurrences=frozenset({NEXT_GEN_2025_ID}),
        )["selected_occurrences"][NEXT_GEN_2025_ID]

    if (
        binding["category_id"] != "next_gen_finals"
        or source["source_start_date"] != "2025-12-17"
        or source["source_end_date"] != "2025-12-21"
        or len(source["run_weeks"]) != 1
        or source["source_finish_after_mapped_occupancy"]
    ):
        raise ValueError("Saved source disagrees with the documented 2025 Next Gen edition")

    target = source["run_weeks"][0]
    ordinal = source["run_ordinals"][0]
    if ordinal == 0:
        raise ValueError("The Next Gen announcement week is outside the Run horizon")
    announcement = calendar.position_at_ordinal(ordinal - 1)
    rules = TournamentGroupRulesPolicy(
        run_id=run_id, branch_id=branch_id,
        effective_from_season_index=target["season_index"],
        adopted_by_command_id=request.command_id,
    )
    groups = NativeGroupConfiguration.model_validate({
        "format_kind": "groups_knockout",
        "rules": rules,
        "played_group_win_points": 0,
        "groups": {
            "group_count": 2,
            "group_size": 4,
            "match_best_of": rules.default_match_best_of,
            "rules_source_kind": "season_policy",
            "group_rules_policy_fingerprint": rules.fingerprint,
            "group_rules_effective_from_season_index": rules.effective_from_season_index,
            "advancing_per_group": 2,
            "knockout_crossings": tuple(
                {
                    "match_index": group,
                    "top": {"group_index": group, "finishing_position": 1},
                    "bottom": {"group_index": opponent, "finishing_position": 2},
                }
                for group, opponent in ((1, 2), (2, 1))
            ),
        },
    })
    edition = CalendarTourEdition(
        schema_version="calendar_tournament_edition.v3",
        edition_id=NEXT_GEN_2025_ID,
        name=f'{binding["historical_category_label"]} 2025',
        week=RunWeekPosition(
            calendar=calendar, season_index=target["season_index"], week=target["season_week"],
        ),
        announcement_week=RunWeekPosition(
            calendar=calendar, season_index=announcement.season_index, week=announcement.season_week,
        ),
        start_slot=request.start_slot,
        simulation_seed=request.seed,
        main_entrant_count=8,
        ranked=False,
        point_table={},
        validity_weeks=calendar.weeks_per_year,
        group_configuration=groups,
    )
    command = CalendarTourCommand(
        action="create-edition",
        command_id=request.command_id,
        expected_saved_head=request.expected_saved_head,
        expected_checkpoint_fingerprint=request.expected_checkpoint_fingerprint,
        expected_tour_fingerprint=request.expected_tour_fingerprint,
        seed=request.seed,
        operator_label=request.operator_label,
        audit_reason=f"{request.audit_reason} [Saved ATP source {NEXT_GEN_2025_ID}, 2025-12-17 to 2025-12-21]",
        data=edition.model_dump(mode="json"),
    )
    return CalendarTourService(repository).preview(
        run_id=run_id, branch_id=branch_id, command=command,
    )
