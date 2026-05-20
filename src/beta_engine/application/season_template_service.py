"""Read-only Season Template foundation service."""

from __future__ import annotations

from dataclasses import dataclass

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
