from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.category_service import CategoryService
from beta_engine.application.season_registry_service import SeasonRegistryService, TOTAL_REGISTRY_SEASONS
from beta_engine.application.season_template_service import SeasonTemplateService
from beta_engine.application.tournament_master_service import TournamentMasterService

ValidationSeverity = Literal["ok", "info", "warning"]


class TourSeasonsValidationIssue(BaseModel):
    issue_id: str
    severity: ValidationSeverity
    area: str
    item_id: str | None = None
    item_name: str | None = None
    message: str
    link_hint: str | None = None


class TourSeasonsValidationSection(BaseModel):
    section_id: str
    title: str
    issues: list[TourSeasonsValidationIssue] = Field(default_factory=list)


class TourSeasonsValidationSummary(BaseModel):
    total_checks: int
    warning_count: int
    info_count: int
    ok_count: int
    registry_loaded: bool
    category_count: int
    tournament_count: int
    season_template_count: int
    season_template_slot_count: int


class TourSeasonsValidationResponse(BaseModel):
    status: Literal["read_only_foundation"]
    summary: TourSeasonsValidationSummary
    sections: list[TourSeasonsValidationSection]
    planned_future: list[str]


@dataclass(slots=True)
class TourSeasonsValidationService:
    registry_service: SeasonRegistryService
    category_service: CategoryService
    tournament_service: TournamentMasterService
    season_template_service: SeasonTemplateService

    def validate(self) -> TourSeasonsValidationResponse:
        registry = self.registry_service.build_registry()
        categories = self.category_service.list_categories().categories
        tournaments = self.tournament_service.list_tournaments().tournaments
        templates = self.season_template_service.list_templates().templates

        registry_issues: list[TourSeasonsValidationIssue] = [
            self._issue("registry-season-count", "ok" if registry.season_count == TOTAL_REGISTRY_SEASONS else "warning", "registry", f"season_count is {registry.season_count} (expected {TOTAL_REGISTRY_SEASONS}).", link_hint="/admin/tour-seasons/season-registry"),
            self._issue("registry-week-count", "ok" if registry.week_count == 61 else "warning", "registry", f"week_count is {registry.week_count} (expected 61).", link_hint="/admin/tour-seasons/season-registry"),
            self._issue("registry-season-week-1", "ok" if registry.season_week_1_year_week == 37 else "warning", "registry", f"season_week_1_year_week is {registry.season_week_1_year_week} (expected 37).", link_hint="/admin/tour-seasons/season-registry"),
        ]

        category_issues: list[TourSeasonsValidationIssue] = []
        for category in categories:
            if category.notes:
                category_issues.append(self._issue(f"category-notes-{category.category_id}", "warning", "category", f"Notes present: {'; '.join(category.notes)}", category.category_id, category.name, f"/admin/tour-seasons/categories/{category.category_id}"))
            if category.main_draw_size is None:
                category_issues.append(self._issue(f"category-main-draw-size-{category.category_id}", "info", "category", "Main draw mixed or unavailable.", category.category_id, category.name, f"/admin/tour-seasons/categories/{category.category_id}"))
            if category.qualification_draw_size is None:
                category_issues.append(self._issue(f"category-qualification-draw-size-{category.category_id}", "info", "category", "Qualification draw mixed or unavailable.", category.category_id, category.name, f"/admin/tour-seasons/categories/{category.category_id}"))
            if category.schedule_footprint_weeks is None:
                category_issues.append(self._issue(f"category-schedule-footprint-{category.category_id}", "info", "category", "Schedule footprint weeks mixed or unavailable.", category.category_id, category.name, f"/admin/tour-seasons/categories/{category.category_id}"))
            if not category.source_template_ids:
                category_issues.append(self._issue(f"category-source-template-ids-{category.category_id}", "warning", "category", "No source template IDs linked.", category.category_id, category.name, f"/admin/tour-seasons/categories/{category.category_id}"))
        if not category_issues:
            category_issues.append(self._issue("category-no-issues", "ok", "category", "No issues detected from current read-only checks.", link_hint="/admin/tour-seasons/categories"))

        tournament_issues: list[TourSeasonsValidationIssue] = []
        for tournament in tournaments:
            if tournament.notes:
                tournament_issues.append(self._issue(f"tournament-notes-{tournament.tournament_id}", "warning", "tournament", f"Notes present: {'; '.join(tournament.notes)}", tournament.tournament_id, tournament.name, f"/admin/tour-seasons/tournaments/{tournament.tournament_id}"))
            if tournament.default_category is None:
                tournament_issues.append(self._issue(f"tournament-default-category-{tournament.tournament_id}", "info", "tournament", "Mixed category in source templates.", tournament.tournament_id, tournament.name, f"/admin/tour-seasons/tournaments/{tournament.tournament_id}"))
            if tournament.default_host_country is None:
                tournament_issues.append(self._issue(f"tournament-default-host-country-{tournament.tournament_id}", "info", "tournament", "Mixed host in source templates.", tournament.tournament_id, tournament.name, f"/admin/tour-seasons/tournaments/{tournament.tournament_id}"))
            if tournament.default_region is None:
                tournament_issues.append(self._issue(f"tournament-default-region-{tournament.tournament_id}", "info", "tournament", "Mixed region in source templates.", tournament.tournament_id, tournament.name, f"/admin/tour-seasons/tournaments/{tournament.tournament_id}"))
            if not tournament.source_template_ids:
                tournament_issues.append(self._issue(f"tournament-source-template-ids-{tournament.tournament_id}", "warning", "tournament", "No source template IDs linked.", tournament.tournament_id, tournament.name, f"/admin/tour-seasons/tournaments/{tournament.tournament_id}"))
        if not tournament_issues:
            tournament_issues.append(self._issue("tournament-no-issues", "ok", "tournament", "No issues detected from current read-only checks.", link_hint="/admin/tour-seasons/tournaments"))

        template_issues: list[TourSeasonsValidationIssue] = []
        for template in templates:
            if template.week_count != 61:
                template_issues.append(self._issue(f"template-week-count-{template.template_id}", "warning", "season_template", f"week_count is {template.week_count} (expected 61).", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
            if template.slot_count != len(template.slots):
                template_issues.append(self._issue(f"template-slot-count-{template.template_id}", "warning", "season_template", f"slot_count ({template.slot_count}) does not match slots.length ({len(template.slots)}).", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
            if not template.slots:
                template_issues.append(self._issue(f"template-no-slots-{template.template_id}", "info", "season_template", "No slots present.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
            if template.source == "derived_preview:tournament_templates":
                template_issues.append(self._issue(f"template-derived-source-{template.template_id}", "info", "season_template", "Derived preview source; dedicated season template source ID is not yet explicit.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))

            for slot in template.slots:
                if slot.season_week_start < 1 or slot.season_week_end > 61:
                    template_issues.append(self._issue(f"template-slot-range-{template.template_id}-{slot.slot_id}", "warning", "season_template", f"Slot {slot.slot_id} has week range SW{slot.season_week_start}–SW{slot.season_week_end} outside SW1–SW61.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
                if slot.season_week_end < slot.season_week_start:
                    template_issues.append(self._issue(f"template-slot-order-{template.template_id}-{slot.slot_id}", "warning", "season_template", f"Slot {slot.slot_id} has end week before start week.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
                if slot.has_qualification and slot.qualifying_week_start is None:
                    template_issues.append(self._issue(f"template-slot-qualification-week-{template.template_id}-{slot.slot_id}", "warning", "season_template", f"Slot {slot.slot_id} has qualification enabled but qualifying_week_start is null.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
                if slot.source_template_id is None:
                    template_issues.append(self._issue(f"template-slot-source-template-{template.template_id}-{slot.slot_id}", "info", "season_template", f"Slot {slot.slot_id} has no source_template_id.", template.template_id, template.name, f"/admin/tour-seasons/season-templates/{template.template_id}"))
        if not template_issues:
            template_issues.append(self._issue("season-template-no-issues", "ok", "season_template", "No issues detected from current read-only checks.", link_hint="/admin/tour-seasons/season-templates"))

        sections = [
            TourSeasonsValidationSection(section_id="registry", title="Registry", issues=registry_issues),
            TourSeasonsValidationSection(section_id="category", title="Category", issues=category_issues),
            TourSeasonsValidationSection(section_id="tournament", title="Tournament", issues=tournament_issues),
            TourSeasonsValidationSection(section_id="season_template", title="Season Template", issues=template_issues),
        ]

        all_issues = [issue for section in sections for issue in section.issues]
        warning_count = sum(1 for issue in all_issues if issue.severity == "warning")
        info_count = sum(1 for issue in all_issues if issue.severity == "info")
        ok_count = sum(1 for issue in all_issues if issue.severity == "ok")
        slot_count = sum(len(template.slots) for template in templates)

        return TourSeasonsValidationResponse(
            status="read_only_foundation",
            summary=TourSeasonsValidationSummary(
                total_checks=len(all_issues),
                warning_count=warning_count,
                info_count=info_count,
                ok_count=ok_count,
                registry_loaded=True,
                category_count=len(categories),
                tournament_count=len(tournaments),
                season_template_count=len(templates),
                season_template_slot_count=slot_count,
            ),
            sections=sections,
            planned_future=[
                "Backend validation engine.",
                "Compare/apply validation.",
                "Edition lifecycle validation.",
                "Simulation-impact validation.",
            ],
        )

    def _issue(
        self,
        issue_id: str,
        severity: ValidationSeverity,
        area: str,
        message: str,
        item_id: str | None = None,
        item_name: str | None = None,
        link_hint: str | None = None,
    ) -> TourSeasonsValidationIssue:
        return TourSeasonsValidationIssue(
            issue_id=issue_id,
            severity=severity,
            area=area,
            item_id=item_id,
            item_name=item_name,
            message=message,
            link_hint=link_hint,
        )
