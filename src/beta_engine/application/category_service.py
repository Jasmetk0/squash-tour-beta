"""Read-only Categories foundation service derived from tournament templates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments.models import TournamentTemplate


class CategorySummary(BaseModel):
    category_id: str
    name: str
    status: str = "read_only_foundation"
    source: str = "derived_preview:tournament_templates"
    template_count: int = Field(ge=0)
    valid_from_season: str | None = None
    valid_to_season: str | None = None
    tour_level: str | None = None
    prestige_rank: int | None = None
    mandatory: bool | None = None
    main_draw_size: int | None = None
    qualification_draw_size: int | None = None
    direct_entries: int | None = None
    qualifiers: int | None = None
    wildcards: int | None = None
    lucky_losers: int | None = None
    seeds_count: int | None = None
    points_by_round: dict[str, int] | None = None
    prize_money_total: int | float | None = None
    match_format: str | None = None
    qualifying_weeks_count: int | None = None
    main_draw_weeks_count: int | None = None
    schedule_footprint_weeks: int | None = None
    source_template_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CategoriesResponse(BaseModel):
    categories: list[CategorySummary] = Field(default_factory=list)
    source_path: str | None = None
    status: str = "read_only_foundation"


@dataclass(slots=True)
class CategoryService:
    template_service: TournamentTemplatesConfigService

    def list_categories(self) -> CategoriesResponse:
        templates = self.template_service.get_config().templates
        grouped: dict[str, list[TournamentTemplate]] = {}
        for template in templates:
            grouped.setdefault(template.category, []).append(template)

        categories = [self._build_summary(name, rows) for name, rows in grouped.items()]
        categories.sort(key=lambda item: item.category_id)
        return CategoriesResponse(categories=categories, source_path=str(self.template_service.config_path))

    def _build_summary(self, name: str, templates: list[TournamentTemplate]) -> CategorySummary:
        source_template_ids = sorted(template.template_id for template in templates)
        notes: list[str] = []

        return CategorySummary(
            category_id=self._slug(name),
            name=name,
            template_count=len(templates),
            tour_level=self._consistent_value(templates, "tour_level", notes),
            mandatory=None,
            main_draw_size=self._consistent_value(templates, "main_draw_size", notes),
            qualification_draw_size=self._consistent_value(templates, "qualification_draw_size", notes),
            direct_entries=self._consistent_computed(templates, lambda template: template.main_draw_size - template.qualifier_spots - template.wild_cards, "direct_entries", notes),
            qualifiers=self._consistent_value(templates, "qualifier_spots", notes),
            wildcards=self._consistent_value(templates, "wild_cards", notes),
            lucky_losers=self._consistent_computed(templates, lambda template: template.lucky_loser_rules.max_spots, "lucky_losers", notes),
            seeds_count=self._consistent_value(templates, "seeds_count", notes),
            points_by_round=self._consistent_computed(templates, self._points_for_template, "points_by_round", notes),
            prize_money_total=self._consistent_value(templates, "prize_money", notes),
            match_format=None,
            qualifying_weeks_count=self._consistent_computed(templates, lambda template: 1 if template.qualification_draw_size > 0 else 0, "qualifying_weeks_count", notes),
            main_draw_weeks_count=None,
            schedule_footprint_weeks=self._consistent_value(templates, "duration_in_season_weeks", notes),
            source_template_ids=source_template_ids,
            notes=notes,
        )

    def _consistent_value(self, templates: list[TournamentTemplate], attr: str, notes: list[str]) -> Any:
        values = {getattr(template, attr) for template in templates}
        if len(values) == 1:
            return next(iter(values))
        notes.append(f"mixed values across source templates for {attr}")
        return None

    def _consistent_computed(self, templates: list[TournamentTemplate], fn: Any, field: str, notes: list[str]) -> Any:
        values = [fn(template) for template in templates]
        markers = {json.dumps(value, sort_keys=True) for value in values}
        if len(markers) == 1:
            return values[0]
        notes.append(f"mixed values across source templates for {field}")
        return None

    def _points_for_template(self, template: TournamentTemplate) -> dict[str, int] | None:
        if template.point_distribution is not None:
            return template.point_distribution.model_dump()
        return None

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
