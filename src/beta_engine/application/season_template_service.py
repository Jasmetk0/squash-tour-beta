"""Read-only Season Template foundation service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import SeasonTemplateSlotValidationPreview


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


class SeasonTemplateSlotValidationSummary(BaseModel):
    status: Literal["clean", "warnings", "errors"]
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    slot_count: int = Field(ge=0)
    week_count: int | None = Field(default=None, ge=0, le=61)
    first_week: int | None = Field(default=None, ge=1, le=61)
    last_week: int | None = Field(default=None, ge=1, le=61)


class SeasonTemplateSlotValidationResponse(BaseModel):
    template_id: str
    template_exists: bool
    read_only: bool = True
    summary: SeasonTemplateSlotValidationSummary
    issues: list[SeasonTemplateValidationIssue] = Field(default_factory=list)
    message: str


class SeasonTemplateSlotConflict(BaseModel):
    severity: Literal["warning", "info"]
    code: str
    message: str
    season_week: int | None = Field(default=None, ge=1, le=61)
    slot_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    tour_levels: list[str] = Field(default_factory=list)
    host_countries: list[str] = Field(default_factory=list)
    read_only: bool = True


class SeasonTemplateSlotConflictSummary(BaseModel):
    status: Literal["clean", "warnings", "info"]
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    slot_count: int = Field(ge=0)
    occupied_week_count: int = Field(ge=0, le=61)
    busiest_week: int | None = Field(default=None, ge=1, le=61)
    busiest_week_slot_count: int | None = Field(default=None, ge=0)
    read_only: bool = True


class SeasonTemplateSlotConflictReportResponse(BaseModel):
    template_id: str
    template_exists: bool
    read_only: bool = True
    summary: SeasonTemplateSlotConflictSummary
    conflicts: list[SeasonTemplateSlotConflict] = Field(default_factory=list)
    message: str

class SeasonTemplateSlotConflictCodeMetadata(BaseModel):
    code: str
    severity: Literal["warning", "info"]
    title: str
    description: str
    read_only: bool = True


class SeasonTemplateSlotConflictCodeRegistryResponse(BaseModel):
    codes: list[SeasonTemplateSlotConflictCodeMetadata] = Field(default_factory=list)
    code_count: int = Field(ge=0)
    read_only: bool = True
    message: str


@dataclass(slots=True)
class _TemplateValidationIssueSummary:
    status: Literal["clean", "warnings", "errors"]
    error_count: int
    warning_count: int
    issue_count: int
    issue_codes: list[str]
    error_codes: list[str]
    warning_codes: list[str]


class SeasonTemplateSlotValidationIssueCodeMetadata(BaseModel):
    code: str
    severity: Literal["warning", "error"]
    title: str
    description: str
    field: str | None = None
    read_only: bool = True


class SeasonTemplateSlotValidationIssueCodeRegistryResponse(BaseModel):
    codes: list[SeasonTemplateSlotValidationIssueCodeMetadata] = Field(default_factory=list)
    code_count: int = Field(ge=0)
    read_only: bool = True
    message: str


SEASON_TEMPLATE_SLOT_VALIDATION_ISSUE_CODES = (
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_not_found", severity="error", title="Template not found", description="Requested season template ID was not found in read-only template previews.", field="template_id"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_event_name_missing", severity="error", title="Template slot event name missing", description="Template slot is missing event_name or tournament_name.", field="event_name"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_category_missing", severity="error", title="Template slot category missing", description="Template slot is missing a category value.", field="category"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_tour_level_missing", severity="error", title="Template slot tour level missing", description="Source template tour_level is missing for this slot.", field="tour_level"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_week_out_of_range", severity="error", title="Template slot week out of range", description="Template slot week value is outside SW1-SW61 bounds.", field="season_week_start"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_start_after_end", severity="error", title="Template slot start after end", description="Template slot season_week_start is greater than season_week_end.", field="season_week_start"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_duration_invalid", severity="error", title="Template slot duration invalid", description="Template slot duration_in_season_weeks must be greater than 0.", field="duration_in_season_weeks"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_main_draw_size_invalid", severity="error", title="Template slot main draw size invalid", description="Source template main_draw_size must be greater than 0.", field="main_draw_size"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_qualification_draw_size_invalid", severity="error", title="Template slot qualification draw size invalid", description="Source template qualification_draw_size cannot be negative.", field="qualification_draw_size"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_duration_long", severity="warning", title="Template slot duration long", description="Template slot duration is unusually long.", field="duration_in_season_weeks"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_duplicate_week_category_event_name", severity="warning", title="Template slot duplicate week/category/event", description="Multiple slots share the same start week, category, and event name.", field=None),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_week_overloaded", severity="warning", title="Template slot week overloaded", description="A season week contains more than four template slots.", field="season_week_start"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_category_tour_level_week_overloaded", severity="warning", title="Template slot category/tour-level week overloaded", description="A week contains multiple slots for the same category and tour level.", field="season_week_start"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_world_tour_missing", severity="warning", title="Template slot world tour missing", description="Default MSA preview has no WORLD_TOUR slots.", field="tour_level"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_early_weeks_empty", severity="warning", title="Template slot early weeks empty", description="Template has no events in the first four season weeks.", field="season_week_start"),
    SeasonTemplateSlotValidationIssueCodeMetadata(code="template_slot_final_weeks_empty", severity="warning", title="Template slot final weeks empty", description="Template has no events in the final four season weeks.", field="season_week_end"),
)


SEASON_TEMPLATE_SLOT_CONFLICT_CODES = (
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_template_not_found", severity="warning", title="Template not found", description="Requested season template ID was not found in read-only template previews."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_week_overloaded", severity="warning", title="Week overloaded", description="A season week has many overlapping template slots."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_premium_overlap", severity="warning", title="Premium overlap", description="Premium-category slots overlap in the same season week."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_category_tour_level_overlap", severity="warning", title="Category/tour-level overlap", description="Multiple slots share the same category and tour level in one week."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_long_continuous_cluster", severity="info", title="Long continuous cluster", description="Occupied weeks form a long uninterrupted cluster."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_opening_dead_zone", severity="info", title="Opening dead zone", description="No slots are scheduled during opening season weeks 1-4."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_final_dead_zone", severity="info", title="Final dead zone", description="No slots are scheduled during final season weeks 58-61."),
    SeasonTemplateSlotConflictCodeMetadata(code="template_conflict_host_country_cluster", severity="info", title="Host-country cluster", description="The same host country appears repeatedly within a short week window."),
)

_CONFLICT_WEEK_OVERLOAD_THRESHOLD = 4
_CONFLICT_LONG_CLUSTER_THRESHOLD = 4
_CONFLICT_COUNTRY_CLUSTER_COUNT = 3
_CONFLICT_COUNTRY_CLUSTER_WINDOW = 4
_PREMIUM_CATEGORIES = {"DIAMOND", "EMERALD", "PLATINUM", "WORLD_CHAMPIONSHIP", "WORLD_TOUR_FINALS"}


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

    def list_slot_validation_issue_codes(self) -> SeasonTemplateSlotValidationIssueCodeRegistryResponse:
        codes = sorted(SEASON_TEMPLATE_SLOT_VALIDATION_ISSUE_CODES, key=lambda item: item.code)
        return SeasonTemplateSlotValidationIssueCodeRegistryResponse(
            codes=list(codes),
            code_count=len(codes),
            message="Stable read-only season template slot validation issue code registry.",
        )

    def list_slot_conflict_codes(self) -> SeasonTemplateSlotConflictCodeRegistryResponse:
        codes = sorted(SEASON_TEMPLATE_SLOT_CONFLICT_CODES, key=lambda item: item.code)
        return SeasonTemplateSlotConflictCodeRegistryResponse(
            codes=list(codes),
            code_count=len(codes),
            message="Stable read-only season template slot conflict code registry.",
        )

    def _slot_stable_id(self, slot: SeasonTemplateSlot, index: int) -> str:
        return slot.slot_id or f"slot_{index}"

    def _slot_source_template(self, slot: SeasonTemplateSlot, source_by_id: dict[str, Any]) -> Any | None:
        return source_by_id.get(slot.source_template_id or "")

    def _slot_tour_level(self, slot: SeasonTemplateSlot, source_by_id: dict[str, Any]) -> str:
        source = self._slot_source_template(slot, source_by_id)
        return ((source.tour_level if source else "") or "").strip()

    def _slot_category(self, slot: SeasonTemplateSlot) -> str:
        return (slot.category or "").strip()

    def _slot_host_country(self, slot: SeasonTemplateSlot) -> str:
        return (slot.host_country or "").strip()

    def _slot_weeks(self, slot: SeasonTemplateSlot) -> list[int]:
        return [week for week in range(slot.season_week_start, slot.season_week_end + 1) if 1 <= week <= 61]

    def _conflict_sort_key(self, conflict: SeasonTemplateSlotConflict) -> tuple[int, int, str, str]:
        severity_order = {"warning": 0, "info": 1}
        return (
            severity_order[conflict.severity],
            conflict.season_week if conflict.season_week is not None else 99,
            conflict.code,
            conflict.message,
        )


    def _summarize_template_validation_issues(
        self,
        issues: list[SeasonTemplateValidationIssue],
    ) -> _TemplateValidationIssueSummary:
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_codes = sorted({issue.code for issue in issues if issue.severity == "error"})
        warning_codes = sorted({issue.code for issue in issues if issue.severity == "warning"})
        issue_codes = sorted({issue.code for issue in issues})
        status: Literal["clean", "warnings", "errors"] = "errors" if (error_count > 0 or error_codes) else ("warnings" if warning_count > 0 else "clean")
        return _TemplateValidationIssueSummary(
            status=status,
            error_count=error_count,
            warning_count=warning_count,
            issue_count=len(issues),
            issue_codes=issue_codes,
            error_codes=error_codes,
            warning_codes=warning_codes,
        )

    def build_slot_validation_preview(
        self,
        issues: list[SeasonTemplateValidationIssue],
        template_id: str,
        template_exists: bool = True,
    ) -> SeasonTemplateSlotValidationPreview | None:
        if not template_exists:
            return None
        issue_summary = self._summarize_template_validation_issues(issues)
        return SeasonTemplateSlotValidationPreview(
            template_id=template_id,
            template_exists=template_exists,
            status=issue_summary.status,
            error_count=issue_summary.error_count,
            warning_count=issue_summary.warning_count,
            issue_count=issue_summary.issue_count,
            issue_codes=issue_summary.issue_codes,
            error_codes=issue_summary.error_codes,
            warning_codes=issue_summary.warning_codes,
            read_only=True,
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

    def validate_template_by_id(self, template_id: str) -> SeasonTemplateSlotValidationResponse:
        templates_response = self.list_templates()
        selected = next((template for template in templates_response.templates if template.template_id == template_id), None)
        if selected is None:
            issues = [
                SeasonTemplateValidationIssue(
                    severity="error",
                    code="template_not_found",
                    message=f"Season template '{template_id}' was not found.",
                    slot_id=None,
                )
            ]
            return SeasonTemplateSlotValidationResponse(
                template_id=template_id,
                template_exists=False,
                summary=SeasonTemplateSlotValidationSummary(
                    status="errors",
                    error_count=1,
                    warning_count=0,
                    issue_count=1,
                    slot_count=0,
                    week_count=0,
                    first_week=None,
                    last_week=None,
                ),
                issues=issues,
                message="Template not found.",
            )

        issues = self.validate_template_slots(selected)
        issue_summary = self._summarize_template_validation_issues(issues)

        occupied_weeks: set[int] = set()
        for slot in selected.slots:
            occupied_weeks.update(range(slot.season_week_start, slot.season_week_end + 1))

        first_week = min((slot.season_week_start for slot in selected.slots), default=None)
        last_week = max((slot.season_week_end for slot in selected.slots), default=None)
        return SeasonTemplateSlotValidationResponse(
            template_id=template_id,
            template_exists=True,
            summary=SeasonTemplateSlotValidationSummary(
                status=issue_summary.status,
                error_count=issue_summary.error_count,
                warning_count=issue_summary.warning_count,
                issue_count=issue_summary.issue_count,
                slot_count=len(selected.slots),
                week_count=len(occupied_weeks),
                first_week=first_week,
                last_week=last_week,
            ),
            issues=issues,
            message="Template slot validation completed.",
        )

    def analyze_template_slot_conflicts(self, template_id: str) -> SeasonTemplateSlotConflictReportResponse:
        templates_response = self.list_templates()
        selected = next((template for template in templates_response.templates if template.template_id == template_id), None)
        if selected is None:
            conflicts = [SeasonTemplateSlotConflict(severity="warning", code="template_conflict_template_not_found", message="Template not found.")]
            return SeasonTemplateSlotConflictReportResponse(
                template_id=template_id,
                template_exists=False,
                summary=SeasonTemplateSlotConflictSummary(
                    status="warnings",
                    warning_count=1,
                    info_count=0,
                    conflict_count=1,
                    slot_count=0,
                    occupied_week_count=0,
                    busiest_week=None,
                    busiest_week_slot_count=None,
                ),
                conflicts=conflicts,
                message="Template not found.",
            )

        slot_ids_by_index = [self._slot_stable_id(slot, index) for index, slot in enumerate(selected.slots, start=1)]
        config = self.template_service.get_config()
        source_by_id = {item.template_id: item for item in config.templates}
        conflicts: list[SeasonTemplateSlotConflict] = []
        week_to_slot_indexes: dict[int, list[int]] = {}
        occupied_weeks: set[int] = set()
        week_category_tour: dict[tuple[int, str, str], list[int]] = {}
        week_premium_slot_indexes: dict[int, list[int]] = {}

        for index, slot in enumerate(selected.slots):
            tour_level = self._slot_tour_level(slot, source_by_id)
            category = self._slot_category(slot)
            normalized_category = category.upper()
            for week in self._slot_weeks(slot):
                occupied_weeks.add(week)
                week_to_slot_indexes.setdefault(week, []).append(index)
                category_key = (week, category.lower(), str(tour_level).lower())
                week_category_tour.setdefault(category_key, []).append(index)
                if normalized_category in _PREMIUM_CATEGORIES:
                    week_premium_slot_indexes.setdefault(week, []).append(index)

        for week in sorted(week_to_slot_indexes):
            slot_indexes = week_to_slot_indexes[week]
            if len(slot_indexes) >= _CONFLICT_WEEK_OVERLOAD_THRESHOLD:
                conflicts.append(SeasonTemplateSlotConflict(severity="warning", code="template_conflict_week_overloaded", message=f"Season week {week} has {len(slot_indexes)} template slots.", season_week=week, slot_ids=sorted(slot_ids_by_index[i] for i in slot_indexes)))

        for week in sorted(week_premium_slot_indexes):
            slot_indexes = week_premium_slot_indexes[week]
            if len(slot_indexes) > 1:
                categories = sorted({self._slot_category(selected.slots[i]) for i in slot_indexes if self._slot_category(selected.slots[i])})
                tour_levels = sorted({self._slot_tour_level(selected.slots[i], source_by_id) for i in slot_indexes if self._slot_tour_level(selected.slots[i], source_by_id)})
                conflicts.append(SeasonTemplateSlotConflict(severity="warning", code="template_conflict_premium_overlap", message=f"Season week {week} has overlapping premium-category template slots.", season_week=week, slot_ids=sorted(slot_ids_by_index[i] for i in slot_indexes), categories=categories, tour_levels=tour_levels))

        for (week, category, tour_level), slot_indexes in sorted(week_category_tour.items()):
            if len(slot_indexes) >= 2 and (category or tour_level):
                conflicts.append(SeasonTemplateSlotConflict(severity="warning", code="template_conflict_category_tour_level_overlap", message=f"Season week {week} has {len(slot_indexes)} slots for category '{category or 'unknown'}' and tour level '{tour_level or 'unknown'}'.", season_week=week, slot_ids=sorted(slot_ids_by_index[i] for i in slot_indexes), categories=sorted({self._slot_category(selected.slots[i]) for i in slot_indexes if self._slot_category(selected.slots[i])}), tour_levels=sorted({self._slot_tour_level(selected.slots[i], source_by_id) for i in slot_indexes if self._slot_tour_level(selected.slots[i], source_by_id)})))

        sorted_occupied_weeks = sorted(occupied_weeks)
        cluster_start = 0
        while cluster_start < len(sorted_occupied_weeks):
            cluster_end = cluster_start
            while cluster_end + 1 < len(sorted_occupied_weeks) and sorted_occupied_weeks[cluster_end + 1] == sorted_occupied_weeks[cluster_end] + 1:
                cluster_end += 1
            cluster_weeks = sorted_occupied_weeks[cluster_start:cluster_end + 1]
            if len(cluster_weeks) >= _CONFLICT_LONG_CLUSTER_THRESHOLD:
                conflicts.append(SeasonTemplateSlotConflict(severity="info", code="template_conflict_long_continuous_cluster", message=f"Continuous occupied week cluster from {cluster_weeks[0]} to {cluster_weeks[-1]} ({len(cluster_weeks)} weeks).", season_week=cluster_weeks[0]))
            cluster_start = cluster_end + 1

        if not any(week in occupied_weeks for week in range(1, 5)):
            conflicts.append(SeasonTemplateSlotConflict(severity="info", code="template_conflict_opening_dead_zone", message="No template slots are scheduled in season weeks 1-4.", season_week=1))
        if not any(week in occupied_weeks for week in range(58, 62)):
            conflicts.append(SeasonTemplateSlotConflict(severity="info", code="template_conflict_final_dead_zone", message="No template slots are scheduled in season weeks 58-61.", season_week=58))

        for window_start in range(1, 61 - _CONFLICT_COUNTRY_CLUSTER_WINDOW + 2):
            window_end = window_start + _CONFLICT_COUNTRY_CLUSTER_WINDOW - 1
            by_country: dict[str, set[int]] = {}
            for week in range(window_start, window_end + 1):
                for slot_index in week_to_slot_indexes.get(week, []):
                    country = self._slot_host_country(selected.slots[slot_index])
                    if country:
                        by_country.setdefault(country, set()).add(slot_index)
            for country, slot_indexes in sorted(by_country.items()):
                if len(slot_indexes) >= _CONFLICT_COUNTRY_CLUSTER_COUNT:
                    slot_ids = sorted(slot_ids_by_index[i] for i in slot_indexes)
                    if not any(c.code == "template_conflict_host_country_cluster" and c.host_countries == [country] and c.slot_ids == slot_ids and c.season_week == window_start for c in conflicts):
                        conflicts.append(SeasonTemplateSlotConflict(severity="info", code="template_conflict_host_country_cluster", message=f"Host country '{country}' appears in {len(slot_ids)} slots within weeks {window_start}-{window_end}.", season_week=window_start, slot_ids=slot_ids, host_countries=[country]))

        conflicts.sort(key=self._conflict_sort_key)

        warning_count = sum(1 for conflict in conflicts if conflict.severity == "warning")
        info_count = sum(1 for conflict in conflicts if conflict.severity == "info")
        status: Literal["clean", "warnings", "info"] = "warnings" if warning_count > 0 else ("info" if info_count > 0 else "clean")
        busiest_week = None
        busiest_week_slot_count = None
        if week_to_slot_indexes:
            busiest_week, busiest_slots = max(sorted(week_to_slot_indexes.items()), key=lambda item: (len(item[1]), -item[0]))
            busiest_week_slot_count = len(busiest_slots)

        return SeasonTemplateSlotConflictReportResponse(
            template_id=template_id,
            template_exists=True,
            summary=SeasonTemplateSlotConflictSummary(
                status=status,
                warning_count=warning_count,
                info_count=info_count,
                conflict_count=len(conflicts),
                slot_count=len(selected.slots),
                occupied_week_count=len(occupied_weeks),
                busiest_week=busiest_week,
                busiest_week_slot_count=busiest_week_slot_count,
            ),
            conflicts=conflicts,
            message="Template slot conflict analysis completed.",
        )
