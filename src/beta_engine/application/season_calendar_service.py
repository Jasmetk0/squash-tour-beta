"""Application service for deterministic season calendar construction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.calendar import (
    DEFAULT_SEASON_START_YEAR_WEEK,
    TOTAL_SEASON_WEEKS,
    parse_season_start_year,
    season_week_to_calendar_position,
)
from beta_engine.domain.tournaments.models import (
    SeasonCalendar,
    SeasonCalendarBuildRequest,
    SeasonCalendarBuildResult,
    SeasonCalendarBuildSummary,
    SeasonCalendarEvent,
    SeasonCalendarMetadata,
    SeasonCalendarValidationIssue,
    SeasonCalendarValidationIssueCodeMetadata,
    SeasonCalendarValidationIssueCodeRegistryResponse,
    SeasonCalendarValidationIssueV2,
    SeasonCalendarValidationResponse,
    SeasonCalendarValidationSummary,
    TournamentTemplate,
)
from beta_engine.infrastructure.points_config import load_points_config

SEASON_CALENDAR_VALIDATION_ISSUE_CODES: tuple[SeasonCalendarValidationIssueCodeMetadata, ...] = (
    SeasonCalendarValidationIssueCodeMetadata(code="calendar_missing", severity="warning", title="Calendar missing", description="No persisted season calendar exists for the requested season."),
    SeasonCalendarValidationIssueCodeMetadata(code="event_count_zero", severity="warning", title="No events in calendar", description="Persisted calendar exists but contains zero events."),
    SeasonCalendarValidationIssueCodeMetadata(code="event_id_missing", severity="error", title="Missing event ID", description="An event is missing event_id.", field="event_id"),
    SeasonCalendarValidationIssueCodeMetadata(code="duplicate_event_id", severity="error", title="Duplicate event ID", description="Two or more events share the same event_id.", field="event_id"),
    SeasonCalendarValidationIssueCodeMetadata(code="event_name_missing", severity="error", title="Missing event name", description="An event is missing event_name.", field="event_name"),
    SeasonCalendarValidationIssueCodeMetadata(code="category_missing", severity="error", title="Missing category", description="An event is missing category.", field="category"),
    SeasonCalendarValidationIssueCodeMetadata(code="tour_level_missing", severity="error", title="Missing tour level", description="An event is missing tour_level.", field="tour_level"),
    SeasonCalendarValidationIssueCodeMetadata(code="tour_level_unknown", severity="warning", title="Unknown tour level", description="tour_level is outside the known WORLD_TOUR/ELITE_TOUR set.", field="tour_level"),
    SeasonCalendarValidationIssueCodeMetadata(code="season_week_out_of_range", severity="error", title="Season week out of range", description="season_week is outside the 1..61 season window.", field="season_week"),
    SeasonCalendarValidationIssueCodeMetadata(code="end_season_week_out_of_range", severity="error", title="End season week out of range", description="end_season_week is outside the 1..61 season window.", field="end_season_week"),
    SeasonCalendarValidationIssueCodeMetadata(code="season_week_after_end_week", severity="error", title="Start week after end week", description="season_week is greater than end_season_week.", field="season_week"),
    SeasonCalendarValidationIssueCodeMetadata(code="duration_invalid", severity="error", title="Invalid duration", description="duration_in_season_weeks must be greater than 0.", field="duration_in_season_weeks"),
    SeasonCalendarValidationIssueCodeMetadata(code="duration_unusually_long", severity="warning", title="Unusually long duration", description="duration_in_season_weeks is unusually long (>3).", field="duration_in_season_weeks"),
    SeasonCalendarValidationIssueCodeMetadata(code="event_spans_many_weeks", severity="warning", title="Event spans many weeks", description="Event span between start and end season weeks is unusually large.", field="end_season_week"),
    SeasonCalendarValidationIssueCodeMetadata(code="main_draw_size_invalid", severity="error", title="Invalid main draw size", description="main_draw_size must be greater than 0.", field="main_draw_size"),
    SeasonCalendarValidationIssueCodeMetadata(code="qualification_draw_size_invalid", severity="error", title="Invalid qualification draw size", description="qualification_draw_size cannot be negative.", field="qualification_draw_size"),
    SeasonCalendarValidationIssueCodeMetadata(code="prize_money_negative", severity="error", title="Negative prize money", description="prize_money cannot be negative.", field="prize_money"),
    SeasonCalendarValidationIssueCodeMetadata(code="prestige_negative", severity="error", title="Negative prestige", description="prestige cannot be negative.", field="prestige"),
    SeasonCalendarValidationIssueCodeMetadata(code="duplicate_week_category_event_name", severity="warning", title="Duplicate week/category/name", description="Multiple events share season_week + category + event_name.", field="season_week"),
    SeasonCalendarValidationIssueCodeMetadata(code="event_count", severity="info", title="Event count summary", description="Computed informational event count metric."),
    SeasonCalendarValidationIssueCodeMetadata(code="first_last_weeks", severity="info", title="Season week span summary", description="Computed informational first/last season week metric."),
    SeasonCalendarValidationIssueCodeMetadata(code="world_tour_events", severity="info", title="World Tour count summary", description="Computed informational World Tour event count metric."),
    SeasonCalendarValidationIssueCodeMetadata(code="qualification_events", severity="info", title="Qualification event count summary", description="Computed informational qualification event count metric."),
    SeasonCalendarValidationIssueCodeMetadata(code="calendar_registry_parse_error", severity="error", title="Calendar registry parse error", description="Persisted season calendar registry JSON could not be parsed."),
    SeasonCalendarValidationIssueCodeMetadata(code="calendar_registry_model_error", severity="error", title="Calendar registry model error", description="Persisted season calendar registry failed model validation."),
)


class SeasonCalendarRegistry(BaseModel):
    calendars_by_season: dict[str, SeasonCalendar] = Field(default_factory=dict)


class SeasonCalendarAlreadyExistsError(ValueError):
    """Raised when attempting create-only insertion for an existing season calendar."""


class TournamentEditionRankingUpdate(BaseModel):
    ranking_status: str
    ranking_points_table: dict[str, Any] = Field(default_factory=dict)


def map_season_week_to_calendar_week(
    *,
    season: str,
    season_week: int,
    season_start_calendar_year: int = 2000,
    season_start_year_week: int = DEFAULT_SEASON_START_YEAR_WEEK,
) -> tuple[int, int]:
    """Compatibility wrapper around the centralized FAX season-week mapping."""

    _ = season_start_calendar_year  # Kept for API compatibility; season label is the source of calendar year.
    position = season_week_to_calendar_position(
        season=season,
        season_week=season_week,
        season_start_year_week=season_start_year_week,
    )
    return position.calendar_year, position.year_week


@dataclass(slots=True)
class SeasonCalendarService:
    """Build, validate, read, and persist file-backed season calendars."""

    template_service: TournamentTemplatesConfigService
    calendar_registry_path: Path = Path("config/simulation/season_calendars.json")

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_registry_path, Path):
            self.calendar_registry_path = Path(self.calendar_registry_path)

    def list_validation_issue_codes(self) -> SeasonCalendarValidationIssueCodeRegistryResponse:
        codes = sorted(SEASON_CALENDAR_VALIDATION_ISSUE_CODES, key=lambda item: item.code)
        return SeasonCalendarValidationIssueCodeRegistryResponse(
            codes=codes,
            code_count=len(codes),
            read_only=True,
            message="Stable read-only season calendar validation issue code registry.",
        )

    def get_calendar(self, *, season: str) -> SeasonCalendarBuildResult:
        registry = self._load_registry()
        calendar = registry.calendars_by_season.get(season)
        if calendar is None:
            return SeasonCalendarBuildResult(
                calendar=None,
                summary=SeasonCalendarBuildSummary(calendar_exists=False),
                metadata=None,
                validation_warnings=[],
                validation_errors=[],
            )
        summary = self._summary(calendar, persisted=True, calendar_exists=True)
        return SeasonCalendarBuildResult(
            calendar=calendar,
            summary=summary,
            metadata=calendar.metadata,
            validation_warnings=calendar.validation_warnings,
            validation_errors=calendar.validation_errors,
        )

    def create_calendar_if_absent(self, *, season: str, calendar: SeasonCalendar) -> SeasonCalendar:
        """Persist a season calendar only when the target season key does not yet exist."""
        registry = self._load_registry()
        if season in registry.calendars_by_season:
            raise SeasonCalendarAlreadyExistsError(
                f"Season calendar already exists for season '{season}'."
            )
        next_calendars = dict(registry.calendars_by_season)
        next_calendars[season] = calendar
        self._save_registry(SeasonCalendarRegistry(calendars_by_season=next_calendars))
        return calendar

    def update_edition_ranking(self, *, season: str, event_id: str, request: TournamentEditionRankingUpdate) -> SeasonCalendarEvent:
        """Update ranking configuration while an Edition remains an Admin Draft."""
        registry = self._load_registry()
        calendar = registry.calendars_by_season.get(season)
        if calendar is None:
            raise ValueError(f"No season calendar exists for season '{season}'.")
        event = next((item for item in calendar.events if item.event_id == event_id), None)
        if event is None:
            raise ValueError(f"Unknown Tournament Edition '{event_id}'.")
        if event.status != "planned":
            raise ValueError("Ranking status cannot change after competition has begun; retroactive ranking rewrites are not supported.")
        payload = event.model_dump(exclude_computed_fields=True)
        payload.update(ranking_status=request.ranking_status, ranking_points_table=dict(request.ranking_points_table), ranking_configuration_legacy=False)
        # Revalidate enum/input and computed contract before the atomic registry write.
        updated = SeasonCalendarEvent.model_validate(payload)
        next_events = [updated if item.event_id == event_id else item for item in calendar.events]
        next_calendar = calendar.model_copy(update={"events": next_events})
        next_calendars = dict(registry.calendars_by_season)
        next_calendars[season] = next_calendar
        self._save_registry(SeasonCalendarRegistry(calendars_by_season=next_calendars))
        return updated

    def build_calendar(self, *, season: str, request: SeasonCalendarBuildRequest) -> SeasonCalendarBuildResult:
        registry = self._load_registry()
        existing = season in registry.calendars_by_season
        if not request.dry_run and existing and not request.overwrite_existing:
            raise ValueError(f"Season calendar already exists for season '{season}'. Set overwrite_existing=true to replace only that season.")

        templates_config = self.template_service.get_config()
        all_templates = sorted(templates_config.templates, key=self._template_sort_key)
        skipped_inactive = [template.template_id for template in all_templates if not template.active]
        selected = [template for template in all_templates if request.include_inactive_templates or template.active]
        if request.max_events is not None:
            selected = selected[: request.max_events]

        events = self._build_events(
            season=season,
            templates=selected,
            seed=request.seed,
            season_start_calendar_year=request.season_start_calendar_year,
            season_start_year_week=request.season_start_year_week,
        )
        warnings, errors = self.validate_calendar_events(events, skipped_inactive_count=0 if request.include_inactive_templates else len(skipped_inactive))
        build_fingerprint = self._fingerprint(
            {
                "season": season,
                "seed": request.seed,
                "start_year": request.season_start_calendar_year,
                "start_week": request.season_start_year_week,
                "templates": [self._template_payload(template) for template in selected],
                "events": [event.model_dump(mode="json", exclude={"calendar_fingerprint"}) for event in events],
            }
        )
        for event in events:
            event.calendar_fingerprint = build_fingerprint
        metadata = SeasonCalendarMetadata(
            season=season,
            season_start_calendar_year=request.season_start_calendar_year,
            season_start_year_week=request.season_start_year_week,
            total_season_weeks=TOTAL_SEASON_WEEKS,
            event_count=len(events),
            build_seed=request.seed,
            build_fingerprint=build_fingerprint,
            source_template_count=len(templates_config.templates),
            persistence_path=None if request.dry_run else str(self.calendar_registry_path),
            dry_run=request.dry_run,
            overwrite_existing=request.overwrite_existing,
        )
        calendar = SeasonCalendar(season=season, events=events, metadata=metadata, validation_warnings=warnings, validation_errors=errors)
        if not request.dry_run:
            next_calendars = dict(registry.calendars_by_season)
            next_calendars[season] = calendar
            self._save_registry(SeasonCalendarRegistry(calendars_by_season=next_calendars))
        summary = self._summary(calendar, persisted=not request.dry_run, calendar_exists=existing or not request.dry_run)
        return SeasonCalendarBuildResult(calendar=calendar, summary=summary, metadata=metadata, validation_warnings=warnings, validation_errors=errors)



    def validate_persisted_calendar(self, *, season: str) -> SeasonCalendarValidationResponse:
        """Read-only validation for an already persisted season calendar."""

        try:
            result = self.get_calendar(season=season)
        except json.JSONDecodeError as exc:
            return self._registry_load_error_response(
                season=season,
                code="calendar_registry_parse_error",
                exception_type=type(exc).__name__,
            )
        except ValidationError as exc:
            return self._registry_load_error_response(
                season=season,
                code="calendar_registry_model_error",
                exception_type=type(exc).__name__,
            )
        if result.calendar is None:
            issues = [
                SeasonCalendarValidationIssueV2(
                    severity="warning",
                    code="calendar_missing",
                    message=f"No season calendar exists for season '{season}'.",
                )
            ]
            summary = SeasonCalendarValidationSummary(
                status="warnings",
                warning_count=1,
                event_count=0,
                categories={"count": 0, "values": []},
                tour_levels={"count": 0, "values": []},
                host_countries={"count": 0, "values": []},
            )
            return SeasonCalendarValidationResponse(
                season=season,
                calendar_exists=False,
                validation_summary=summary,
                issues=issues,
                read_only=True,
                message="No persisted season calendar was found to validate.",
            )

        calendar = result.calendar
        issues: list[SeasonCalendarValidationIssueV2] = []
        seen_event_ids: set[str] = set()
        duplicate_signature_counts: dict[tuple[int | None, str, str], int] = {}
        categories: dict[str, int] = {}
        tour_levels: dict[str, int] = {}
        host_countries: dict[str, int] = {}
        weeks: list[int] = []

        def add_issue(severity: str, code: str, message: str, *, event_id: str | None = None, field: str | None = None, context: dict[str, Any] | None = None) -> None:
            issues.append(SeasonCalendarValidationIssueV2(severity=severity, code=code, message=message, event_id=event_id, field=field, context=context or {}))

        if not calendar.events:
            add_issue("warning", "event_count_zero", "Calendar contains zero events.")

        for event in calendar.events:
            if not event.event_id.strip():
                add_issue("error", "event_id_missing", "event_id is required.", field="event_id")
            elif event.event_id in seen_event_ids:
                add_issue("error", "duplicate_event_id", f"Duplicate event_id '{event.event_id}'.", event_id=event.event_id, field="event_id")
            else:
                seen_event_ids.add(event.event_id)

            if not event.event_name.strip():
                add_issue("error", "event_name_missing", "event_name is required.", event_id=event.event_id, field="event_name")
            if not event.category.strip():
                add_issue("error", "category_missing", "category is required.", event_id=event.event_id, field="category")
            if event.tour_level is None:
                add_issue("error", "tour_level_missing", "tour_level is required.", event_id=event.event_id, field="tour_level")
            elif event.tour_level not in {"WORLD_TOUR", "ELITE_TOUR"}:
                add_issue("warning", "tour_level_unknown", f"tour_level '{event.tour_level}' is outside known set.", event_id=event.event_id, field="tour_level")

            if not (1 <= event.season_week <= TOTAL_SEASON_WEEKS):
                add_issue("error", "season_week_out_of_range", "season_week must be between 1 and 61.", event_id=event.event_id, field="season_week")
            if event.end_season_week is None or not (1 <= event.end_season_week <= TOTAL_SEASON_WEEKS):
                add_issue("error", "end_season_week_out_of_range", "end_season_week must be between 1 and 61.", event_id=event.event_id, field="end_season_week")
            if event.end_season_week is not None and event.season_week > event.end_season_week:
                add_issue("error", "season_week_after_end_week", "season_week cannot be after end_season_week.", event_id=event.event_id, field="season_week")

            if event.duration_in_season_weeks <= 0:
                add_issue("error", "duration_invalid", "duration_in_season_weeks must be greater than 0.", event_id=event.event_id, field="duration_in_season_weeks")
            elif event.duration_in_season_weeks > 3:
                add_issue("warning", "duration_unusually_long", "duration_in_season_weeks is unusually long (>3).", event_id=event.event_id, field="duration_in_season_weeks")
            if event.end_season_week is not None and event.season_week >= 1 and event.end_season_week - event.season_week >= 3:
                add_issue("warning", "event_spans_many_weeks", "Event spans many season weeks.", event_id=event.event_id, field="end_season_week")

            if event.main_draw_size <= 0:
                add_issue("error", "main_draw_size_invalid", "main_draw_size must be greater than 0.", event_id=event.event_id, field="main_draw_size")
            if event.qualification_draw_size < 0:
                add_issue("error", "qualification_draw_size_invalid", "qualification_draw_size cannot be negative.", event_id=event.event_id, field="qualification_draw_size")
            if event.prize_money < 0:
                add_issue("error", "prize_money_negative", "prize_money cannot be negative.", event_id=event.event_id, field="prize_money")
            if event.prestige < 0:
                add_issue("error", "prestige_negative", "prestige cannot be negative.", event_id=event.event_id, field="prestige")

            signature = (event.season_week, event.category.strip().upper(), event.event_name.strip().upper())
            duplicate_signature_counts[signature] = duplicate_signature_counts.get(signature, 0) + 1

            category_key = event.category.strip() or ""
            if category_key:
                categories[category_key] = categories.get(category_key, 0) + 1
            tour_key = str(event.tour_level) if event.tour_level else ""
            if tour_key:
                tour_levels[tour_key] = tour_levels.get(tour_key, 0) + 1
            country_key = event.host_country.strip() if event.host_country else ""
            if country_key:
                host_countries[country_key] = host_countries.get(country_key, 0) + 1
            weeks.append(event.season_week)

        for (week, category, name), count in sorted(duplicate_signature_counts.items()):
            if count > 1:
                add_issue("warning", "duplicate_week_category_event_name", "Multiple events share the same season_week + category + event_name.", field="season_week", context={"season_week": week, "category": category, "event_name": name, "count": count})

        event_count = len(calendar.events)
        first_week = min(weeks) if weeks else None
        last_week = max(weeks) if weeks else None

        world_tour_events = sum(1 for event in calendar.events if event.tour_level == "WORLD_TOUR")
        qualification_events = sum(1 for event in calendar.events if event.qualification_draw_size > 0)
        add_issue("info", "event_count", f"Calendar has {event_count} events.", context={"event_count": event_count})
        add_issue("info", "first_last_weeks", "Computed first/last season week.", context={"first_season_week": first_week, "last_season_week": last_week})
        add_issue("info", "world_tour_events", "Computed World Tour event count.", context={"world_tour_events": world_tour_events})
        add_issue("info", "qualification_events", "Computed qualification event count.", context={"qualification_events": qualification_events})

        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        info_count = sum(1 for issue in issues if issue.severity == "info")
        status = "errors" if error_count > 0 else ("warnings" if warning_count > 0 else "clean")

        summary = SeasonCalendarValidationSummary(
            status=status,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            event_count=event_count,
            first_season_week=first_week,
            last_season_week=last_week,
            categories={"count": len(categories), "values": sorted(categories), "counts": dict(sorted(categories.items()))},
            tour_levels={"count": len(tour_levels), "values": sorted(tour_levels), "counts": dict(sorted(tour_levels.items())), "world_tour_events": world_tour_events},
            host_countries={"count": len(host_countries), "values": sorted(host_countries), "counts": dict(sorted(host_countries.items())), "qualification_events": qualification_events},
        )
        return SeasonCalendarValidationResponse(
            season=season,
            calendar_exists=True,
            validation_summary=summary,
            issues=issues,
            read_only=True,
            message="Persisted season calendar validation completed.",
        )

    def validate_calendar_events(
        self,
        events: list[SeasonCalendarEvent],
        *,
        skipped_inactive_count: int = 0,
    ) -> tuple[list[SeasonCalendarValidationIssue], list[SeasonCalendarValidationIssue]]:
        warnings: list[SeasonCalendarValidationIssue] = []
        errors: list[SeasonCalendarValidationIssue] = []
        if not events:
            errors.append(self._issue("error", "no_events", "season calendar must contain at least one event"))
        seen: set[str] = set()
        counts_by_week: dict[int, int] = {}
        for event in events:
            if event.event_id in seen:
                errors.append(self._issue("error", "duplicate_event_id", f"duplicate event_id '{event.event_id}'", event_id=event.event_id, field="event_id"))
            seen.add(event.event_id)
            counts_by_week[event.season_week] = counts_by_week.get(event.season_week, 0) + 1
            if not 1 <= event.season_week <= TOTAL_SEASON_WEEKS:
                errors.append(self._issue("error", "season_week_out_of_range", "season_week must be between 1 and 61", event_id=event.event_id, field="season_week"))
            if event.end_season_week is None or event.end_season_week > TOTAL_SEASON_WEEKS:
                errors.append(self._issue("error", "end_season_week_out_of_range", "end_season_week must be between 1 and 61", event_id=event.event_id, field="end_season_week"))
            if event.duration_in_season_weeks < 1:
                errors.append(self._issue("error", "duration_invalid", "duration_in_season_weeks must be at least 1", event_id=event.event_id, field="duration_in_season_weeks"))
            if not event.template_id:
                errors.append(self._issue("error", "template_id_missing", "template_id is required", event_id=event.event_id, field="template_id"))
            if event.main_draw_size <= 0:
                errors.append(self._issue("error", "main_draw_size_invalid", "main_draw_size must be greater than 0", event_id=event.event_id, field="main_draw_size"))
            for field in ("seeds_count", "qualifier_spots", "wild_cards", "byes"):
                value = int(getattr(event, field))
                if value > event.main_draw_size:
                    errors.append(self._issue("error", f"{field}_exceeds_main_draw", f"{field} cannot exceed main_draw_size", event_id=event.event_id, field=field))
            if event.calendar_year is None:
                errors.append(self._issue("error", "calendar_year_missing", "calendar_year is required", event_id=event.event_id, field="calendar_year"))
            if event.year_week is None or not 1 <= event.year_week <= 61:
                errors.append(self._issue("error", "year_week_out_of_range", "year_week must be between 1 and 61", event_id=event.event_id, field="year_week"))
            if event.end_season_week and event.end_season_week > TOTAL_SEASON_WEEKS:
                warnings.append(self._issue("warning", "duration_overlaps_season_end", "event duration overlaps season end", event_id=event.event_id, field="duration_in_season_weeks"))
        for week, count in sorted(counts_by_week.items()):
            if count > 3:
                warnings.append(self._issue("warning", "too_many_parallel_events", f"season_week {week} has more than 3 events"))
        if len(events) > 200:
            warnings.append(self._issue("warning", "very_large_event_count", "calendar has a very large event count"))
        if not any(event.tour_level == "WORLD_TOUR" for event in events):
            warnings.append(self._issue("warning", "no_world_tour_events", "calendar has no World Tour events"))
        if not any(event.tour_level == "ELITE_TOUR" for event in events):
            warnings.append(self._issue("warning", "no_elite_tour_events", "calendar has no Elite Tour events"))
        if events and not any(1 <= event.season_week <= 4 for event in events):
            warnings.append(self._issue("warning", "no_events_first_4_weeks", "calendar has no events in the first 4 season weeks"))
        if events and not any(58 <= event.season_week <= 61 for event in events):
            warnings.append(self._issue("warning", "no_events_final_4_weeks", "calendar has no events in the final 4 season weeks"))
        if skipped_inactive_count:
            warnings.append(self._issue("warning", "inactive_templates_skipped", f"{skipped_inactive_count} inactive template(s) skipped"))
        warnings.append(self._issue("warning", "ranking_race_not_integrated", "ranking/race integration not implemented yet"))
        return warnings, errors

    def _registry_load_error_response(self, *, season: str, code: str, exception_type: str) -> SeasonCalendarValidationResponse:
        issue = SeasonCalendarValidationIssueV2(
            severity="error",
            code=code,
            message="Persisted season calendar registry could not be parsed for validation.",
            context={"exception_type": exception_type},
        )
        summary = SeasonCalendarValidationSummary(
            status="errors",
            error_count=1,
            event_count=0,
            categories={"count": 0, "values": []},
            tour_levels={"count": 0, "values": []},
            host_countries={"count": 0, "values": []},
        )
        return SeasonCalendarValidationResponse(
            season=season,
            calendar_exists=False,
            validation_summary=summary,
            issues=[issue],
            read_only=True,
            message="Persisted season calendar registry could not be parsed for validation.",
        )

    def _build_events(
        self,
        *,
        season: str,
        templates: list[TournamentTemplate],
        seed: int,
        season_start_calendar_year: int,
        season_start_year_week: int,
    ) -> list[SeasonCalendarEvent]:
        if not templates:
            return []
        event_count = len(templates)
        step = max(1, TOTAL_SEASON_WEEKS // event_count)
        offset = seed % step if step > 1 else 0
        events: list[SeasonCalendarEvent] = []
        season_start_year = self._season_start_year(season, fallback=season_start_calendar_year)
        try:
            configured_points = load_points_config(Path("config/points/mvp_points.json"))
        except (OSError, ValueError, json.JSONDecodeError):
            configured_points = {}
        for index, template in enumerate(templates):
            base_week = 1 + offset + index * step
            season_week = ((base_week - 1) % TOTAL_SEASON_WEEKS) + 1
            duration = max(1, template.duration_in_season_weeks)
            if season_week + duration - 1 > TOTAL_SEASON_WEEKS:
                season_week = max(1, TOTAL_SEASON_WEEKS - duration + 1)
            position = season_week_to_calendar_position(
                season=season,
                season_week=season_week,
                season_start_year_week=season_start_year_week,
            )
            calendar_year, year_week = position.calendar_year, position.year_week
            template_payload = self._template_payload(template)
            template_fingerprint = self._fingerprint(template_payload)
            authored_points = template.point_distribution.model_dump(mode="json", exclude_unset=True) if template.point_distribution else configured_points.get(template.point_distribution_ref or "", {})
            edition_points = {{"winner": "champion", "semifinalist": "semifinal", "quarterfinalist": "quarterfinal"}.get(key, key): value for key, value in authored_points.items()}
            event_id = f"EVT-{season_start_year}-W{season_week:02d}-{template.template_id}"
            events.append(
                SeasonCalendarEvent(
                    event_id=event_id,
                    season=season,
                    season_week=season_week,
                    calendar_year=calendar_year,
                    year_week=year_week,
                    template_id=template.template_id,
                    event_name=template.event_name,
                    category=template.category,
                    tour_level=template.tour_level,
                    host_country=template.host_country,
                    host_city=None,
                    region=template.region,
                    duration_in_season_weeks=duration,
                    start_season_week=season_week,
                    end_season_week=season_week + duration - 1,
                    status="planned",
                    main_draw_size=template.main_draw_size,
                    qualification_draw_size=template.qualification_draw_size,
                    seeds_count=template.seeds_count,
                    qualifier_spots=template.qualifier_spots,
                    wild_cards=template.wild_cards,
                    byes=template.byes,
                    point_distribution_ref=template.point_distribution_ref,
                    point_distribution=template.point_distribution,
                    ranking_status="ranked",
                    ranking_points_table=edition_points,
                    ranking_configuration_legacy=False,
                    prize_money=template.prize_money,
                    prestige=template.prestige,
                    event_level_overrides={},
                    source_template_fingerprint=template_fingerprint,
                    template_snapshot_fingerprint=template_fingerprint,
                    template_snapshot=template_payload,
                    cluster_id=template.seasonal_grouping or "default",
                    travel_group=template.region,
                )
            )
        return sorted(events, key=lambda event: (event.season_week, event.tour_level or "", event.template_id))

    def _summary(self, calendar: SeasonCalendar, *, persisted: bool, calendar_exists: bool) -> SeasonCalendarBuildSummary:
        weeks = sorted({event.season_week for event in calendar.events})
        return SeasonCalendarBuildSummary(
            event_count=len(calendar.events),
            season_weeks_used=len(weeks),
            first_event_week=weeks[0] if weeks else None,
            last_event_week=weeks[-1] if weeks else None,
            world_tour_events=sum(1 for event in calendar.events if event.tour_level == "WORLD_TOUR"),
            elite_tour_events=sum(1 for event in calendar.events if event.tour_level == "ELITE_TOUR"),
            validation_warning_count=len(calendar.validation_warnings),
            validation_error_count=len(calendar.validation_errors),
            persisted=persisted,
            calendar_exists=calendar_exists,
        )

    def _load_registry(self) -> SeasonCalendarRegistry:
        if not self.calendar_registry_path.exists():
            return SeasonCalendarRegistry()
        return SeasonCalendarRegistry.model_validate(json.loads(self.calendar_registry_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonCalendarRegistry) -> None:
        self.calendar_registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.calendar_registry_path.with_suffix(f"{self.calendar_registry_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.calendar_registry_path)

    @staticmethod
    def _template_sort_key(template: TournamentTemplate) -> tuple[str, float, str, str]:
        return (template.tour_level, -template.prestige, template.category, template.template_id)

    @staticmethod
    def _template_payload(template: TournamentTemplate) -> dict[str, Any]:
        return template.model_dump(mode="json")

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _season_start_year(season: str, *, fallback: int) -> int:
        try:
            return parse_season_start_year(season)
        except ValueError:
            return fallback

    @staticmethod
    def _issue(severity: str, code: str, message: str, *, event_id: str | None = None, field: str | None = None) -> SeasonCalendarValidationIssue:
        return SeasonCalendarValidationIssue(severity=severity, code=code, message=message, event_id=event_id, field=field)
