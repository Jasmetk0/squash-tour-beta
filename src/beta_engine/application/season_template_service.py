"""Read-only Season Template foundation service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService


class SeasonTemplateSlot(BaseModel):
    slot_id: str
    season_week_start: int = Field(ge=1, le=61)
    season_week_end: int = Field(ge=1, le=61)
    duration_weeks: int = Field(ge=1)
    tournament_name: str
    category: str
    host_country: str | None = None
    region: str | None = None
    has_qualification: bool
    qualifying_week_start: int | None = Field(default=None, ge=1, le=61)
    main_draw_week_start: int | None = Field(default=None, ge=1, le=61)
    source_template_id: str | None = None
    notes: str | None = None


class SeasonTemplateSummary(BaseModel):
    template_id: str
    name: str
    description: str
    season_count_supported: int | None = None
    week_count: int = 61
    slot_count: int = Field(ge=0)
    source: str
    status: str = "read_only_foundation"
    slots: list[SeasonTemplateSlot] = Field(default_factory=list)


class SeasonTemplatesResponse(BaseModel):
    templates: list[SeasonTemplateSummary] = Field(default_factory=list)
    source_path: str | None = None
    status: str


class SeasonTemplateValidationIssue(BaseModel):
    severity: Literal["warning", "error"]
    code: str
    message: str
    slot_id: str | None = None


@dataclass(slots=True)
class SeasonTemplateService:
    template_service: TournamentTemplatesConfigService

    def list_templates(self) -> SeasonTemplatesResponse:
        templates_config = self.template_service.get_config()
        source_path = str(self.template_service.config_path)
        ordered = sorted(templates_config.templates, key=lambda item: item.template_id)

        slots: list[SeasonTemplateSlot] = []
        for index, template in enumerate(ordered, start=1):
            season_week_start = min(index, 61)
            duration = max(1, template.duration_in_season_weeks)
            season_week_end = min(61, season_week_start + duration - 1)
            has_qualification = template.qualification_draw_size > 0
            slots.append(
                SeasonTemplateSlot(
                    slot_id=f"slot-{index:02d}-{template.template_id}",
                    season_week_start=season_week_start,
                    season_week_end=season_week_end,
                    duration_weeks=duration,
                    tournament_name=template.event_name,
                    category=template.category,
                    host_country=template.host_country,
                    region=template.region,
                    has_qualification=has_qualification,
                    qualifying_week_start=season_week_start if has_qualification else None,
                    main_draw_week_start=season_week_start,
                    source_template_id=template.template_id,
                    notes="Derived preview from tournament_templates config.",
                )
            )

        summary = SeasonTemplateSummary(
            template_id="default_msa_template_preview",
            name="Default MSA Template Preview",
            description="Read-only derived preview built from current tournament templates config.",
            season_count_supported=40,
            slot_count=len(slots),
            source="derived_preview:tournament_templates",
            slots=slots,
        )
        return SeasonTemplatesResponse(
            templates=[summary],
            source_path=source_path,
            status="read_only_foundation",
        )

    def validate_template_slots(self, template: SeasonTemplateSummary) -> list[SeasonTemplateValidationIssue]:
        issues: list[SeasonTemplateValidationIssue] = []
        world_tour_slot_count = 0
        week_counts: dict[int, int] = {}
        category_tour_week: dict[tuple[int, str, str], int] = {}
        duplicate_signature: dict[tuple[int, str, str], int] = {}
        occupied_weeks: set[int] = set()

        config = self.template_service.get_config()
        source_by_id = {item.template_id: item for item in config.templates}

        for slot in template.slots:
            source = source_by_id.get(slot.source_template_id or "")
            category = (slot.category or "").strip()
            event_name = (slot.tournament_name or "").strip()
            tour_level = (source.tour_level if source else "") or ""
            duration = source.duration_in_season_weeks if source else slot.duration_weeks

            if not event_name:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_event_name_missing", message="Template slot is missing event_name/tournament_name.", slot_id=slot.slot_id))
            if not category:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_category_missing", message="Template slot is missing category.", slot_id=slot.slot_id))
            if not str(tour_level).strip():
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_tour_level_missing", message="Template slot is missing tour_level in source template config.", slot_id=slot.slot_id))

            if not (1 <= slot.season_week_start <= 61):
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_week_out_of_range", message=f"season_week_start {slot.season_week_start} is outside 1..61.", slot_id=slot.slot_id))
            if not (1 <= slot.season_week_end <= 61):
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_week_out_of_range", message=f"season_week_end {slot.season_week_end} is outside 1..61.", slot_id=slot.slot_id))
            if slot.season_week_start > slot.season_week_end:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_start_after_end", message="season_week_start is greater than season_week_end.", slot_id=slot.slot_id))
            if duration <= 0:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_duration_invalid", message="duration_in_season_weeks must be > 0.", slot_id=slot.slot_id))
            if source is not None and source.main_draw_size <= 0:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_main_draw_size_invalid", message="main_draw_size must be > 0.", slot_id=slot.slot_id))
            if source is not None and source.qualification_draw_size < 0:
                issues.append(SeasonTemplateValidationIssue(severity="error", code="template_slot_qualification_draw_size_invalid", message="qualification_draw_size cannot be negative.", slot_id=slot.slot_id))

            if duration > 3:
                issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_duration_long", message=f"Template slot duration {duration} weeks is unusually long (>3).", slot_id=slot.slot_id))

            duplicate_key = (slot.season_week_start, category.lower(), event_name.lower())
            duplicate_signature[duplicate_key] = duplicate_signature.get(duplicate_key, 0) + 1

            if source and source.tour_level == "WORLD_TOUR":
                world_tour_slot_count += 1

            for week in range(slot.season_week_start, slot.season_week_end + 1):
                if 1 <= week <= 61:
                    occupied_weeks.add(week)
                    week_counts[week] = week_counts.get(week, 0) + 1
                    category_tour_key = (week, category.lower(), str(tour_level).lower())
                    category_tour_week[category_tour_key] = category_tour_week.get(category_tour_key, 0) + 1

        for (week, _category, _event_name), count in duplicate_signature.items():
            if count > 1:
                issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_duplicate_week_category_event_name", message=f"Duplicate slots share season_week_start/category/event_name in week {week}.", slot_id=None))

        for week, count in week_counts.items():
            if count > 4:
                issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_week_overloaded", message=f"Week {week} has {count} template slots (>4).", slot_id=None))

        for (week, category, tour_level), count in category_tour_week.items():
            if count > 1:
                issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_category_tour_level_week_overloaded", message=f"Week {week} has {count} slots for {category}/{tour_level}.", slot_id=None))

        if template.template_id.startswith("default_msa") and world_tour_slot_count == 0:
            issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_world_tour_missing", message="Template has no WORLD_TOUR slots.", slot_id=None))

        if len(template.slots) >= 12 and not any(week in occupied_weeks for week in range(1, 5)):
            issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_early_weeks_empty", message="Template has no events in first 4 season weeks.", slot_id=None))
        if len(template.slots) >= 12 and not any(week in occupied_weeks for week in range(58, 62)):
            issues.append(SeasonTemplateValidationIssue(severity="warning", code="template_slot_final_weeks_empty", message="Template has no events in final 4 season weeks.", slot_id=None))

        return issues
