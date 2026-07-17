"""Application service for deterministic season event entry-list generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayer
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.entries import EntryDecision, EntryEngine, EntryTarget
from beta_engine.domain.players.lifecycle import MAX_RUNTIME_PLAYER_AGE, MIN_RUNTIME_PLAYER_AGE
from beta_engine.domain.players.models import Player
from beta_engine.domain.tournaments import LuckyLoserRules, SeasonCalendarEvent, TournamentTemplate
from beta_engine.infrastructure.entry_config import load_entry_tuning_config

EntryListDecision = Literal["accepted_main_draw", "accepted_qualification", "alternate", "rejected", "not_entered"]
ValidationSeverity = Literal["warning", "error"]


class EntryListValidationIssue(BaseModel):
    severity: ValidationSeverity
    code: str
    message: str
    event_id: str | None = None
    player_id: str | None = None
    field: str | None = None


class SeasonEventEntry(BaseModel):
    entry_id: str
    player_id: str
    name: str
    country_code: str
    ranking_points: int = Field(ge=0)
    race_points: int = Field(ge=0)
    current_ability: int = Field(ge=1, le=99)
    potential_ability: int = Field(ge=1, le=99)
    entry_probability: float = Field(ge=0.0, le=1.0)
    entry_score: float
    quality_score: float = Field(ge=0.0, le=1.0)
    travel_score: float | None = Field(default=None, ge=0.0, le=1.0)
    decision: EntryListDecision
    acceptance_status: str
    ranking_priority: int
    seed_candidate_rank: int | None = None
    source_player_fingerprint: str
    bootstrap_fingerprint: str
    generated_fingerprint: str
    reason: str | None = None
    decision_notes: str | None = None


class EntryListSummary(BaseModel):
    total_active_players: int = 0
    considered_players: int = 0
    entered_players: int = 0
    main_draw_acceptances: int = 0
    qualification_acceptances: int = 0
    alternates: int = 0
    rejected_or_not_entered: int = 0
    countries_represented: int = 0
    average_entry_probability: float = 0.0
    average_quality_score: float = 0.0
    validation_warning_count: int = 0
    validation_error_count: int = 0


class EntryListMetadata(BaseModel):
    event_id: str
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    build_fingerprint: str
    active_players_fingerprint: str
    calendar_event_fingerprint: str
    ranking_basis: str = "current zero-points bootstrap; future official ranking not integrated"
    persistence_path: str | None = None


class SeasonEventEntryList(BaseModel):
    event_id: str
    season: str
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = Field(default=None, ge=1900, le=2100)
    year_week: int | None = Field(default=None, ge=1, le=61)
    template_id: str
    generated_from_calendar_fingerprint: str
    generated_from_active_players_fingerprint: str
    seed: int
    dry_run: bool
    persisted: bool
    entries: list[SeasonEventEntry] = Field(default_factory=list)
    summary: EntryListSummary
    metadata: EntryListMetadata
    validation_warnings: list[EntryListValidationIssue] = Field(default_factory=list)
    validation_errors: list[EntryListValidationIssue] = Field(default_factory=list)


class SeasonEventEntryListResult(BaseModel):
    entry_list: SeasonEventEntryList | None = None
    summary: EntryListSummary = Field(default_factory=EntryListSummary)
    metadata: EntryListMetadata | None = None
    validation_warnings: list[EntryListValidationIssue] = Field(default_factory=list)
    validation_errors: list[EntryListValidationIssue] = Field(default_factory=list)
    entry_list_exists: bool = False


class EntryListGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False
    max_alternates: int = Field(default=16, ge=0, le=256)
    include_not_entered: bool = False


class SeasonEntryListsRegistry(BaseModel):
    entry_lists_by_event_id: dict[str, SeasonEventEntryList] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonEntryListService:
    active_players_service: InitialPoolSeasonBootstrapService
    calendar_service: SeasonCalendarService
    countries_service: CountriesConfigService
    entry_lists_path: Path = Path("config/world/season_entry_lists.json")
    entry_tuning_path: Path = Path("config/balance/entry_tuning.json")

    def __post_init__(self) -> None:
        if not isinstance(self.entry_lists_path, Path):
            self.entry_lists_path = Path(self.entry_lists_path)
        if not isinstance(self.entry_tuning_path, Path):
            self.entry_tuning_path = Path(self.entry_tuning_path)

    def get_entry_list(self, *, event_id: str) -> SeasonEventEntryListResult:
        registry = self._load_registry()
        entry_list = registry.entry_lists_by_event_id.get(event_id)
        if entry_list is None:
            return SeasonEventEntryListResult(entry_list=None, entry_list_exists=False)
        return SeasonEventEntryListResult(
            entry_list=entry_list,
            summary=entry_list.summary,
            metadata=entry_list.metadata,
            validation_warnings=entry_list.validation_warnings,
            validation_errors=entry_list.validation_errors,
            entry_list_exists=True,
        )

    def generate_entry_list(self, *, event_id: str, request: EntryListGenerateRequest) -> SeasonEventEntryListResult:
        registry = self._load_registry()
        exists = event_id in registry.entry_lists_by_event_id
        if not request.dry_run and exists and not request.overwrite_existing:
            raise ValueError(f"Entry list already exists for event '{event_id}'. Set overwrite_existing=true to replace only that event.")

        event = self._find_event(event_id)
        active_response = self.active_players_service.get_active_players(season=str(event.season))
        active_players = sorted(active_response.players, key=lambda player: player.player_id)
        if not active_players:
            raise ValueError(f"No active season players found for season '{event.season}'. Bootstrap active players before generating entries.")

        countries_by_code = {country.code: country for country in self.countries_service.list_countries()}
        players = [self._adapt_player(player) for player in active_players]
        template = self._template_from_event_snapshot(event)
        engine = EntryEngine(rng=DeterministicRng(request.seed), tuning=load_entry_tuning_config(self.entry_tuning_path))
        event_rng = engine.rng.branch(SeedScope.WEEK, self._season_seed_component(event.season), event.week, event.event_id)

        decisions_by_player: dict[str, EntryDecision] = {}
        warnings: list[EntryListValidationIssue] = []
        for player in players:
            country = countries_by_code.get(player.nationality)
            if country is None:
                warnings.append(self._issue("warning", "country_missing", f"player country '{player.nationality}' is missing from country config", event_id=event.event_id, player_id=player.player_id, field="country_code"))
                continue
            decisions_by_player[player.player_id] = engine.decide_entry(player=player, player_country=country, event=event, template=template, event_rng=event_rng)

        active_by_id = {player.player_id: player for player in active_players}
        main_candidates = [d for d in decisions_by_player.values() if d.target == EntryTarget.MAIN]
        qualification_candidates = [d for d in decisions_by_player.values() if d.target == EntryTarget.QUALIFICATION]
        ranked_main = self._sort_decisions(main_candidates, active_by_id)
        ranked_qualification = self._sort_decisions(qualification_candidates, active_by_id)

        direct_slots = max(0, event.main_draw_size - event.qualifier_spots - event.wild_cards - event.byes)
        qualification_slots = event.qualification_draw_size
        entries: list[SeasonEventEntry] = []
        used_players: set[str] = set()
        priority = 1
        for decision in ranked_main[:direct_slots]:
            entries.append(self._entry_from_decision(decision, active_by_id[decision.player_id], "accepted_main_draw", priority, reason="direct main draw acceptance"))
            used_players.add(decision.player_id)
            priority += 1
        for decision in ranked_qualification[:qualification_slots]:
            if decision.player_id in used_players:
                continue
            entries.append(self._entry_from_decision(decision, active_by_id[decision.player_id], "accepted_qualification", priority, reason="qualification acceptance"))
            used_players.add(decision.player_id)
            priority += 1

        remaining_entered = [d for d in self._sort_decisions([*ranked_main[direct_slots:], *ranked_qualification[qualification_slots:]], active_by_id) if d.player_id not in used_players]
        for decision in remaining_entered[: request.max_alternates]:
            entries.append(self._entry_from_decision(decision, active_by_id[decision.player_id], "alternate", priority, reason="waitlist alternate"))
            used_players.add(decision.player_id)
            priority += 1
        if request.include_not_entered:
            for decision in self._sort_decisions(list(decisions_by_player.values()), active_by_id):
                if decision.player_id in used_players:
                    continue
                decision_name = "rejected" if decision.target in {EntryTarget.MAIN, EntryTarget.QUALIFICATION} else "not_entered"
                reason = "entered but not accepted" if decision_name == "rejected" else "entry roll did not enter tournament"
                entries.append(self._entry_from_decision(decision, active_by_id[decision.player_id], decision_name, priority, reason=reason))
                priority += 1

        active_fp = self._fingerprint([player.model_dump(mode="json") for player in active_players])
        event_fp = event.calendar_fingerprint or event.template_snapshot_fingerprint or self._fingerprint(event.model_dump(mode="json"))
        validation_warnings, validation_errors = self.validate_event_entry_constraints(event=event, entries=entries, existing_entry_lists=registry.entry_lists_by_event_id)
        warnings.extend(validation_warnings)
        summary = self._summary(active_players=active_players, considered=len(decisions_by_player), entries=entries, warnings=warnings, errors=validation_errors)
        build_fp = self._fingerprint({
            "event_id": event.event_id,
            "seed": request.seed,
            "active_players_fingerprint": active_fp,
            "calendar_event_fingerprint": event_fp,
            "entries": [entry.model_dump(mode="json") for entry in entries],
            "summary": summary.model_dump(mode="json"),
        })
        metadata = EntryListMetadata(
            event_id=event.event_id,
            season=str(event.season),
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            build_fingerprint=build_fp,
            active_players_fingerprint=active_fp,
            calendar_event_fingerprint=event_fp,
            persistence_path=None if request.dry_run else str(self.entry_lists_path),
        )
        entry_list = SeasonEventEntryList(
            event_id=event.event_id,
            season=str(event.season),
            season_week=event.season_week,
            calendar_year=event.calendar_year,
            year_week=event.year_week,
            template_id=event.template_id,
            generated_from_calendar_fingerprint=event_fp,
            generated_from_active_players_fingerprint=active_fp,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            entries=entries,
            summary=summary,
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=validation_errors,
        )
        if not request.dry_run:
            if validation_errors:
                first = validation_errors[0]
                raise ValueError(f"Entry list validation failed: {first.code}: {first.message}")
            next_lists = dict(registry.entry_lists_by_event_id)
            next_lists[event_id] = entry_list
            self._save_registry(SeasonEntryListsRegistry(entry_lists_by_event_id=next_lists))
        return SeasonEventEntryListResult(entry_list=entry_list, summary=summary, metadata=metadata, validation_warnings=warnings, validation_errors=validation_errors, entry_list_exists=exists or not request.dry_run)

    def validate_event_entry_constraints(self, *, event: SeasonCalendarEvent, entries: list[SeasonEventEntry], existing_entry_lists: dict[str, SeasonEventEntryList]) -> tuple[list[EntryListValidationIssue], list[EntryListValidationIssue]]:
        warnings: list[EntryListValidationIssue] = []
        errors: list[EntryListValidationIssue] = []
        accepted = {entry.player_id for entry in entries if entry.decision in {"accepted_main_draw", "accepted_qualification"}}
        start = event.start_season_week or event.season_week
        end = event.end_season_week or start
        for existing in existing_entry_lists.values():
            if existing.event_id == event.event_id or existing.season != str(event.season):
                continue
            existing_start = existing.season_week
            existing_end = existing.season_week
            calendar = self.calendar_service.get_calendar(season=existing.season).calendar
            if calendar is not None:
                matched = next((item for item in calendar.events if item.event_id == existing.event_id), None)
                if matched is not None:
                    existing_start = matched.start_season_week or matched.season_week
                    existing_end = matched.end_season_week or existing_start
            if max(start, existing_start) > min(end, existing_end):
                continue
            existing_accepted = {entry.player_id for entry in existing.entries if entry.decision in {"accepted_main_draw", "accepted_qualification"}}
            for player_id in sorted(accepted & existing_accepted):
                errors.append(self._issue("error", "player_week_overlap", f"player '{player_id}' is already accepted into overlapping event '{existing.event_id}'", event_id=event.event_id, player_id=player_id, field="season_week"))
        if not accepted:
            warnings.append(self._issue("warning", "no_accepted_players", "entry list has no accepted main draw or qualification players", event_id=event.event_id))
        return warnings, errors

    def _find_event(self, event_id: str) -> SeasonCalendarEvent:
        registry = self.calendar_service._load_registry()  # intentional application-layer registry reuse
        if not registry.calendars_by_season:
            raise ValueError("No persisted season calendar exists. Persist a season calendar before generating entries.")
        for calendar in registry.calendars_by_season.values():
            for event in calendar.events:
                if event.event_id == event_id:
                    return event
        raise ValueError(f"Unknown persisted season calendar event '{event_id}'.")

    @staticmethod
    def _adapt_player(player: SeasonActivePlayer) -> Player:
        attrs = player.attributes
        return Player(
            player_id=player.player_id,
            name=player.name,
            # Defensive legacy normalization only; valid 15/45 lifecycle ages are preserved.
            age=max(MIN_RUNTIME_PLAYER_AGE, min(MAX_RUNTIME_PLAYER_AGE, player.age_years_at_season_start)),
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            nationality=player.nationality or player.country_code,
            technique=attrs.technique,
            movement=attrs.movement,
            physical=attrs.physical,
            mental=attrs.mental,
            consistency=attrs.consistency,
            clutch=attrs.clutch,
            recovery=attrs.recovery,
            play_style=player.play_style,
            archetype=player.archetype,
            hidden_career_traits=player.hidden_career_traits,
        )

    @staticmethod
    def _template_from_event_snapshot(event: SeasonCalendarEvent) -> TournamentTemplate:
        snapshot = dict(event.template_snapshot or {})
        payload: dict[str, Any] = {
            **snapshot,
            "template_id": event.template_id,
            "tour_level": event.tour_level or snapshot.get("tour_level") or "WORLD_TOUR",
            "category": event.category or snapshot.get("category") or "UNKNOWN",
            "event_name": event.event_name or snapshot.get("event_name") or event.event_id,
            "region": event.region,
            "host_country": event.host_country,
            "main_draw_size": event.main_draw_size,
            "qualification_draw_size": event.qualification_draw_size,
            "seeds_count": event.seeds_count,
            "qualifier_spots": event.qualifier_spots,
            "wild_cards": event.wild_cards,
            "byes": event.byes,
            "lucky_loser_rules": snapshot.get("lucky_loser_rules") or LuckyLoserRules(enabled=True, max_spots=0).model_dump(mode="json"),
            "point_distribution_ref": event.point_distribution_ref or snapshot.get("point_distribution_ref"),
            "point_distribution": event.point_distribution or snapshot.get("point_distribution"),
            "event_duration_days": snapshot.get("event_duration_days") or 1,
            "qualification_duration_days": snapshot.get("qualification_duration_days") or 0,
            "prize_money": event.prize_money,
            "prestige": event.prestige,
            "duration_in_season_weeks": event.duration_in_season_weeks,
            "active": snapshot.get("active", True),
        }
        if payload.get("point_distribution_ref") is None and payload.get("point_distribution") is None:
            payload["point_distribution_ref"] = "event_snapshot"
        return TournamentTemplate.model_validate(payload)

    @staticmethod
    def _sort_decisions(decisions: list[EntryDecision], players_by_id: dict[str, SeasonActivePlayer]) -> list[EntryDecision]:
        return sorted(decisions, key=lambda decision: (-players_by_id[decision.player_id].ranking_points, -decision.entry_score, -decision.quality_score, decision.player_id))

    def _entry_from_decision(self, decision: EntryDecision, player: SeasonActivePlayer, decision_name: EntryListDecision, priority: int, *, reason: str) -> SeasonEventEntry:
        payload = {
            "event_id": decision.event_id,
            "player_id": player.player_id,
            "decision": decision_name,
            "priority": priority,
            "entry_score": decision.entry_score,
            "quality_score": decision.quality_score,
            "source": player.bootstrap_fingerprint,
        }
        generated = self._fingerprint(payload)
        return SeasonEventEntry(
            entry_id=f"{decision.event_id}:{player.player_id}:{decision_name}",
            player_id=player.player_id,
            name=player.name,
            country_code=player.country_code,
            ranking_points=player.ranking_points,
            race_points=player.race_points,
            current_ability=player.current_ability,
            potential_ability=player.potential_ability,
            entry_probability=decision.entry_probability,
            entry_score=decision.entry_score,
            quality_score=decision.quality_score,
            travel_score=decision.travel_score,
            decision=decision_name,
            acceptance_status=decision_name,
            ranking_priority=priority,
            seed_candidate_rank=priority if decision_name == "accepted_main_draw" else None,
            source_player_fingerprint=player.source_generation_fingerprint,
            bootstrap_fingerprint=player.bootstrap_fingerprint,
            generated_fingerprint=generated,
            reason=reason,
            decision_notes=f"EntryEngine target={decision.target.value}",
        )

    @staticmethod
    def _summary(*, active_players: list[SeasonActivePlayer], considered: int, entries: list[SeasonEventEntry], warnings: list[EntryListValidationIssue], errors: list[EntryListValidationIssue]) -> EntryListSummary:
        entered = [entry for entry in entries if entry.decision in {"accepted_main_draw", "accepted_qualification", "alternate"}]
        return EntryListSummary(
            total_active_players=len(active_players),
            considered_players=considered,
            entered_players=len(entered),
            main_draw_acceptances=sum(1 for entry in entries if entry.decision == "accepted_main_draw"),
            qualification_acceptances=sum(1 for entry in entries if entry.decision == "accepted_qualification"),
            alternates=sum(1 for entry in entries if entry.decision == "alternate"),
            rejected_or_not_entered=sum(1 for entry in entries if entry.decision in {"rejected", "not_entered"}),
            countries_represented=len({entry.country_code for entry in entered}),
            average_entry_probability=round(sum(entry.entry_probability for entry in entries) / len(entries), 6) if entries else 0.0,
            average_quality_score=round(sum(entry.quality_score for entry in entries) / len(entries), 6) if entries else 0.0,
            validation_warning_count=len(warnings),
            validation_error_count=len(errors),
        )

    def _load_registry(self) -> SeasonEntryListsRegistry:
        if not self.entry_lists_path.exists():
            return SeasonEntryListsRegistry()
        return SeasonEntryListsRegistry.model_validate(json.loads(self.entry_lists_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonEntryListsRegistry) -> None:
        self.entry_lists_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.entry_lists_path.with_suffix(f"{self.entry_lists_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.entry_lists_path)

    @staticmethod
    def _season_seed_component(season: str | int) -> int:
        if isinstance(season, int):
            return season
        try:
            return int(str(season).split("/", maxsplit=1)[0])
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(severity: ValidationSeverity, code: str, message: str, *, event_id: str | None = None, player_id: str | None = None, field: str | None = None) -> EntryListValidationIssue:
        return EntryListValidationIssue(severity=severity, code=code, message=message, event_id=event_id, player_id=player_id, field=field)
