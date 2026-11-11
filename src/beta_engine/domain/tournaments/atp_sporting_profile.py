"""Versioned ATP event configuration copied into an independent Run Package.

Tournament structure/points come from tennis; matches and table rules explicitly
use the stored squash policies. No automatic Race, age or seed eligibility.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.tournaments.calendar_groups import NativeGroupConfiguration
from beta_engine.domain.tournaments.calendar_tour import CalendarTourEdition
from beta_engine.domain.tournaments.format_authority import TournamentGroupRulesPolicy


class ATPSportingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["atp_squash_group_profile.v1"]
    occurrence_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_start_date: str
    source_end_date: str
    source_urls: tuple[str, ...] = Field(min_length=1)
    entrant_selection: Literal["admin_selected_no_automatic_race_or_age"]
    native_announcement_lead_weeks: int = Field(ge=1, le=52)
    group_count: int = Field(ge=1, le=64)
    group_size: int = Field(ge=2, le=128)
    advancing_per_group: int = Field(ge=1)
    knockout_crossings: tuple[dict, ...]
    ranked: bool
    played_group_win_points: int = Field(ge=0, le=1000000)
    knockout_stage_points: dict[str, int]
    match_best_of: Literal[3, 5]
    knockout_best_of: Literal[3, 5]
    scoring_policy_id: Literal["master_group_table_points.v1"]
    tie_break_policy_id: Literal["wins_points_h2h_ratios_admin_unresolved.v1"]
    walkover_policy_id: Literal["group_wo_win_max_points_no_fabricated_ratios.v1"]

    @model_validator(mode="after")
    def validate_structure(self):
        start, end = date.fromisoformat(self.source_start_date), date.fromisoformat(self.source_end_date)
        if end < start or (end - start).days > 21:
            raise ValueError("Invalid ATP sporting source date window")
        if not self.occurrence_id.startswith(f"atp_{start.year}_"):
            raise ValueError("ATP sporting profile source year mismatch")
        if any(not url.startswith("https://") for url in self.source_urls):
            raise ValueError("ATP sporting evidence requires HTTPS source URLs")
        # Validate the same production format/point contracts used at import.
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        from beta_engine.domain.calendar.run_week_position import RunWeekPosition
        self.build_edition(
            run_id="profile-validation", branch_id="profile-validation", command_id="profile-validation",
            week=RunWeekPosition(calendar=RunCalendar(52, 1, start.year, 1), season_index=0, week=2),
            announcement_week=RunWeekPosition(calendar=RunCalendar(52, 1, start.year, 1), season_index=0, week=1),
            start_slot=1, seed=0,
        )
        return self

    def build_edition(self, *, run_id, branch_id, command_id, week, announcement_week, start_slot, seed):
        rules = TournamentGroupRulesPolicy(
            run_id=run_id, branch_id=branch_id, adopted_by_command_id=command_id,
            effective_from_season_index=week.season_index,
            default_match_best_of=self.match_best_of,
            scoring_policy_id=self.scoring_policy_id,
            tie_break_policy_id=self.tie_break_policy_id,
            walkover_policy_id=self.walkover_policy_id,
        )
        groups = NativeGroupConfiguration.model_validate({
            "format_kind": "groups_knockout", "rules": rules,
            "played_group_win_points": self.played_group_win_points,
            "knockout_best_of": self.knockout_best_of,
            "groups": {
                "group_count": self.group_count, "group_size": self.group_size,
                "match_best_of": self.match_best_of, "rules_source_kind": "season_policy",
                "group_rules_policy_fingerprint": rules.fingerprint,
                "group_rules_effective_from_season_index": rules.effective_from_season_index,
                "advancing_per_group": self.advancing_per_group,
                "knockout_crossings": self.knockout_crossings,
            },
        })
        return CalendarTourEdition(
            schema_version="calendar_tournament_edition.v3",
            edition_id=self.occurrence_id, name=self.name, week=week,
            announcement_week=announcement_week, start_slot=start_slot, simulation_seed=seed,
            main_entrant_count=self.group_count * self.group_size,
            ranked=self.ranked, point_table=self.knockout_stage_points,
            validity_weeks=week.calendar.weeks_per_year, group_configuration=groups,
        )
