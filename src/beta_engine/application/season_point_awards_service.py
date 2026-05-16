"""Application service for deterministic event-level ranking/race point awards."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_event_results_service import PlayerReachedStage, SeasonEventResultPackage, SeasonEventResultsService
from beta_engine.application.season_match_service import MatchValidationIssue
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayersRegistry
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.infrastructure.points_config import load_points_config


# Temporary foundation mapping used only when event/template point config cannot be resolved.
FALLBACK_STAGE_POINTS: dict[str, int] = {
    "champion": 1000,
    "finalist": 650,
    "semifinal": 400,
    "quarterfinal": 250,
    "round_of_16": 120,
    "round_of_32": 60,
    "round_of_64": 30,
    "round_of_128": 10,
    "qualification_winner": 25,
    "qualification_final": 10,
    "qualification_semifinal": 5,
    "qualification_round": 0,
    "main_draw_participant": 0,
    "unknown": 0,
}

POINT_KEY_TO_STAGE: dict[str, str] = {
    "winner": "champion",
    "champion": "champion",
    "finalist": "finalist",
    "semifinalist": "semifinal",
    "semifinal": "semifinal",
    "quarterfinalist": "quarterfinal",
    "quarterfinal": "quarterfinal",
    "round_of_16": "round_of_16",
    "round_of_32": "round_of_32",
    "round_of_64": "round_of_64",
    "round_of_128": "round_of_128",
    "qualification_winner": "qualification_winner",
    "qualification_final": "qualification_final",
    "qualification_semifinal": "qualification_semifinal",
    "qualification_round": "qualification_round",
    "main_draw_participant": "main_draw_participant",
    "unknown": "unknown",
}


class PlayerPointAward(BaseModel):
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    reached_stage: PlayerReachedStage
    qualifier: bool = False
    seed_number: int | None = None
    ranking_points_awarded: int = Field(ge=0)
    race_points_awarded: int = Field(ge=0)
    previous_ranking_points: int | None = Field(default=None, ge=0)
    previous_race_points: int | None = Field(default=None, ge=0)
    projected_ranking_points: int | None = Field(default=None, ge=0)
    projected_race_points: int | None = Field(default=None, ge=0)
    source_result_fingerprint: str
    source_player_result_fingerprint: str
    award_fingerprint: str


class PointAwardSummary(BaseModel):
    event_id: str
    player_count: int = 0
    awarded_player_count: int = 0
    total_ranking_points: int = 0
    total_race_points: int = 0
    champion_player_id: str | None = None
    champion_points: int = 0
    finalist_player_id: str | None = None
    finalist_points: int = 0
    applied: bool = False
    validation_warning_count: int = 0
    validation_error_count: int = 0


class PointAwardMetadata(BaseModel):
    event_id: str
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    applied: bool
    build_fingerprint: str
    result_package_fingerprint: str
    point_distribution_fingerprint: str
    point_distribution_source: str
    ranking_updates_implemented: bool = True
    rolling_ranking_implemented: bool = False
    best_n_implemented: bool = False
    persistence_path: str | None = None


class EventPointAwardPackage(BaseModel):
    event_id: str
    season: str
    template_id: str
    event_name: str | None = None
    category: str | None = None
    tour_level: str | None = None
    seed: int
    dry_run: bool
    persisted: bool
    applied: bool = False
    awards: list[PlayerPointAward] = Field(default_factory=list)
    summary: PointAwardSummary
    metadata: PointAwardMetadata
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)


class PointAwardGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False


class PointAwardApplyRequest(BaseModel):
    seed: int = 12345
    overwrite_existing: bool = False
    allow_reapply: bool = False


class UpdatedPlayerPoints(BaseModel):
    player_id: str
    player_name: str | None = None
    previous_ranking_points: int = Field(ge=0)
    previous_race_points: int = Field(ge=0)
    new_ranking_points: int = Field(ge=0)
    new_race_points: int = Field(ge=0)
    delta_ranking_points: int = Field(ge=0)
    delta_race_points: int = Field(ge=0)


class AppliedEventRecord(BaseModel):
    applied: bool = True
    applied_fingerprint: str
    season: str
    seed: int


class SeasonPointAwardsRegistry(BaseModel):
    awards_by_event_id: dict[str, EventPointAwardPackage] = Field(default_factory=dict)
    applied_events: dict[str, AppliedEventRecord] = Field(default_factory=dict)


class EventPointAwardPackageResult(BaseModel):
    award_package: EventPointAwardPackage | None = None
    summary: PointAwardSummary | None = None
    metadata: PointAwardMetadata | None = None
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)
    award_package_exists: bool = False
    applied: bool = False


class PointAwardApplyResult(BaseModel):
    event_id: str
    applied: bool
    award_package: EventPointAwardPackage | None = None
    updated_players: list[UpdatedPlayerPoints] = Field(default_factory=list)
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)
    metadata: PointAwardMetadata | None = None


@dataclass(slots=True)
class SeasonPointAwardsService:
    """Generate and explicitly apply event-level points from persisted result packages."""

    result_service: SeasonEventResultsService
    active_players_service: InitialPoolSeasonBootstrapService
    calendar_service: SeasonCalendarService | None = None
    template_service: TournamentTemplatesConfigService | None = None
    awards_path: Path = Path("config/world/season_point_awards.json")
    points_config_path: Path = Path("config/points/mvp_points.json")

    def __post_init__(self) -> None:
        if not isinstance(self.awards_path, Path):
            self.awards_path = Path(self.awards_path)
        if not isinstance(self.points_config_path, Path):
            self.points_config_path = Path(self.points_config_path)
        if self.calendar_service is None:
            self.calendar_service = self.result_service.calendar_service

    def get_event_point_awards(self, *, event_id: str) -> EventPointAwardPackageResult:
        registry = self._load_registry()
        package = registry.awards_by_event_id.get(event_id)
        if package is None:
            return EventPointAwardPackageResult(award_package=None, award_package_exists=False, applied=event_id in registry.applied_events)
        return EventPointAwardPackageResult(
            award_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            award_package_exists=True,
            applied=package.applied or event_id in registry.applied_events,
        )

    def generate_event_point_awards(self, *, event_id: str, request: PointAwardGenerateRequest) -> EventPointAwardPackageResult:
        registry = self._load_registry()
        existing = registry.awards_by_event_id.get(event_id)
        if not request.dry_run and existing is not None and not request.overwrite_existing:
            raise ValueError(f"Point award package already exists for event '{event_id}'. Set overwrite_existing=true to replace only if not applied.")
        if not request.dry_run and existing is not None and existing.applied:
            raise ValueError(f"Point award package for event '{event_id}' has already been applied and cannot be overwritten.")
        if event_id in registry.applied_events:
            raise ValueError(f"Points for event '{event_id}' have already been applied and cannot be regenerated in this slice.")

        result_package = self._load_result_package(event_id)
        if result_package.validation_errors:
            codes = ", ".join(issue.code for issue in result_package.validation_errors)
            raise ValueError(f"Persisted event result package has validation errors: {codes}")

        active_players = self.active_players_service.get_active_players(season=result_package.season).players
        if not active_players:
            raise ValueError(f"No active season players found for season '{result_package.season}'. Persist active players before awarding points.")
        active_by_id = {player.player_id: player for player in active_players}

        distribution, distribution_source = self._resolve_point_distribution(result_package)
        warnings = self._foundation_warnings(event_id)
        if distribution_source.startswith("fallback"):
            warnings.append(self._issue("warning", "point_distribution_fallback_used", "fallback event-level point distribution was used", event_id=event_id))
        if result_package.completion_status != "complete":
            warnings.append(self._issue("warning", "event_result_incomplete", "event result package is not complete; preview/persist is allowed but apply is blocked", event_id=event_id))

        errors: list[MatchValidationIssue] = []
        awards: list[PlayerPointAward] = []
        result_fp = result_package.metadata.build_fingerprint
        for player_result in result_package.player_results:
            active = active_by_id.get(player_result.player_id)
            if active is None:
                errors.append(self._issue("error", "active_player_missing", "player in event result is missing from active season players", event_id=event_id, player_id=player_result.player_id))
                continue
            if player_result.reached_stage not in distribution:
                errors.append(self._issue("error", "unknown_reached_stage", "reached_stage has no point mapping", event_id=event_id, player_id=player_result.player_id, field="reached_stage"))
                continue
            points = max(0, int(distribution[player_result.reached_stage]))
            player_result_fp = self._fingerprint(player_result.model_dump(mode="json"))
            award_fp = self._fingerprint({
                "event_id": event_id,
                "seed": request.seed,
                "player_id": player_result.player_id,
                "reached_stage": player_result.reached_stage,
                "ranking_points_awarded": points,
                "race_points_awarded": points,
                "source_result_fingerprint": result_fp,
                "source_player_result_fingerprint": player_result_fp,
            })
            awards.append(PlayerPointAward(
                player_id=player_result.player_id,
                player_name=player_result.player_name or active.name,
                country_code=player_result.country_code or active.country_code,
                reached_stage=player_result.reached_stage,
                qualifier=player_result.qualifier,
                seed_number=player_result.seed_number,
                ranking_points_awarded=points,
                race_points_awarded=points,
                previous_ranking_points=active.ranking_points,
                previous_race_points=active.race_points,
                projected_ranking_points=active.ranking_points + points,
                projected_race_points=active.race_points + points,
                source_result_fingerprint=result_fp,
                source_player_result_fingerprint=player_result_fp,
                award_fingerprint=award_fp,
            ))

        distribution_fp = self._fingerprint(distribution)
        build_fp = self._fingerprint({
            "event_id": event_id,
            "seed": request.seed,
            "result_package_fingerprint": result_fp,
            "point_distribution_fingerprint": distribution_fp,
            "awards": [award.model_dump(mode="json") for award in sorted(awards, key=lambda item: item.player_id)],
        })
        applied = existing.applied if existing else False
        summary = self._summary(event_id=event_id, awards=awards, result_package=result_package, applied=applied, warnings=warnings, errors=errors)
        package = EventPointAwardPackage(
            event_id=event_id,
            season=result_package.season,
            template_id=result_package.template_id,
            event_name=result_package.event_name,
            category=result_package.category,
            tour_level=result_package.tour_level,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            applied=applied,
            awards=sorted(awards, key=lambda item: (self._stage_sort(item.reached_stage), item.player_name or "", item.player_id)),
            summary=summary,
            metadata=PointAwardMetadata(
                event_id=event_id,
                season=result_package.season,
                seed=request.seed,
                dry_run=request.dry_run,
                persisted=not request.dry_run,
                applied=applied,
                build_fingerprint=build_fp,
                result_package_fingerprint=result_fp,
                point_distribution_fingerprint=distribution_fp,
                point_distribution_source=distribution_source,
                persistence_path=None if request.dry_run else str(self.awards_path),
            ),
            validation_warnings=warnings,
            validation_errors=errors,
        )
        package.summary.validation_warning_count = len(package.validation_warnings)
        package.summary.validation_error_count = len(package.validation_errors)
        if package.validation_errors and not request.dry_run:
            codes = ", ".join(issue.code for issue in package.validation_errors)
            raise ValueError(f"Point award validation errors block persistence: {codes}")
        if not request.dry_run:
            next_awards = dict(registry.awards_by_event_id)
            next_awards[event_id] = package
            self._save_registry(SeasonPointAwardsRegistry(awards_by_event_id=next_awards, applied_events=dict(registry.applied_events)))
        return EventPointAwardPackageResult(
            award_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            award_package_exists=not request.dry_run,
            applied=package.applied,
        )

    def apply_event_point_awards(self, *, event_id: str, request: PointAwardApplyRequest) -> PointAwardApplyResult:
        if request.allow_reapply:
            raise ValueError("allow_reapply is not supported in this slice; implement explicit revert/reapply first.")
        registry = self._load_registry()
        package = registry.awards_by_event_id.get(event_id)
        if package is None:
            raise ValueError(f"No persisted point award package exists for event '{event_id}'. Persist awards before applying points.")
        if event_id in registry.applied_events or package.applied:
            raise ValueError(f"Points for event '{event_id}' have already been applied.")

        result_package = self._load_result_package(event_id)
        if result_package.completion_status != "complete":
            raise ValueError(f"Cannot apply points for event '{event_id}' because event result completion_status is '{result_package.completion_status}'.")
        if result_package.metadata.build_fingerprint != package.metadata.result_package_fingerprint:
            raise ValueError("Persisted point awards no longer match the current event result package fingerprint.")

        active_registry = self.active_players_service._load_registry()
        players = list(active_registry.players_by_season.get(package.season, []))
        if not players:
            raise ValueError(f"No active season players found for season '{package.season}'.")
        by_id = {player.player_id: player for player in players}
        missing = [award.player_id for award in package.awards if award.player_id not in by_id]
        if missing:
            missing_list = ", ".join(sorted(missing)[:5])
            raise ValueError(f"Cannot apply points because awarded players are missing from active season players: {missing_list}")

        award_by_player = {award.player_id: award for award in package.awards}
        updated_players: list[UpdatedPlayerPoints] = []
        next_players = []
        for player in players:
            award = award_by_player.get(player.player_id)
            if award is None:
                next_players.append(player)
                continue
            new_ranking = player.ranking_points + award.ranking_points_awarded
            new_race = player.race_points + award.race_points_awarded
            updated_players.append(UpdatedPlayerPoints(
                player_id=player.player_id,
                player_name=player.name,
                previous_ranking_points=player.ranking_points,
                previous_race_points=player.race_points,
                new_ranking_points=new_ranking,
                new_race_points=new_race,
                delta_ranking_points=award.ranking_points_awarded,
                delta_race_points=award.race_points_awarded,
            ))
            next_players.append(player.model_copy(update={"ranking_points": new_ranking, "race_points": new_race}))

        active_registry.players_by_season[package.season] = next_players
        self.active_players_service._save_registry(active_registry)

        applied_package = package.model_copy(update={"applied": True, "dry_run": False, "persisted": True})
        applied_package.metadata = package.metadata.model_copy(update={"applied": True, "dry_run": False, "persisted": True, "persistence_path": str(self.awards_path)})
        applied_package.summary = package.summary.model_copy(update={"applied": True})
        next_awards = dict(registry.awards_by_event_id)
        next_awards[event_id] = applied_package
        next_applied = dict(registry.applied_events)
        next_applied[event_id] = AppliedEventRecord(applied_fingerprint=applied_package.metadata.build_fingerprint, season=package.season, seed=request.seed)
        self._save_registry(SeasonPointAwardsRegistry(awards_by_event_id=next_awards, applied_events=next_applied))
        return PointAwardApplyResult(
            event_id=event_id,
            applied=True,
            award_package=applied_package,
            updated_players=sorted(updated_players, key=lambda item: item.player_id),
            validation_warnings=applied_package.validation_warnings,
            validation_errors=[],
            metadata=applied_package.metadata,
        )

    def _load_result_package(self, event_id: str) -> SeasonEventResultPackage:
        result = self.result_service.get_event_result(event_id=event_id)
        if result.result_package is None:
            raise ValueError(f"No persisted event result package exists for event '{event_id}'. Persist event results first.")
        return result.result_package

    def _resolve_point_distribution(self, package: SeasonEventResultPackage) -> tuple[dict[str, int], str]:
        event = None
        if self.calendar_service is not None:
            calendar = self.calendar_service.get_calendar(season=package.season).calendar
            if calendar is not None:
                event = next((item for item in calendar.events if item.event_id == package.event_id), None)
        if event is not None:
            if event.point_distribution is not None:
                return self._normalize_distribution(event.point_distribution.model_dump(mode="json")), "calendar_event.point_distribution"
            snapshot = event.template_snapshot or {}
            if isinstance(snapshot.get("point_distribution"), dict):
                return self._normalize_distribution(snapshot["point_distribution"]), "calendar_event.template_snapshot.point_distribution"
            ref = event.point_distribution_ref or snapshot.get("point_distribution_ref")
            resolved = self._distribution_by_ref(str(ref)) if ref else None
            if resolved is not None:
                return self._normalize_distribution(resolved), f"point_distribution_ref:{ref}"
        if self.template_service is not None:
            template = self.template_service.get_template(package.template_id)
            if template is not None:
                if template.point_distribution is not None:
                    return self._normalize_distribution(template.point_distribution.model_dump(mode="json")), "template.point_distribution"
                if template.point_distribution_ref:
                    resolved = self._distribution_by_ref(template.point_distribution_ref)
                    if resolved is not None:
                        return self._normalize_distribution(resolved), f"point_distribution_ref:{template.point_distribution_ref}"
        return dict(FALLBACK_STAGE_POINTS), "fallback.default_stage_points"

    def _distribution_by_ref(self, ref: str) -> dict[str, int] | None:
        try:
            distributions = load_points_config(self.points_config_path)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        return distributions.get(ref)

    @staticmethod
    def _normalize_distribution(distribution: dict[str, Any]) -> dict[str, int]:
        normalized = dict(FALLBACK_STAGE_POINTS)
        for key, value in distribution.items():
            stage = POINT_KEY_TO_STAGE.get(str(key))
            if stage is not None:
                normalized[stage] = max(0, int(value))
        return normalized

    @staticmethod
    def _foundation_warnings(event_id: str) -> list[MatchValidationIssue]:
        return [
            SeasonPointAwardsService._issue("warning", "race_points_equal_ranking_points", "race points equal ranking points as a temporary foundation", event_id=event_id),
            SeasonPointAwardsService._issue("warning", "rolling_ranking_not_implemented", "rolling 61-week ranking is not implemented in this slice", event_id=event_id),
            SeasonPointAwardsService._issue("warning", "best_n_not_implemented", "best-N ranking selection is not implemented in this slice", event_id=event_id),
            SeasonPointAwardsService._issue("warning", "prize_money_not_awarded", "prize money is not awarded by point application", event_id=event_id),
        ]

    @staticmethod
    def _summary(*, event_id: str, awards: list[PlayerPointAward], result_package: SeasonEventResultPackage, applied: bool, warnings: list[MatchValidationIssue], errors: list[MatchValidationIssue]) -> PointAwardSummary:
        champion = next((award for award in awards if award.player_id == result_package.summary.champion_player_id), None)
        finalist = next((award for award in awards if award.player_id == result_package.summary.finalist_player_id), None)
        return PointAwardSummary(
            event_id=event_id,
            player_count=len(awards),
            awarded_player_count=sum(1 for award in awards if award.ranking_points_awarded > 0 or award.race_points_awarded > 0),
            total_ranking_points=sum(award.ranking_points_awarded for award in awards),
            total_race_points=sum(award.race_points_awarded for award in awards),
            champion_player_id=champion.player_id if champion else result_package.summary.champion_player_id,
            champion_points=champion.ranking_points_awarded if champion else 0,
            finalist_player_id=finalist.player_id if finalist else result_package.summary.finalist_player_id,
            finalist_points=finalist.ranking_points_awarded if finalist else 0,
            applied=applied,
            validation_warning_count=len(warnings),
            validation_error_count=len(errors),
        )

    def _load_registry(self) -> SeasonPointAwardsRegistry:
        if not self.awards_path.exists():
            return SeasonPointAwardsRegistry()
        return SeasonPointAwardsRegistry.model_validate(json.loads(self.awards_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonPointAwardsRegistry) -> None:
        self.awards_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.awards_path.with_suffix(f"{self.awards_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.awards_path)

    @staticmethod
    def _stage_sort(stage: str) -> int:
        order = {name: index for index, name in enumerate(FALLBACK_STAGE_POINTS)}
        return order.get(stage, 99)

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(severity: Literal["warning", "error"], code: str, message: str, *, event_id: str | None = None, player_id: str | None = None, field: str | None = None) -> MatchValidationIssue:
        return MatchValidationIssue(severity=severity, code=code, message=message, event_id=event_id, match_id=None, player_id=player_id, field=field)
