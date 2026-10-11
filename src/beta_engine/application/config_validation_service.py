"""Read-only config validation service for loaded engine config domains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from beta_engine.domain.countries import Country
from beta_engine.domain.tournaments import SeasonCalendar, TournamentTemplate, TournamentTemplatesConfig
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.points_config import load_points_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_player_identity_config
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore

ValidationSeverity = Literal["warning", "error"]


@dataclass(frozen=True)
class ConfigValidationIssue:
    severity: ValidationSeverity
    domain: str
    check_id: str
    source: str
    message: str
    location: str | None = None


@dataclass(frozen=True)
class ConfigDomainValidationResult:
    domain: str
    source: str
    valid: bool
    warnings: list[ConfigValidationIssue]
    errors: list[ConfigValidationIssue]


@dataclass(frozen=True)
class ConfigValidationReport:
    valid: bool
    warnings: list[ConfigValidationIssue]
    errors: list[ConfigValidationIssue]
    domains: list[ConfigDomainValidationResult]


@dataclass(slots=True)
class ConfigValidationService:
    """Validates configured engine domains without mutating persistence state."""

    def validate_current_config(self, *, season: int) -> ConfigValidationReport:
        issues: list[ConfigValidationIssue] = []
        domain_sources = {
            "season_calendar": f"config/calendar/season_{season}.json",
            "tournament_templates": "config/tournament_templates/mvp_templates.json",
            "countries": "config/world_packages/official_fax_world/countries/index.json",
            "player_identity": "config/player_generation/player_identity.json",
            "points": "config/points/mvp_points.json",
            "entry_tuning": "config/balance/entry_tuning.json",
        }

        calendar = self._load_domain(
            domain="season_calendar",
            source=domain_sources["season_calendar"],
            loader=lambda: load_season_calendar(season=season),
            issues=issues,
        )
        templates_config = self._load_domain(
            domain="tournament_templates",
            source=domain_sources["tournament_templates"],
            loader=load_tournament_templates_config,
            issues=issues,
        )
        countries_config = self._load_domain(
            domain="countries",
            source=domain_sources["countries"],
            loader=lambda: WorldPackageCountryStore("config/world_packages/official_fax_world").load_config(),
            issues=issues,
        )
        self._load_domain(
            domain="player_identity",
            source=domain_sources["player_identity"],
            loader=load_player_identity_config,
            issues=issues,
        )
        points = self._load_domain(
            domain="points",
            source=domain_sources["points"],
            loader=load_points_config,
            issues=issues,
        )
        self._load_domain(
            domain="entry_tuning",
            source=domain_sources["entry_tuning"],
            loader=load_entry_tuning_config,
            issues=issues,
        )

        if calendar is not None and templates_config is not None and countries_config is not None and points is not None:
            issues.extend(
                self._cross_validate(
                    calendar=calendar,
                    templates_config=templates_config,
                    countries=countries_config.countries,
                    points=points,
                    season_source=domain_sources["season_calendar"],
                    template_source=domain_sources["tournament_templates"],
                    countries_source=domain_sources["countries"],
                    points_source=domain_sources["points"],
                )
            )

        issues = self._sort_issues(issues)
        warnings = [issue for issue in issues if issue.severity == "warning"]
        errors = [issue for issue in issues if issue.severity == "error"]

        domains: list[ConfigDomainValidationResult] = []
        for domain, source in domain_sources.items():
            domain_warnings = [issue for issue in warnings if issue.domain == domain]
            domain_errors = [issue for issue in errors if issue.domain == domain]
            domains.append(
                ConfigDomainValidationResult(
                    domain=domain,
                    source=source,
                    valid=not domain_errors,
                    warnings=domain_warnings,
                    errors=domain_errors,
                )
            )

        return ConfigValidationReport(
            valid=not errors,
            warnings=warnings,
            errors=errors,
            domains=domains,
        )

    def _load_domain(self, *, domain: str, source: str, loader, issues: list[ConfigValidationIssue]):
        try:
            return loader()
        except Exception as exc:  # noqa: BLE001 - validation surface should aggregate all domain load failures.
            issues.append(
                ConfigValidationIssue(
                    severity="error",
                    domain=domain,
                    check_id="load_error",
                    source=source,
                    message=str(exc),
                )
            )
            return None

    def _cross_validate(
        self,
        *,
        calendar: SeasonCalendar,
        templates_config: TournamentTemplatesConfig,
        countries: list[Country],
        points: dict[str, dict[str, int]],
        season_source: str,
        template_source: str,
        countries_source: str,
        points_source: str,
    ) -> list[ConfigValidationIssue]:
        issues: list[ConfigValidationIssue] = []
        countries_by_code = {country.code: country for country in countries}
        templates_by_id = {template.template_id: template for template in templates_config.templates}

        for template in templates_config.templates:
            issues.extend(
                self._validate_template(
                    template=template,
                    countries_by_code=countries_by_code,
                    points=points,
                    template_source=template_source,
                    countries_source=countries_source,
                    points_source=points_source,
                )
            )

        for event in calendar.events:
            template = templates_by_id.get(event.template_id)
            if template is None:
                issues.append(
                    ConfigValidationIssue(
                        severity="error",
                        domain="season_calendar",
                        check_id="template_ref_exists",
                        source=season_source,
                        message=f"event references unknown template_id '{event.template_id}'",
                        location=f"event_id={event.event_id}",
                    )
                )
                continue

            if event.host_country not in countries_by_code:
                issues.append(
                    ConfigValidationIssue(
                        severity="error",
                        domain="season_calendar",
                        check_id="host_country_exists",
                        source=season_source,
                        message=f"event host_country '{event.host_country}' not found in countries config",
                        location=f"event_id={event.event_id}",
                    )
                )

            if event.host_country != template.host_country:
                issues.append(
                    ConfigValidationIssue(
                        severity="warning",
                        domain="season_calendar",
                        check_id="event_template_host_country_mismatch",
                        source=season_source,
                        message=(
                            f"event host_country '{event.host_country}' differs from template host_country "
                            f"'{template.host_country}'"
                        ),
                        location=f"event_id={event.event_id}",
                    )
                )

        return issues

    def _validate_template(
        self,
        *,
        template: TournamentTemplate,
        countries_by_code: dict[str, Country],
        points: dict[str, dict[str, int]],
        template_source: str,
        countries_source: str,
        points_source: str,
    ) -> list[ConfigValidationIssue]:
        issues: list[ConfigValidationIssue] = []

        if template.host_country not in countries_by_code:
            issues.append(
                ConfigValidationIssue(
                    severity="error",
                    domain="tournament_templates",
                    check_id="host_country_exists",
                    source=template_source,
                    message=f"template host_country '{template.host_country}' not found in countries config",
                    location=f"template_id={template.template_id} ({countries_source})",
                )
            )

        if template.point_distribution_ref is not None and template.point_distribution_ref not in points:
            issues.append(
                ConfigValidationIssue(
                    severity="error",
                    domain="tournament_templates",
                    check_id="point_distribution_ref_exists",
                    source=template_source,
                    message=(
                        f"template point_distribution_ref '{template.point_distribution_ref}' not found in points config"
                    ),
                    location=f"template_id={template.template_id} ({points_source})",
                )
            )

        if template.point_distribution_ref is not None and template.point_distribution is not None:
            issues.append(
                ConfigValidationIssue(
                    severity="warning",
                    domain="tournament_templates",
                    check_id="point_distribution_ref_and_inline_present",
                    source=template_source,
                    message="template defines both point_distribution_ref and inline point_distribution",
                    location=f"template_id={template.template_id}",
                )
            )

        return issues

    def _sort_issues(self, issues: list[ConfigValidationIssue]) -> list[ConfigValidationIssue]:
        severity_order = {"error": 0, "warning": 1}
        return sorted(
            issues,
            key=lambda issue: (
                severity_order[issue.severity],
                issue.domain,
                issue.check_id,
                issue.location or "",
                issue.message,
            ),
        )
