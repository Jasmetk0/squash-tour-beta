"""Application service for deterministic season calendar construction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments.models import (
    SeasonCalendar,
    SeasonCalendarBuildRequest,
    SeasonCalendarBuildResult,
    SeasonCalendarBuildSummary,
    SeasonCalendarEvent,
    SeasonCalendarMetadata,
    SeasonCalendarValidationIssue,
    TournamentTemplate,
)

TOTAL_SEASON_WEEKS = 61


class SeasonCalendarRegistry(BaseModel):
    calendars_by_season: dict[str, SeasonCalendar] = Field(default_factory=dict)


def map_season_week_to_calendar_week(
    *,
    season: str,
    season_week: int,
    season_start_calendar_year: int = 2000,
    season_start_year_week: int = 35,
) -> tuple[int, int]:
    """Map internal season week to deterministic calendar year/week positioning."""

    if not 1 <= season_week <= TOTAL_SEASON_WEEKS:
        raise ValueError("season_week must be between 1 and 61")
    if not 1900 <= season_start_calendar_year <= 2100:
        raise ValueError("season_start_calendar_year must be between 1900 and 2100")
    if not 1 <= season_start_year_week <= 53:
        raise ValueError("season_start_year_week must be between 1 and 53")

    year = season_start_calendar_year
    week = season_start_year_week + season_week - 1
    while week > 52:
        week -= 52
        year += 1
    return year, week


@dataclass(slots=True)
class SeasonCalendarService:
    """Build, validate, read, and persist file-backed season calendars."""

    template_service: TournamentTemplatesConfigService
    calendar_registry_path: Path = Path("config/world/season_calendars.json")

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_registry_path, Path):
            self.calendar_registry_path = Path(self.calendar_registry_path)

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
            if event.year_week is None or not 1 <= event.year_week <= 53:
                errors.append(self._issue("error", "year_week_out_of_range", "year_week must be between 1 and 53", event_id=event.event_id, field="year_week"))
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
        for index, template in enumerate(templates):
            base_week = 1 + offset + index * step
            season_week = ((base_week - 1) % TOTAL_SEASON_WEEKS) + 1
            duration = max(1, template.duration_in_season_weeks)
            if season_week + duration - 1 > TOTAL_SEASON_WEEKS:
                season_week = max(1, TOTAL_SEASON_WEEKS - duration + 1)
            calendar_year, year_week = map_season_week_to_calendar_week(
                season=season,
                season_week=season_week,
                season_start_calendar_year=season_start_calendar_year,
                season_start_year_week=season_start_year_week,
            )
            template_payload = self._template_payload(template)
            template_fingerprint = self._fingerprint(template_payload)
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
            return int(str(season).split("/", maxsplit=1)[0])
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _issue(severity: str, code: str, message: str, *, event_id: str | None = None, field: str | None = None) -> SeasonCalendarValidationIssue:
        return SeasonCalendarValidationIssue(severity=severity, code=code, message=message, event_id=event_id, field=field)
