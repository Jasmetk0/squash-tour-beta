"""Authoritative, season-specific Category ranking-points configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, Field

from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.calendar import parse_season_start_year
from beta_engine.infrastructure.points_config import load_points_config, normalize_ranking_points_table


class SeasonCategoryPointsTable(BaseModel):
    season: str
    category: str
    ranking_points_table: dict[str, int] = Field(default_factory=dict)
    provenance: str
    source_season: str | None = None


class SeasonCategoryPointsResponse(BaseModel):
    season: str
    initialized: bool
    categories: list[SeasonCategoryPointsTable] = Field(default_factory=list)


class SeasonCategoryPointsRegistry(BaseModel):
    seasons: dict[str, list[SeasonCategoryPointsTable]] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonCategoryPointsService:
    template_service: TournamentTemplatesConfigService
    registry_path: Path = Path("config/simulation/season_category_points.json")
    baseline_points_path: Path = Path("config/points/mvp_points.json")

    def __post_init__(self) -> None:
        self.registry_path = Path(self.registry_path)
        self.baseline_points_path = Path(self.baseline_points_path)

    def get(self, season: str) -> SeasonCategoryPointsResponse:
        rows = self._load().seasons.get(season)
        return SeasonCategoryPointsResponse(season=season, initialized=rows is not None, categories=rows or [])

    def initialize(self, season: str) -> SeasonCategoryPointsResponse:
        registry = self._load()
        if season in registry.seasons:
            return self.get(season)
        response = self.preview_initialization(season, registry=registry)
        updated = SeasonCategoryPointsRegistry(seasons={**registry.seasons, season: response.categories})
        self._save(updated)
        return response

    def preview_initialization(self, season: str, *, registry: SeasonCategoryPointsRegistry | None = None) -> SeasonCategoryPointsResponse:
        """Resolve the exact initialization candidate without writing authoritative state."""
        registry = registry or self._load()
        if season in registry.seasons:
            return SeasonCategoryPointsResponse(season=season, initialized=True, categories=registry.seasons[season])
        previous = self._previous_season(season)
        previous_by_category = {row.category: row for row in registry.seasons.get(previous, [])}
        baselines = self._baseline_by_category()
        rows: list[SeasonCategoryPointsTable] = []
        for category in self._active_categories():
            if category in previous_by_category:
                table = dict(previous_by_category[category].ranking_points_table)
                provenance, source = "prefilled_from_previous_season", previous
            else:
                table = dict(baselines.get(category, {}))
                provenance, source = "seeded_from_baseline", None
            rows.append(SeasonCategoryPointsTable(season=season, category=category, ranking_points_table=table, provenance=provenance, source_season=source))
        return SeasonCategoryPointsResponse(season=season, initialized=True, categories=rows)

    def update(self, season: str, category: str, table: dict[str, object]) -> SeasonCategoryPointsTable:
        registry = self._load()
        rows = registry.seasons.get(season)
        if rows is None:
            raise ValueError(f"Season Category points are not initialized for '{season}'.")
        canonical = normalize_ranking_points_table(table)
        if category not in {row.category for row in rows}:
            raise ValueError(f"Unknown Category '{category}' for season '{season}'.")
        replacement = SeasonCategoryPointsTable(season=season, category=category, ranking_points_table=canonical, provenance="manually_edited")
        next_rows = [replacement if row.category == category else row for row in rows]
        self._save(SeasonCategoryPointsRegistry(seasons={**registry.seasons, season: next_rows}))
        return replacement

    def resolve_table(self, season: str, category: str) -> dict[str, int] | None:
        rows = self._load().seasons.get(season)
        if rows is None:
            return None
        row = next((item for item in rows if item.category == category), None)
        return dict(row.ranking_points_table) if row else {}

    def _active_categories(self) -> list[str]:
        return sorted({template.category for template in self.template_service.get_config().templates if template.active})

    def _baseline_by_category(self) -> dict[str, dict[str, int]]:
        distributions = load_points_config(self.baseline_points_path)
        result: dict[str, dict[str, int]] = {}
        for template in self.template_service.get_config().templates:
            if not template.active or template.category in result:
                continue
            if template.point_distribution is not None:
                authored = template.point_distribution.model_dump(mode="json", exclude_unset=True)
                result[template.category] = normalize_ranking_points_table(authored)
            elif template.point_distribution_ref:
                result[template.category] = dict(distributions.get(template.point_distribution_ref, {}))
        return result

    @staticmethod
    def _previous_season(season: str) -> str:
        year = parse_season_start_year(season)
        return f"{year - 1:04d}/{year % 100:02d}"

    def _load(self) -> SeasonCategoryPointsRegistry:
        if not self.registry_path.exists():
            return SeasonCategoryPointsRegistry()
        return SeasonCategoryPointsRegistry.model_validate_json(self.registry_path.read_text(encoding="utf-8"))

    def _save(self, registry: SeasonCategoryPointsRegistry) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.registry_path.parent, delete=False) as handle:
            handle.write(registry.model_dump_json(indent=2))
            temporary = handle.name
        os.replace(temporary, self.registry_path)
