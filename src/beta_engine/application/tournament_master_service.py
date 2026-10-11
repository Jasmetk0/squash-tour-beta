"""Read-only Tournament Masters foundation service derived from tournament templates."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments.models import TournamentTemplate


class TournamentMasterSummary(BaseModel):
    tournament_id: str
    name: str
    status: str = "read_only_foundation"
    source: str = "derived_preview:tournament_templates"
    source_template_ids: list[str] = Field(default_factory=list)
    template_count: int = Field(ge=0)
    categories: list[str] = Field(default_factory=list)
    tour_levels: list[str] = Field(default_factory=list)
    host_countries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    default_category: str | None = None
    default_host_country: str | None = None
    default_region: str | None = None
    default_duration_weeks: int | None = None
    has_qualification: bool | None = None
    notes: list[str] = Field(default_factory=list)


class TournamentMastersResponse(BaseModel):
    tournaments: list[TournamentMasterSummary] = Field(default_factory=list)
    source_path: str | None = None
    status: str = "read_only_foundation"


@dataclass(slots=True)
class TournamentMasterService:
    template_service: TournamentTemplatesConfigService

    def list_tournaments(self) -> TournamentMastersResponse:
        templates = self.template_service.get_config().templates
        grouped: dict[str, list[TournamentTemplate]] = {}
        for template in templates:
            grouped.setdefault(template.event_name, []).append(template)

        tournaments = [self._build_summary(name, rows) for name, rows in grouped.items()]
        tournaments.sort(key=lambda item: item.tournament_id)
        return TournamentMastersResponse(tournaments=tournaments, source_path=str(self.template_service.config_path))

    def _build_summary(self, name: str, templates: list[TournamentTemplate]) -> TournamentMasterSummary:
        notes: list[str] = []
        categories = sorted({template.category for template in templates})
        tour_levels = sorted({template.tour_level for template in templates})
        host_countries = sorted({template.host_country for template in templates})
        regions = sorted({template.region for template in templates})

        return TournamentMasterSummary(
            tournament_id=self._slug(name),
            name=name,
            source_template_ids=sorted(template.template_id for template in templates),
            template_count=len(templates),
            categories=categories,
            tour_levels=tour_levels,
            host_countries=host_countries,
            regions=regions,
            default_category=self._default_or_none(categories, "category", notes),
            default_host_country=self._default_or_none(host_countries, "host_country", notes),
            default_region=self._default_or_none(regions, "region", notes),
            default_duration_weeks=self._default_or_none(sorted({template.duration_in_season_weeks for template in templates}), "duration_in_season_weeks", notes),
            has_qualification=self._default_or_none(sorted({template.qualification_draw_size > 0 for template in templates}), "has_qualification", notes),
            notes=notes,
        )

    def _default_or_none(self, values: list[object], field_name: str, notes: list[str]):
        if len(values) == 1:
            return values[0]
        notes.append(f"mixed values across source templates for {field_name}")
        return None

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
