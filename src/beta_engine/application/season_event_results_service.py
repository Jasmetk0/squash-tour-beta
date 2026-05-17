"""Application service for deterministic event result extraction from persisted matches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_draw_service import DrawSlotRecord, SeasonDrawService
from beta_engine.application.season_match_service import MatchValidationIssue, SeasonEventMatchPackage, SeasonMatchRecord, SeasonMatchService
from beta_engine.domain.tournaments.models import CalendarEvent

EventCompletionStatus = Literal["incomplete", "complete", "blocked"]
PlayerResultDrawType = Literal["qualification", "main", "both"]
PlayerReachedStage = Literal[
    "champion",
    "finalist",
    "semifinal",
    "quarterfinal",
    "round_of_16",
    "round_of_32",
    "round_of_64",
    "round_of_128",
    "qualification_winner",
    "qualification_final",
    "qualification_semifinal",
    "qualification_round",
    "main_draw_participant",
    "unknown",
]


class PlayerResultSummary(BaseModel):
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    seed_number: int | None = None
    entry_decision: str | None = None
    qualifier: bool = False
    wildcard: bool = False
    ranking_priority: int | None = None


class PlayerEventResult(BaseModel):
    player_id: str
    player_name: str | None = None
    country_code: str | None = None
    draw_type: PlayerResultDrawType
    entry_decision: str | None = None
    seed_number: int | None = None
    qualifier: bool = False
    reached_stage: PlayerReachedStage
    final_round_number: int | None = None
    eliminated_by_player_id: str | None = None
    eliminated_by_player_name: str | None = None
    last_match_id: str | None = None
    wins: int = 0
    losses: int = 0
    walkovers_received: int = 0
    byes_received: int = 0
    retired_or_walkover_loss: bool = False
    points_awarded: int = 0
    race_points_awarded: int = 0
    prize_money_awarded: float = 0


class MatchResultRef(BaseModel):
    match_id: str
    draw_type: Literal["qualification", "main"]
    round_number: int
    round_name: str
    bracket_position: int
    winner_player_id: str | None = None
    loser_player_id: str | None = None
    scoreline: str | None = None
    result_fingerprint: str | None = None


class EventResultSummary(BaseModel):
    event_id: str
    completion_status: EventCompletionStatus
    player_count: int = 0
    main_draw_player_count: int = 0
    qualification_player_count: int = 0
    completed_matches: int = 0
    incomplete_matches: int = 0
    champion_player_id: str | None = None
    finalist_player_id: str | None = None
    qualification_winner_count: int = 0
    ranking_points_awarded_total: int = 0
    race_points_awarded_total: int = 0
    validation_warning_count: int = 0
    validation_error_count: int = 0


class EventResultMetadata(BaseModel):
    event_id: str
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    build_fingerprint: str
    match_package_fingerprint: str | None = None
    draw_package_fingerprint: str | None = None
    calendar_event_fingerprint: str | None = None
    ranking_updates_implemented: bool = False
    points_awarding_implemented: bool = False
    persistence_path: str | None = None


class SeasonEventResultPackage(BaseModel):
    event_id: str
    season: str
    template_id: str
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = Field(default=None, ge=1900, le=2100)
    year_week: int | None = Field(default=None, ge=1, le=61)
    event_name: str | None = None
    category: str | None = None
    tour_level: str | None = None
    host_country: str | None = None
    seed: int
    dry_run: bool
    persisted: bool
    completion_status: EventCompletionStatus
    champion: PlayerResultSummary | None = None
    finalist: PlayerResultSummary | None = None
    semifinalists: list[PlayerResultSummary] = Field(default_factory=list)
    quarterfinalists: list[PlayerResultSummary] = Field(default_factory=list)
    qualification_winners: list[PlayerResultSummary] = Field(default_factory=list)
    player_results: list[PlayerEventResult] = Field(default_factory=list)
    match_result_refs: list[MatchResultRef] = Field(default_factory=list)
    summary: EventResultSummary
    metadata: EventResultMetadata
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)


class EventResultExtractRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False


class SeasonEventResultsRegistry(BaseModel):
    results_by_event_id: dict[str, SeasonEventResultPackage] = Field(default_factory=dict)


class SeasonEventResultPackageResult(BaseModel):
    result_package: SeasonEventResultPackage | None = None
    summary: EventResultSummary | None = None
    metadata: EventResultMetadata | None = None
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)
    result_package_exists: bool = False


@dataclass(slots=True)
class SeasonEventResultsService:
    """Extract and optionally persist event outcomes from persisted match packages."""

    match_service: SeasonMatchService
    draw_service: SeasonDrawService | None = None
    calendar_service: SeasonCalendarService | None = None
    results_path: Path = Path("config/world/season_event_results.json")

    def __post_init__(self) -> None:
        if not isinstance(self.results_path, Path):
            self.results_path = Path(self.results_path)
        if self.draw_service is None:
            self.draw_service = self.match_service.draw_service
        if self.calendar_service is None and self.draw_service is not None:
            self.calendar_service = self.draw_service.calendar_service

    def get_event_result(self, *, event_id: str) -> SeasonEventResultPackageResult:
        package = self._load_registry().results_by_event_id.get(event_id)
        if package is None:
            return SeasonEventResultPackageResult(result_package=None, result_package_exists=False)
        return SeasonEventResultPackageResult(
            result_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            result_package_exists=True,
        )

    def extract_event_result(self, *, event_id: str, request: EventResultExtractRequest) -> SeasonEventResultPackageResult:
        registry = self._load_registry()
        warnings: list[MatchValidationIssue] = []
        errors: list[MatchValidationIssue] = []
        if not request.dry_run and event_id in registry.results_by_event_id and not request.overwrite_existing:
            errors.append(self._issue("error", "result_already_exists", f"Event result package already exists for event '{event_id}'. Set overwrite_existing=true to replace only that event.", event_id=event_id))
            raise ValueError(errors[0].message)

        match_result = self.match_service.get_match_package(event_id=event_id)
        if match_result.match_package is None:
            raise ValueError(f"No persisted match package exists for event '{event_id}'. Persist and progress a match package first.")
        match_package = match_result.match_package
        if match_package.validation_errors:
            errors.extend(match_package.validation_errors)
            if not request.dry_run:
                raise ValueError("Persisted match package has validation errors; fix or regenerate matches before extracting results.")

        event = self._calendar_event(match_package)
        draw_package = self.draw_service.get_draw_package(event_id=event_id).draw_package if self.draw_service else None
        player_meta = self._player_metadata(draw_package, match_package)
        completion_status = self._completion_status(match_package)
        if completion_status == "incomplete":
            warnings.append(self._issue("warning", "event_incomplete", "event is incomplete; result package is a current-state summary", event_id=event_id))
        if completion_status == "blocked":
            warnings.append(self._issue("warning", "event_blocked", "event is blocked by unresolved source, qualifier, or BYE state", event_id=event_id))
        warnings.extend([
            self._issue("warning", "ranking_race_points_not_awarded", "ranking/race points are not awarded by event result extraction yet", event_id=event_id),
            self._issue("warning", "prize_money_not_awarded", "prize money is not awarded by event result extraction yet", event_id=event_id),
        ])
        if any(m.scoreline == "BYE" for m in self._all_matches(match_package)):
            warnings.append(self._issue("warning", "bye_auto_advances_present", "some matches are BYE auto-advance only", event_id=event_id))
        if any(m.status == "completed" and not m.scoreline for m in self._all_matches(match_package)):
            warnings.append(self._issue("warning", "scoreline_missing", "some completed matches are missing scorelines", event_id=event_id))
        if match_package.metadata.qualification_winners_promoted:
            warnings.append(self._issue("warning", "draw_package_not_mirrored", "qualifier promotions may be stored only in the match package; persisted draw package placeholders may not be mirrored", event_id=event_id))
        if match_package.qualification_matches and not match_package.metadata.qualification_winners_promoted:
            warnings.append(self._issue("warning", "qualification_promotion_may_be_partial", "qualification winner promotion may be partial or not yet performed", event_id=event_id))

        refs = self._match_refs(match_package)
        champion_match = self._final_match(match_package.main_draw_matches)
        champion = self._summary_for(champion_match.winner_player_id, player_meta, match_package) if champion_match and champion_match.status == "completed" and champion_match.winner_player_id else None
        finalist = self._summary_for(champion_match.loser_player_id, player_meta, match_package) if champion_match and champion_match.status == "completed" and champion_match.loser_player_id else None
        if completion_status == "complete" and champion is None:
            errors.append(self._issue("error", "main_draw_final_missing", "main draw final is missing or does not have a completed champion", event_id=event_id))

        semifinalists = self._loser_summaries_for_main_round(match_package, player_meta, offset_from_final=1)
        quarterfinalists = self._loser_summaries_for_main_round(match_package, player_meta, offset_from_final=2)
        qualification_winners = self._qualification_winner_summaries(match_package, player_meta)
        player_results = self._player_results(match_package, player_meta, champion_id=champion.player_id if champion else None, finalist_id=finalist.player_id if finalist else None)
        errors.extend(self._validate_player_results(event_id, player_results))

        completed = sum(1 for m in self._all_matches(match_package) if m.status == "completed")
        incomplete = sum(1 for m in self._all_matches(match_package) if m.status != "completed")
        summary = EventResultSummary(
            event_id=event_id,
            completion_status=completion_status,
            player_count=len(player_results),
            main_draw_player_count=len({p.player_id for p in player_results if p.draw_type in {"main", "both"}}),
            qualification_player_count=len({p.player_id for p in player_results if p.draw_type in {"qualification", "both"}}),
            completed_matches=completed,
            incomplete_matches=incomplete,
            champion_player_id=champion.player_id if champion else None,
            finalist_player_id=finalist.player_id if finalist else None,
            qualification_winner_count=len(qualification_winners),
            validation_warning_count=len(warnings),
            validation_error_count=len(errors),
        )
        build_fp = self._fingerprint({
            "event_id": event_id,
            "seed": request.seed,
            "match_package_fingerprint": match_package.metadata.build_fingerprint,
            "champion": champion.model_dump(mode="json") if champion else None,
            "finalist": finalist.model_dump(mode="json") if finalist else None,
            "player_results": [p.model_dump(mode="json") for p in player_results],
            "match_refs": [r.model_dump(mode="json") for r in refs],
        })
        package = SeasonEventResultPackage(
            event_id=event_id,
            season=match_package.season,
            template_id=match_package.template_id,
            season_week=match_package.season_week,
            calendar_year=match_package.calendar_year,
            year_week=match_package.year_week,
            event_name=event.event_name if event else None,
            category=event.category if event else None,
            tour_level=event.tour_level if event else None,
            host_country=event.host_country if event else None,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            completion_status=completion_status,
            champion=champion,
            finalist=finalist,
            semifinalists=semifinalists,
            quarterfinalists=quarterfinalists,
            qualification_winners=qualification_winners,
            player_results=player_results,
            match_result_refs=refs,
            summary=summary,
            metadata=EventResultMetadata(
                event_id=event_id,
                season=match_package.season,
                seed=request.seed,
                dry_run=request.dry_run,
                persisted=not request.dry_run,
                build_fingerprint=build_fp,
                match_package_fingerprint=match_package.metadata.build_fingerprint,
                draw_package_fingerprint=match_package.metadata.draw_package_fingerprint,
                calendar_event_fingerprint=draw_package.metadata.calendar_event_fingerprint if draw_package else None,
                persistence_path=None if request.dry_run else str(self.results_path),
            ),
            validation_warnings=warnings,
            validation_errors=errors,
        )
        # Refresh summary counts after package-level errors are finalized.
        package.summary.validation_warning_count = len(package.validation_warnings)
        package.summary.validation_error_count = len(package.validation_errors)
        if package.validation_errors and not request.dry_run:
            codes = ", ".join(issue.code for issue in package.validation_errors)
            raise ValueError(f"Event result validation errors block persistence: {codes}")
        if not request.dry_run:
            next_results = dict(registry.results_by_event_id)
            next_results[event_id] = package
            self._save_registry(SeasonEventResultsRegistry(results_by_event_id=next_results))
        return SeasonEventResultPackageResult(
            result_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            result_package_exists=not request.dry_run,
        )

    def _calendar_event(self, package: SeasonEventMatchPackage) -> CalendarEvent | None:
        if self.calendar_service is None:
            return None
        calendar = self.calendar_service.get_calendar(season=package.season).calendar
        if calendar is None:
            return None
        return next((event for event in calendar.events if event.event_id == package.event_id), None)

    @staticmethod
    def _player_metadata(draw_package: Any, match_package: SeasonEventMatchPackage) -> dict[str, dict[str, Any]]:
        meta: dict[str, dict[str, Any]] = {}
        if draw_package:
            brackets = [draw_package.qualification_draw, draw_package.main_draw]
            for bracket in [b for b in brackets if b is not None]:
                for slot in bracket.slots:
                    if slot.player_id:
                        entry = meta.setdefault(slot.player_id, {})
                        SeasonEventResultsService._merge_slot_meta(entry, slot)
                for seed in bracket.seeds:
                    entry = meta.setdefault(seed.player_id, {})
                    entry["seed_number"] = seed.seed_number
                    entry["ranking_priority"] = seed.ranking_priority
        for match in SeasonEventResultsService._all_matches(match_package):
            for player_id, name, country in ((match.top_player_id, match.top_player_name, match.top_country_code), (match.bottom_player_id, match.bottom_player_name, match.bottom_country_code)):
                if player_id:
                    entry = meta.setdefault(player_id, {})
                    entry.setdefault("player_name", name)
                    entry.setdefault("country_code", country)
        return meta

    @staticmethod
    def _merge_slot_meta(entry: dict[str, Any], slot: DrawSlotRecord) -> None:
        entry.setdefault("player_name", slot.player_name)
        entry.setdefault("country_code", slot.country_code)
        entry.setdefault("entry_decision", slot.entry_decision)
        if slot.seed_number is not None:
            entry["seed_number"] = slot.seed_number
        if slot.entry_decision == "accepted_qualification":
            entry["qualifier"] = True
        if slot.entry_decision == "wild_card_reserved":
            entry["wildcard"] = True

    @staticmethod
    def _completion_status(package: SeasonEventMatchPackage) -> EventCompletionStatus:
        main_final = SeasonEventResultsService._final_match(package.main_draw_matches)
        if main_final and main_final.status == "completed" and main_final.winner_player_id:
            return "complete"
        all_matches = SeasonEventResultsService._all_matches(package)
        pending = any(match.status == "pending" for match in all_matches)
        blocked = any(match.status in {"blocked_waiting_for_sources", "bye_auto_advance_pending"} for match in all_matches)
        if not pending and blocked:
            return "blocked"
        return "incomplete"

    @staticmethod
    def _match_refs(package: SeasonEventMatchPackage) -> list[MatchResultRef]:
        return [
            MatchResultRef(
                match_id=match.match_id,
                draw_type=match.draw_type,
                round_number=match.round_number,
                round_name=match.round_name,
                bracket_position=match.bracket_position,
                winner_player_id=match.winner_player_id,
                loser_player_id=match.loser_player_id,
                scoreline=match.scoreline,
                result_fingerprint=match.result_fingerprint,
            )
            for match in sorted(SeasonEventResultsService._all_matches(package), key=lambda m: (m.draw_type != "qualification", m.round_number, m.bracket_position, m.match_id))
        ]

    @staticmethod
    def _summary_for(player_id: str | None, player_meta: dict[str, dict[str, Any]], package: SeasonEventMatchPackage) -> PlayerResultSummary | None:
        if not player_id:
            return None
        meta = player_meta.get(player_id, {})
        qualifier = bool(meta.get("qualifier")) or any(m.draw_type == "qualification" and player_id in {m.top_player_id, m.bottom_player_id} for m in SeasonEventResultsService._all_matches(package))
        return PlayerResultSummary(
            player_id=player_id,
            player_name=meta.get("player_name"),
            country_code=meta.get("country_code"),
            seed_number=meta.get("seed_number"),
            entry_decision=meta.get("entry_decision"),
            qualifier=qualifier,
            wildcard=bool(meta.get("wildcard", False)),
            ranking_priority=meta.get("ranking_priority"),
        )

    @staticmethod
    def _loser_summaries_for_main_round(package: SeasonEventMatchPackage, player_meta: dict[str, dict[str, Any]], *, offset_from_final: int) -> list[PlayerResultSummary]:
        if not package.main_draw_matches:
            return []
        final_round = max(match.round_number for match in package.main_draw_matches)
        target_round = final_round - offset_from_final
        if target_round < 1:
            return []
        return [
            summary
            for summary in (SeasonEventResultsService._summary_for(match.loser_player_id, player_meta, package) for match in sorted(package.main_draw_matches, key=lambda m: (m.bracket_position, m.match_id)) if match.round_number == target_round and match.status == "completed")
            if summary is not None
        ]

    @staticmethod
    def _qualification_winner_summaries(package: SeasonEventMatchPackage, player_meta: dict[str, dict[str, Any]]) -> list[PlayerResultSummary]:
        if not package.qualification_matches:
            return []
        max_round = max(match.round_number for match in package.qualification_matches)
        return [
            summary
            for summary in (SeasonEventResultsService._summary_for(match.winner_player_id, player_meta, package) for match in sorted(package.qualification_matches, key=lambda m: (m.bracket_position, m.match_id)) if match.round_number == max_round and match.status == "completed")
            if summary is not None
        ]

    @staticmethod
    def _player_results(package: SeasonEventMatchPackage, player_meta: dict[str, dict[str, Any]], *, champion_id: str | None, finalist_id: str | None) -> list[PlayerEventResult]:
        stats: dict[str, dict[str, Any]] = {}
        qual_final_round = max((m.round_number for m in package.qualification_matches), default=0)
        main_final_round = max((m.round_number for m in package.main_draw_matches), default=0)
        main_draw_size = max((2 ** main_final_round), 1) if main_final_round else 0
        qual_winners = {m.winner_player_id for m in package.qualification_matches if qual_final_round and m.round_number == qual_final_round and m.status == "completed" and m.winner_player_id}
        for match in sorted(SeasonEventResultsService._all_matches(package), key=lambda m: (m.draw_type != "qualification", m.round_number, m.bracket_position, m.match_id)):
            for player_id, name, country in ((match.top_player_id, match.top_player_name, match.top_country_code), (match.bottom_player_id, match.bottom_player_name, match.bottom_country_code)):
                if not player_id:
                    continue
                item = stats.setdefault(player_id, {"player_id": player_id, "draws": set(), "wins": 0, "losses": 0, "byes": 0, "walkovers": 0, "last_match_id": None, "last_round": None, "last_draw": match.draw_type, "eliminated_by": None, "stage": "unknown"})
                item["draws"].add(match.draw_type)
                meta = player_meta.setdefault(player_id, {})
                meta.setdefault("player_name", name)
                meta.setdefault("country_code", country)
            if match.status != "completed" or not match.winner_player_id:
                continue
            winner = stats.setdefault(match.winner_player_id, {"player_id": match.winner_player_id, "draws": {match.draw_type}, "wins": 0, "losses": 0, "byes": 0, "walkovers": 0, "last_match_id": None, "last_round": None, "last_draw": match.draw_type, "eliminated_by": None, "stage": "unknown"})
            winner["draws"].add(match.draw_type)
            winner["last_match_id"] = match.match_id
            winner["last_round"] = match.round_number
            winner["last_draw"] = match.draw_type
            if match.scoreline == "BYE":
                winner["byes"] += 1
            elif match.simulated_result and match.simulated_result.walkover:
                winner["walkovers"] += 1
            else:
                winner["wins"] += 1
            if match.draw_type == "qualification" and match.round_number == qual_final_round:
                winner["stage"] = "qualification_winner"
            if match.draw_type == "main" and match.winner_player_id == champion_id:
                winner["stage"] = "champion"
            if match.loser_player_id:
                loser = stats.setdefault(match.loser_player_id, {"player_id": match.loser_player_id, "draws": {match.draw_type}, "wins": 0, "losses": 0, "byes": 0, "walkovers": 0, "last_match_id": None, "last_round": None, "last_draw": match.draw_type, "eliminated_by": None, "stage": "unknown"})
                loser["draws"].add(match.draw_type)
                loser["losses"] += 1
                loser["last_match_id"] = match.match_id
                loser["last_round"] = match.round_number
                loser["last_draw"] = match.draw_type
                loser["eliminated_by"] = match.winner_player_id
                if match.draw_type == "main":
                    loser["stage"] = SeasonEventResultsService._main_loss_stage(match.round_number, main_final_round, main_draw_size)
                else:
                    loser["stage"] = SeasonEventResultsService._qualification_loss_stage(match.round_number, qual_final_round)
        results: list[PlayerEventResult] = []
        for player_id, item in stats.items():
            draws = item["draws"]
            draw_type: PlayerResultDrawType = "both" if draws == {"qualification", "main"} else ("main" if "main" in draws else "qualification")
            meta = player_meta.get(player_id, {})
            qualifier = bool(meta.get("qualifier")) or player_id in qual_winners or draw_type == "both"
            stage = item["stage"]
            if draw_type in {"main", "both"} and stage in {"qualification_winner", "qualification_final", "qualification_semifinal", "qualification_round", "unknown"}:
                stage = "main_draw_participant"
            if player_id == champion_id:
                stage = "champion"
            elif player_id == finalist_id:
                stage = "finalist"
            eliminated_by = item["eliminated_by"]
            eliminated_meta = player_meta.get(eliminated_by or "", {})
            results.append(PlayerEventResult(
                player_id=player_id,
                player_name=meta.get("player_name"),
                country_code=meta.get("country_code"),
                draw_type=draw_type,
                entry_decision=meta.get("entry_decision"),
                seed_number=meta.get("seed_number"),
                qualifier=qualifier,
                reached_stage=stage,
                final_round_number=item["last_round"],
                eliminated_by_player_id=eliminated_by,
                eliminated_by_player_name=eliminated_meta.get("player_name"),
                last_match_id=item["last_match_id"],
                wins=item["wins"],
                losses=item["losses"],
                walkovers_received=item["walkovers"],
                byes_received=item["byes"],
                retired_or_walkover_loss=False,
            ))
        return sorted(results, key=lambda p: (SeasonEventResultsService._stage_sort(p.reached_stage), p.player_name or "", p.player_id))

    @staticmethod
    def _main_loss_stage(round_number: int, final_round: int, draw_size: int) -> PlayerReachedStage:
        if round_number == final_round:
            return "finalist"
        if round_number == final_round - 1:
            return "semifinal"
        if round_number == final_round - 2:
            return "quarterfinal"
        round_of = max(2, draw_size // (2 ** max(0, round_number - 1))) if draw_size else 0
        if round_of in {16, 32, 64, 128}:
            return f"round_of_{round_of}"  # type: ignore[return-value]
        return "main_draw_participant"

    @staticmethod
    def _qualification_loss_stage(round_number: int, final_round: int) -> PlayerReachedStage:
        if round_number == final_round:
            return "qualification_final"
        if round_number == final_round - 1:
            return "qualification_semifinal"
        return "qualification_round"

    @staticmethod
    def _validate_player_results(event_id: str, player_results: list[PlayerEventResult]) -> list[MatchValidationIssue]:
        errors: list[MatchValidationIssue] = []
        for result in player_results:
            if result.losses > 1:
                errors.append(SeasonEventResultsService._issue("error", "player_multiple_losses", "player appears with impossible multiple losses", event_id=event_id, player_id=result.player_id))
        return errors

    @staticmethod
    def _stage_sort(stage: str) -> int:
        order = {
            "champion": 0,
            "finalist": 1,
            "semifinal": 2,
            "quarterfinal": 3,
            "round_of_16": 4,
            "round_of_32": 5,
            "round_of_64": 6,
            "round_of_128": 7,
            "main_draw_participant": 8,
            "qualification_winner": 9,
            "qualification_final": 10,
            "qualification_semifinal": 11,
            "qualification_round": 12,
            "unknown": 99,
        }
        return order.get(stage, 99)

    @staticmethod
    def _final_match(matches: list[SeasonMatchRecord]) -> SeasonMatchRecord | None:
        if not matches:
            return None
        max_round = max(match.round_number for match in matches)
        finals = [match for match in matches if match.round_number == max_round]
        return sorted(finals, key=lambda m: (m.bracket_position, m.match_id))[0] if finals else None

    @staticmethod
    def _all_matches(package: SeasonEventMatchPackage) -> list[SeasonMatchRecord]:
        return package.qualification_matches + package.main_draw_matches

    def _load_registry(self) -> SeasonEventResultsRegistry:
        if not self.results_path.exists():
            return SeasonEventResultsRegistry()
        return SeasonEventResultsRegistry.model_validate(json.loads(self.results_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonEventResultsRegistry) -> None:
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.results_path.with_suffix(f"{self.results_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.results_path)

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(severity: Literal["warning", "error"], code: str, message: str, *, event_id: str | None = None, match_id: str | None = None, player_id: str | None = None, field: str | None = None) -> MatchValidationIssue:
        return MatchValidationIssue(severity=severity, code=code, message=message, event_id=event_id, match_id=match_id, player_id=player_id, field=field)
