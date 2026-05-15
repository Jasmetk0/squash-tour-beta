"""Application service for deterministic event match records and simulation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_draw_service import DrawBracket, DrawSlotRecord, SeasonDrawService, SeasonEventDrawPackage
from beta_engine.application.season_player_bootstrap_service import InitialPoolSeasonBootstrapService, SeasonActivePlayer
from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchParticipantContext
from beta_engine.domain.players.models import Player

MatchDrawType = Literal["qualification", "main"]
MatchStatus = Literal[
    "pending",
    "blocked_waiting_for_sources",
    "bye_auto_advance_pending",
    "completed",
    "walkover_placeholder",
]
MatchValidationSeverity = Literal["warning", "error"]
ProgressionStatusValue = Literal["not_started", "in_progress", "completed", "not_applicable"]
EventProgressionStatusValue = Literal["not_started", "in_progress", "completed", "blocked"]
ProgressionAction = Literal["process_byes", "refresh_status", "simulate_round", "simulate_draw", "promote_qualifiers", "advance_completed"]



class MatchValidationIssue(BaseModel):
    severity: MatchValidationSeverity
    code: str
    message: str
    event_id: str | None = None
    match_id: str | None = None
    player_id: str | None = None
    field: str | None = None


class MatchSimulationResult(BaseModel):
    match_id: str
    winner_player_id: str
    loser_player_id: str
    scoreline: str
    games: list[dict[str, Any]] = Field(default_factory=list)
    points_summary: dict[str, Any] = Field(default_factory=dict)
    retired: bool = False
    walkover: bool = False
    simulation_fingerprint: str
    seed: int


class TournamentProgressionStatus(BaseModel):
    event_id: str
    season: str
    qualification_status: ProgressionStatusValue
    main_draw_status: ProgressionStatusValue
    event_status: EventProgressionStatusValue
    qualification_winners_ready: bool = False
    qualification_winners_promoted: bool = False
    pending_matches: int = 0
    blocked_matches: int = 0
    completed_matches: int = 0
    bye_auto_advances_pending: int = 0
    champion_player_id: str | None = None
    champion_name: str | None = None
    finalist_player_id: str | None = None
    finalist_name: str | None = None
    warnings: list[MatchValidationIssue] = Field(default_factory=list)
    errors: list[MatchValidationIssue] = Field(default_factory=list)


class ProgressionCommandResult(BaseModel):
    event_id: str
    action: ProgressionAction
    match_package: SeasonEventMatchPackage
    progression_status: TournamentProgressionStatus
    changed_match_ids: list[str] = Field(default_factory=list)
    promoted_player_ids: list[str] = Field(default_factory=list)
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeasonMatchRecord(BaseModel):
    match_id: str
    event_id: str
    draw_type: MatchDrawType
    round_number: int = Field(ge=1)
    round_name: str
    bracket_position: int = Field(ge=1)
    top_slot_id: str
    bottom_slot_id: str
    top_source: str
    bottom_source: str
    top_player_id: str | None = None
    bottom_player_id: str | None = None
    top_player_name: str | None = None
    bottom_player_name: str | None = None
    top_country_code: str | None = None
    bottom_country_code: str | None = None
    status: MatchStatus
    winner_player_id: str | None = None
    loser_player_id: str | None = None
    scoreline: str | None = None
    simulated_result: MatchSimulationResult | None = None
    winner_to_match_id: str | None = None
    source_draw_fingerprint: str
    generated_fingerprint: str
    result_fingerprint: str | None = None
    simulation_seed: int | None = None
    result_notes: str | None = None


class MatchPackageSummary(BaseModel):
    event_id: str | None = None
    total_matches: int = 0
    qualification_matches: int = 0
    main_draw_matches: int = 0
    pending_matches: int = 0
    completed_matches: int = 0
    blocked_matches: int = 0
    bye_auto_advances: int = 0
    validation_warning_count: int = 0
    validation_error_count: int = 0


class MatchPackageMetadata(BaseModel):
    event_id: str
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    build_fingerprint: str
    draw_package_fingerprint: str
    active_players_fingerprint: str
    match_engine_version: str | None = "match_engine_v1"
    persistence_path: str | None = None
    ranking_updates_implemented: bool = False
    qualification_winners_promoted: bool = False


class SeasonEventMatchPackage(BaseModel):
    event_id: str
    season: str
    template_id: str
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = Field(default=None, ge=1900, le=2100)
    year_week: int | None = Field(default=None, ge=1, le=53)
    seed: int
    dry_run: bool
    persisted: bool
    qualification_matches: list[SeasonMatchRecord] = Field(default_factory=list)
    main_draw_matches: list[SeasonMatchRecord] = Field(default_factory=list)
    summary: MatchPackageSummary
    metadata: MatchPackageMetadata
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)


class SeasonEventMatchPackageResult(BaseModel):
    match_package: SeasonEventMatchPackage | None = None
    summary: MatchPackageSummary = Field(default_factory=MatchPackageSummary)
    metadata: MatchPackageMetadata | None = None
    validation_warnings: list[MatchValidationIssue] = Field(default_factory=list)
    validation_errors: list[MatchValidationIssue] = Field(default_factory=list)
    match_package_exists: bool = False


class MatchPackageGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False


class MatchSimulateRequest(BaseModel):
    seed: int = 12345


class ProgressionCommandRequest(BaseModel):
    seed: int = 12345


class SimulateRoundRequest(BaseModel):
    seed: int = 12345
    draw_type: MatchDrawType
    round_number: int = Field(ge=1)


class SimulateDrawRequest(BaseModel):
    seed: int = 12345
    draw_type: MatchDrawType


class SeasonMatchesRegistry(BaseModel):
    matches_by_event_id: dict[str, SeasonEventMatchPackage] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonMatchService:
    draw_service: SeasonDrawService
    active_players_service: InitialPoolSeasonBootstrapService
    matches_path: Path = Path("config/world/season_matches.json")

    def __post_init__(self) -> None:
        if not isinstance(self.matches_path, Path):
            self.matches_path = Path(self.matches_path)

    def get_match_package(self, *, event_id: str) -> SeasonEventMatchPackageResult:
        package = self._load_registry().matches_by_event_id.get(event_id)
        if package is None:
            return SeasonEventMatchPackageResult(match_package=None, match_package_exists=False)
        return SeasonEventMatchPackageResult(
            match_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            match_package_exists=True,
        )

    def generate_match_package(self, *, event_id: str, request: MatchPackageGenerateRequest) -> SeasonEventMatchPackageResult:
        registry = self._load_registry()
        if not request.dry_run and event_id in registry.matches_by_event_id and not request.overwrite_existing:
            raise ValueError(f"Match package already exists for event '{event_id}'. Set overwrite_existing=true to replace only that event.")

        draw_result = self.draw_service.get_draw_package(event_id=event_id)
        if draw_result.draw_package is None:
            raise ValueError(f"No persisted draw package exists for event '{event_id}'. Persist a draw package first.")
        draw_package = draw_result.draw_package
        if draw_package.validation_errors:
            raise ValueError("Persisted draw package has validation errors; fix or regenerate the draw before generating matches.")

        players = self._active_players_for_season(draw_package.season)
        players_by_id = {player.player_id: player for player in players}
        warnings = [
            self._issue("warning", "ranking_race_not_implemented", "ranking/race updates are not implemented by match simulation yet", event_id=event_id),
            self._issue("warning", "walkovers_withdrawals_not_implemented", "walkovers/withdrawals are not implemented in this match foundation", event_id=event_id),
        ]
        errors: list[MatchValidationIssue] = []

        qualification_matches = self._records_from_bracket(draw_package=draw_package, bracket=draw_package.qualification_draw, draw_type="qualification", players_by_id=players_by_id, warnings=warnings, errors=errors)
        main_draw_matches = self._records_from_bracket(draw_package=draw_package, bracket=draw_package.main_draw, draw_type="main", players_by_id=players_by_id, warnings=warnings, errors=errors)
        all_matches = qualification_matches + main_draw_matches
        seen: set[str] = set()
        for match in all_matches:
            if match.match_id in seen:
                errors.append(self._issue("error", "duplicate_match_id", f"duplicate match_id '{match.match_id}'", event_id=event_id, match_id=match.match_id, field="match_id"))
            seen.add(match.match_id)

        draw_fp = draw_package.metadata.build_fingerprint
        active_fp = self._active_players_fingerprint(players)
        build_fp = self._fingerprint({
            "event_id": event_id,
            "seed": request.seed,
            "draw_package_fingerprint": draw_fp,
            "active_players_fingerprint": active_fp,
            "qualification_matches": [m.model_dump(mode="json", exclude={"generated_fingerprint"}) for m in qualification_matches],
            "main_draw_matches": [m.model_dump(mode="json", exclude={"generated_fingerprint"}) for m in main_draw_matches],
        })
        if errors and not request.dry_run:
            codes = ", ".join(issue.code for issue in errors)
            raise ValueError(f"Match package validation errors block persistence: {codes}")

        package = SeasonEventMatchPackage(
            event_id=draw_package.event_id,
            season=draw_package.season,
            template_id=draw_package.template_id,
            season_week=draw_package.season_week,
            calendar_year=draw_package.calendar_year,
            year_week=draw_package.year_week,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            qualification_matches=qualification_matches,
            main_draw_matches=main_draw_matches,
            summary=self._summary(event_id=event_id, qualification_matches=qualification_matches, main_draw_matches=main_draw_matches, warnings=warnings, errors=errors),
            metadata=MatchPackageMetadata(
                event_id=event_id,
                season=draw_package.season,
                seed=request.seed,
                dry_run=request.dry_run,
                persisted=not request.dry_run,
                build_fingerprint=build_fp,
                draw_package_fingerprint=draw_fp,
                active_players_fingerprint=active_fp,
                persistence_path=None if request.dry_run else str(self.matches_path),
            ),
            validation_warnings=warnings,
            validation_errors=errors,
        )
        if not request.dry_run:
            next_packages = dict(registry.matches_by_event_id)
            next_packages[event_id] = package
            self._save_registry(SeasonMatchesRegistry(matches_by_event_id=next_packages))
        return SeasonEventMatchPackageResult(match_package=package, summary=package.summary, metadata=package.metadata, validation_warnings=warnings, validation_errors=errors, match_package_exists=not request.dry_run)

    def simulate_match(self, *, event_id: str, match_id: str, request: MatchSimulateRequest) -> SeasonEventMatchPackageResult:
        registry, package = self._persisted_package(event_id)
        match = self._find_match(package, match_id)
        if match.status != "pending":
            raise ValueError(f"Selected match '{match_id}' is not pending.")
        if match.top_player_id is None or match.bottom_player_id is None:
            raise ValueError(f"Selected match '{match_id}' does not have two known players.")
        players = self._active_players_for_season(package.season)
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in players}
        players_by_id = {player.player_id: player for player in players}
        try:
            top = players_by_id[match.top_player_id]
            bottom = players_by_id[match.bottom_player_id]
        except KeyError as exc:
            raise ValueError(f"Player ID '{exc.args[0]}' was not found in active season players for season '{package.season}'.") from exc

        sim_seed = self._simulation_seed(base_seed=request.seed, event_id=event_id, match_id=match_id)
        context = MatchContext(
            match_id=match_id,
            player_a=MatchParticipantContext(player=self._to_domain_player(top)),
            player_b=MatchParticipantContext(player=self._to_domain_player(bottom)),
        )
        domain_result = MatchEngine(rng=DeterministicRng(sim_seed)).simulate(context)
        result_payload = domain_result.model_dump(mode="json")
        result_fp = self._fingerprint({"event_id": event_id, "match_id": match_id, "simulation_seed": sim_seed, "players": [match.top_player_id, match.bottom_player_id], "result": result_payload})
        simulated = MatchSimulationResult(
            match_id=match_id,
            winner_player_id=domain_result.winner_player_id,
            loser_player_id=domain_result.loser_player_id,
            scoreline=self._scoreline(domain_result.winner_player_id, domain_result.sets),
            games=[set_result.model_dump(mode="json") for set_result in domain_result.sets],
            points_summary={"sets_won": domain_result.sets_won, "best_of": domain_result.best_of, "games_to": domain_result.games_to, "win_by": domain_result.win_by},
            retired=domain_result.retired_player_id is not None,
            walkover=False,
            simulation_fingerprint=result_fp,
            seed=sim_seed,
        )
        match.winner_player_id = domain_result.winner_player_id
        match.loser_player_id = domain_result.loser_player_id
        match.scoreline = simulated.scoreline
        match.simulated_result = simulated
        match.result_fingerprint = result_fp
        match.simulation_seed = sim_seed
        match.status = "completed"
        match.result_notes = "ranking/race updates not implemented"
        self._propagate_winner(package, completed=match)
        self._refresh_package(package)
        self._assert_no_ranking_updates(before_points, self._active_players_for_season(package.season))
        packages = dict(registry.matches_by_event_id)
        packages[event_id] = package
        self._save_registry(SeasonMatchesRegistry(matches_by_event_id=packages))
        return SeasonEventMatchPackageResult(match_package=package, summary=package.summary, metadata=package.metadata, validation_warnings=package.validation_warnings, validation_errors=package.validation_errors, match_package_exists=True)

    def simulate_next_match(self, *, event_id: str, request: MatchSimulateRequest) -> SeasonEventMatchPackageResult:
        _, package = self._persisted_package(event_id)
        pending = sorted((m for m in self._all_matches(package) if m.status == "pending" and m.top_player_id and m.bottom_player_id), key=lambda m: (m.draw_type != "qualification", m.round_number, m.bracket_position, m.match_id))
        if not pending:
            raise ValueError(f"No pending match with two known players exists for event '{event_id}'.")
        return self.simulate_match(event_id=event_id, match_id=pending[0].match_id, request=request)

    def get_progression_status(self, *, event_id: str) -> TournamentProgressionStatus:
        _, package = self._persisted_package(event_id)
        return self._progression_status(package)

    def process_byes(self, *, event_id: str, request: ProgressionCommandRequest) -> ProgressionCommandResult:
        registry, package = self._persisted_package(event_id)
        changed: list[str] = []
        warnings: list[MatchValidationIssue] = []
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in self._active_players_for_season(package.season)}
        for match in self._all_matches(package):
            if match.status != "bye_auto_advance_pending":
                continue
            top_known = match.top_player_id is not None
            bottom_known = match.bottom_player_id is not None
            if top_known == bottom_known:
                warnings.append(self._issue("warning", "bye_auto_advance_ambiguous", "BYE auto-advance requires exactly one known player", event_id=event_id, match_id=match.match_id))
                continue
            winner_id = match.top_player_id if top_known else match.bottom_player_id
            match.winner_player_id = winner_id
            match.loser_player_id = None
            match.scoreline = "BYE"
            match.status = "completed"
            match.result_notes = "automatic BYE advance"
            match.simulation_seed = self._simulation_seed(base_seed=request.seed, event_id=event_id, match_id=match.match_id)
            match.result_fingerprint = self._fingerprint({"action": "process_byes", "event_id": event_id, "match_id": match.match_id, "winner_player_id": winner_id, "scoreline": "BYE", "seed": match.simulation_seed})
            changed.append(match.match_id)
            self._propagate_winner(package, completed=match)
        self._refresh_completed_propagation(package, changed=changed)
        return self._save_progression_result(registry, package, action="process_byes", changed_match_ids=changed, promoted_player_ids=[], warnings=warnings, errors=[], before_points=before_points)

    def refresh_progression(self, *, event_id: str, request: ProgressionCommandRequest) -> ProgressionCommandResult:
        registry, package = self._persisted_package(event_id)
        changed: list[str] = []
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in self._active_players_for_season(package.season)}
        self._refresh_completed_propagation(package, changed=changed)
        return self._save_progression_result(registry, package, action="advance_completed", changed_match_ids=changed, promoted_player_ids=[], warnings=[], errors=[], before_points=before_points)

    def promote_qualifiers(self, *, event_id: str, request: ProgressionCommandRequest) -> ProgressionCommandResult:
        registry, package = self._persisted_package(event_id)
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in self._active_players_for_season(package.season)}
        changed: list[str] = []
        promoted: list[str] = []
        warnings: list[MatchValidationIssue] = []
        errors: list[MatchValidationIssue] = []
        if not package.qualification_matches:
            warnings.append(self._issue("warning", "qualification_not_applicable", "event has no qualification draw", event_id=event_id))
            return self._save_progression_result(registry, package, action="promote_qualifiers", changed_match_ids=changed, promoted_player_ids=promoted, warnings=warnings, errors=errors, before_points=before_points)
        final_round = max(match.round_number for match in package.qualification_matches)
        finals = sorted((m for m in package.qualification_matches if m.round_number == final_round), key=lambda m: (m.bracket_position, m.match_id))
        if not finals or any(m.status != "completed" or not m.winner_player_id for m in finals):
            warnings.append(self._issue("warning", "qualification_winners_incomplete", "qualification final-round winners are not complete; no qualifier placeholders were promoted", event_id=event_id))
            return self._save_progression_result(registry, package, action="promote_qualifiers", changed_match_ids=changed, promoted_player_ids=promoted, warnings=warnings, errors=errors, before_points=before_points)
        winners = finals
        draw_result = self.draw_service.get_draw_package(event_id=event_id)
        draw_package = draw_result.draw_package
        placeholder_slots: set[str] = set()
        placeholder_order: dict[str, int] = {}
        if draw_package and draw_package.main_draw:
            for placeholder in sorted(draw_package.main_draw.qualifier_placeholders, key=lambda p: (p.qualifier_index, p.bracket_position, p.slot_id)):
                placeholder_slots.add(placeholder.slot_id)
                placeholder_order[placeholder.slot_id] = placeholder.qualifier_index
        slots: list[tuple[int, SeasonMatchRecord, Literal["top", "bottom"]]] = []
        for match in sorted(package.main_draw_matches, key=lambda m: (m.round_number, m.bracket_position, m.match_id)):
            top_is_placeholder = match.top_source.startswith("SLOT:") and ((match.top_slot_id in placeholder_slots) if placeholder_slots else match.top_player_id is None)
            bottom_is_placeholder = match.bottom_source.startswith("SLOT:") and ((match.bottom_slot_id in placeholder_slots) if placeholder_slots else match.bottom_player_id is None)
            if top_is_placeholder:
                slots.append((placeholder_order.get(match.top_slot_id, len(slots) + 1), match, "top"))
            if bottom_is_placeholder:
                slots.append((placeholder_order.get(match.bottom_slot_id, len(slots) + 1), match, "bottom"))
        slots.sort(key=lambda item: (item[0], item[1].round_number, item[1].bracket_position, item[2]))
        if len(winners) < len(slots):
            warnings.append(self._issue("warning", "not_enough_qualification_winners", "not enough qualification winners are known for all qualifier placeholders; no placeholders were promoted", event_id=event_id))
            return self._save_progression_result(registry, package, action="promote_qualifiers", changed_match_ids=changed, promoted_player_ids=promoted, warnings=warnings, errors=errors, before_points=before_points)
        for source_match, (_, target, side) in zip(winners, slots, strict=False):
            existing = getattr(target, f"{side}_player_id")
            if existing and existing != source_match.winner_player_id:
                errors.append(self._issue("error", "qualifier_placeholder_conflict", "qualifier placeholder already contains a different player", event_id=event_id, match_id=target.match_id, player_id=existing, field=f"{side}_player_id"))
                continue
            if not existing:
                self._assign_side(target, side, source_match)
                target.result_notes = self._append_note(target.result_notes, f"qualifier promoted from {source_match.match_id}")
                changed.append(target.match_id)
                promoted.append(source_match.winner_player_id or "")
            if target.top_player_id and target.bottom_player_id and target.status == "blocked_waiting_for_sources":
                target.status = "pending"
                if target.match_id not in changed:
                    changed.append(target.match_id)
        if promoted:
            package.metadata.qualification_winners_promoted = True
            warnings.append(self._issue("warning", "draw_package_not_mirrored", "qualifier promotions are stored in the match package; persisted draw package placeholders are not rewritten in this slice", event_id=event_id))
        return self._save_progression_result(registry, package, action="promote_qualifiers", changed_match_ids=changed, promoted_player_ids=[p for p in promoted if p], warnings=warnings, errors=errors, before_points=before_points)

    def simulate_round(self, *, event_id: str, request: SimulateRoundRequest) -> ProgressionCommandResult:
        registry, package = self._persisted_package(event_id)
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in self._active_players_for_season(package.season)}
        changed: list[str] = []
        self._refresh_completed_propagation(package, changed=changed)
        matches = sorted((m for m in self._all_matches(package) if m.draw_type == request.draw_type and m.round_number == request.round_number and m.status == "pending" and m.top_player_id and m.bottom_player_id), key=lambda m: (m.bracket_position, m.match_id))
        warnings: list[MatchValidationIssue] = []
        if not matches:
            warnings.append(self._issue("warning", "no_pending_round_matches", "no pending matches with two known players exist for the selected draw round", event_id=event_id, field=f"{request.draw_type}:{request.round_number}"))
        for match in matches:
            self._simulate_match_in_package(package=package, match=match, seed=request.seed)
            changed.append(match.match_id)
            self._propagate_winner(package, completed=match)
        self._refresh_completed_propagation(package, changed=changed)
        return self._save_progression_result(registry, package, action="simulate_round", changed_match_ids=changed, promoted_player_ids=[], warnings=warnings, errors=[], before_points=before_points)

    def simulate_draw(self, *, event_id: str, request: SimulateDrawRequest) -> ProgressionCommandResult:
        registry, package = self._persisted_package(event_id)
        before_points = {p.player_id: (p.ranking_points, p.race_points) for p in self._active_players_for_season(package.season)}
        changed: list[str] = []
        warnings: list[MatchValidationIssue] = []
        rounds = sorted({m.round_number for m in self._all_matches(package) if m.draw_type == request.draw_type})
        for round_number in rounds:
            self._refresh_completed_propagation(package, changed=changed)
            matches = sorted((m for m in self._all_matches(package) if m.draw_type == request.draw_type and m.round_number == round_number and m.status == "pending" and m.top_player_id and m.bottom_player_id), key=lambda m: (m.bracket_position, m.match_id))
            for match in matches:
                self._simulate_match_in_package(package=package, match=match, seed=request.seed)
                changed.append(match.match_id)
                self._propagate_winner(package, completed=match)
            blocked = [m for m in self._all_matches(package) if m.draw_type == request.draw_type and m.round_number == round_number and m.status in {"blocked_waiting_for_sources", "bye_auto_advance_pending"}]
            if blocked:
                warnings.append(self._issue("warning", "simulate_draw_stopped_blocked", "simulate draw stopped because the selected draw still has blocked or BYE-pending matches", event_id=event_id, field=f"{request.draw_type}:{round_number}"))
                break
        return self._save_progression_result(registry, package, action="simulate_draw", changed_match_ids=changed, promoted_player_ids=[], warnings=warnings, errors=[], before_points=before_points)

    def _records_from_bracket(self, *, draw_package: SeasonEventDrawPackage, bracket: DrawBracket | None, draw_type: MatchDrawType, players_by_id: dict[str, SeasonActivePlayer], warnings: list[MatchValidationIssue], errors: list[MatchValidationIssue]) -> list[SeasonMatchRecord]:
        if bracket is None:
            return []
        slots_by_id = {slot.slot_id: slot for slot in bracket.slots}
        node_to_match_id = {self._node_ref_from_match_id(match.match_id): match.match_id for round_ in bracket.rounds for match in round_.matches}
        records: list[SeasonMatchRecord] = []
        for round_ in bracket.rounds:
            for draw_match in round_.matches:
                top_slot = slots_by_id.get(draw_match.top_slot_id)
                bottom_slot = slots_by_id.get(draw_match.bottom_slot_id)
                top = self._slot_player(top_slot, draw_match.top_source, players_by_id)
                bottom = self._slot_player(bottom_slot, draw_match.bottom_source, players_by_id)
                status = self._initial_status(top_slot=top_slot, bottom_slot=bottom_slot, top_player_id=top["player_id"], bottom_player_id=bottom["player_id"], top_source=draw_match.top_source, bottom_source=draw_match.bottom_source)
                if status == "bye_auto_advance_pending":
                    warnings.append(self._issue("warning", "bye_auto_advances_pending", "BYE auto-advances are pending and not processed automatically", event_id=draw_package.event_id, match_id=draw_match.match_id))
                if status == "blocked_waiting_for_sources":
                    warnings.append(self._issue("warning", "blocked_matches_waiting_for_sources", "match is waiting for source winners or unresolved placeholders", event_id=draw_package.event_id, match_id=draw_match.match_id))
                if draw_type == "main" and ((top_slot and top_slot.is_qualifier_placeholder) or (bottom_slot and bottom_slot.is_qualifier_placeholder)):
                    warnings.append(self._issue("warning", "qualification_promotion_not_connected", "qualification winner promotion is not connected yet", event_id=draw_package.event_id, match_id=draw_match.match_id))
                winner_to = node_to_match_id.get(draw_match.winner_to_match_id or "", draw_match.winner_to_match_id)
                payload = {
                    "match_id": draw_match.match_id,
                    "event_id": draw_package.event_id,
                    "draw_type": draw_type,
                    "round_number": draw_match.round_number,
                    "round_name": round_.round_name,
                    "bracket_position": draw_match.bracket_position,
                    "top_slot_id": draw_match.top_slot_id,
                    "bottom_slot_id": draw_match.bottom_slot_id,
                    "top_source": draw_match.top_source,
                    "bottom_source": draw_match.bottom_source,
                    "top_player_id": top["player_id"],
                    "bottom_player_id": bottom["player_id"],
                    "top_player_name": top["player_name"],
                    "bottom_player_name": bottom["player_name"],
                    "top_country_code": top["country_code"],
                    "bottom_country_code": bottom["country_code"],
                    "status": status,
                    "winner_to_match_id": winner_to,
                    "source_draw_fingerprint": bracket.generated_fingerprint,
                }
                payload["generated_fingerprint"] = self._fingerprint(payload)
                records.append(SeasonMatchRecord.model_validate(payload))
        return records

    @staticmethod
    def _slot_player(slot: DrawSlotRecord | None, source: str, players_by_id: dict[str, SeasonActivePlayer]) -> dict[str, str | None]:
        if slot is None or not source.startswith("SLOT:") or slot.is_bye or slot.is_qualifier_placeholder or slot.player_id is None:
            return {"player_id": None, "player_name": None, "country_code": None}
        player = players_by_id.get(slot.player_id)
        return {"player_id": slot.player_id, "player_name": player.name if player else slot.player_name, "country_code": player.country_code if player else slot.country_code}

    @staticmethod
    def _initial_status(*, top_slot: DrawSlotRecord | None, bottom_slot: DrawSlotRecord | None, top_player_id: str | None, bottom_player_id: str | None, top_source: str, bottom_source: str) -> MatchStatus:
        top_bye = bool(top_slot and top_slot.is_bye)
        bottom_bye = bool(bottom_slot and bottom_slot.is_bye)
        if top_bye or bottom_bye:
            return "bye_auto_advance_pending"
        if top_source.startswith("R") or bottom_source.startswith("R"):
            return "blocked_waiting_for_sources"
        if top_player_id and bottom_player_id:
            return "pending"
        return "blocked_waiting_for_sources"

    def _propagate_winner(self, package: SeasonEventMatchPackage, *, completed: SeasonMatchRecord) -> None:
        if not completed.winner_to_match_id or not completed.winner_player_id:
            return
        target = next((m for m in self._all_matches(package) if m.match_id == completed.winner_to_match_id), None)
        if target is None:
            package.validation_warnings.append(self._issue("warning", "winner_target_not_found", "completed match winner target was not found", event_id=package.event_id, match_id=completed.match_id, field="winner_to_match_id"))
            return
        if target.top_source == self._node_ref_from_match_id(completed.match_id) or target.top_slot_id == completed.match_id:
            self._assign_side(target, "top", completed)
        elif target.bottom_source == self._node_ref_from_match_id(completed.match_id) or target.bottom_slot_id == completed.match_id:
            self._assign_side(target, "bottom", completed)
        if target.top_player_id and target.bottom_player_id and target.status == "blocked_waiting_for_sources":
            target.status = "pending"
            target.generated_fingerprint = self._fingerprint(target.model_dump(mode="json", exclude={"generated_fingerprint"}))

    def _assign_side(self, target: SeasonMatchRecord, side: Literal["top", "bottom"], completed: SeasonMatchRecord) -> None:
        winner_name = completed.top_player_name if completed.winner_player_id == completed.top_player_id else completed.bottom_player_name
        winner_country = completed.top_country_code if completed.winner_player_id == completed.top_player_id else completed.bottom_country_code
        setattr(target, f"{side}_player_id", completed.winner_player_id)
        setattr(target, f"{side}_player_name", winner_name)
        setattr(target, f"{side}_country_code", winner_country)

    def _simulate_match_in_package(self, *, package: SeasonEventMatchPackage, match: SeasonMatchRecord, seed: int) -> None:
        if match.status != "pending" or not match.top_player_id or not match.bottom_player_id:
            raise ValueError(f"Selected match '{match.match_id}' is not pending with two known players.")
        players_by_id = {player.player_id: player for player in self._active_players_for_season(package.season)}
        try:
            top = players_by_id[match.top_player_id]
            bottom = players_by_id[match.bottom_player_id]
        except KeyError as exc:
            raise ValueError(f"Player ID '{exc.args[0]}' was not found in active season players for season '{package.season}'.") from exc
        sim_seed = self._simulation_seed(base_seed=seed, event_id=package.event_id, match_id=match.match_id)
        context = MatchContext(
            match_id=match.match_id,
            player_a=MatchParticipantContext(player=self._to_domain_player(top)),
            player_b=MatchParticipantContext(player=self._to_domain_player(bottom)),
        )
        domain_result = MatchEngine(rng=DeterministicRng(sim_seed)).simulate(context)
        result_payload = domain_result.model_dump(mode="json")
        result_fp = self._fingerprint({"event_id": package.event_id, "match_id": match.match_id, "simulation_seed": sim_seed, "players": [match.top_player_id, match.bottom_player_id], "result": result_payload})
        simulated = MatchSimulationResult(
            match_id=match.match_id,
            winner_player_id=domain_result.winner_player_id,
            loser_player_id=domain_result.loser_player_id,
            scoreline=self._scoreline(domain_result.winner_player_id, domain_result.sets),
            games=[set_result.model_dump(mode="json") for set_result in domain_result.sets],
            points_summary={"sets_won": domain_result.sets_won, "best_of": domain_result.best_of, "games_to": domain_result.games_to, "win_by": domain_result.win_by},
            retired=domain_result.retired_player_id is not None,
            walkover=False,
            simulation_fingerprint=result_fp,
            seed=sim_seed,
        )
        match.winner_player_id = domain_result.winner_player_id
        match.loser_player_id = domain_result.loser_player_id
        match.scoreline = simulated.scoreline
        match.simulated_result = simulated
        match.result_fingerprint = result_fp
        match.simulation_seed = sim_seed
        match.status = "completed"
        match.result_notes = "ranking/race updates not implemented"

    def _refresh_completed_propagation(self, package: SeasonEventMatchPackage, *, changed: list[str]) -> None:
        for match in sorted(self._all_matches(package), key=lambda m: (m.draw_type != "qualification", m.round_number, m.bracket_position, m.match_id)):
            if match.status == "completed" and match.winner_player_id:
                before = self._target_state(package, match.winner_to_match_id)
                self._propagate_winner(package, completed=match)
                after = self._target_state(package, match.winner_to_match_id)
                if before != after and match.winner_to_match_id and match.winner_to_match_id not in changed:
                    changed.append(match.winner_to_match_id)
        for match in self._all_matches(package):
            if match.status == "blocked_waiting_for_sources" and match.top_player_id and match.bottom_player_id:
                match.status = "pending"
                if match.match_id not in changed:
                    changed.append(match.match_id)

    def _save_progression_result(
        self,
        registry: SeasonMatchesRegistry,
        package: SeasonEventMatchPackage,
        *,
        action: ProgressionAction,
        changed_match_ids: list[str],
        promoted_player_ids: list[str],
        warnings: list[MatchValidationIssue],
        errors: list[MatchValidationIssue],
        before_points: dict[str, tuple[int, int]],
    ) -> ProgressionCommandResult:
        self._refresh_package(package)
        packages = dict(registry.matches_by_event_id)
        packages[package.event_id] = package
        self._save_registry(SeasonMatchesRegistry(matches_by_event_id=packages))
        self._assert_no_ranking_updates(before_points, self._active_players_for_season(package.season))
        status = self._progression_status(package)
        return ProgressionCommandResult(
            event_id=package.event_id,
            action=action,
            match_package=package,
            progression_status=status,
            changed_match_ids=sorted(set(changed_match_ids), key=changed_match_ids.index),
            promoted_player_ids=promoted_player_ids,
            validation_warnings=warnings,
            validation_errors=errors,
            metadata={"build_fingerprint": package.metadata.build_fingerprint, "ranking_updates_implemented": package.metadata.ranking_updates_implemented},
        )

    def _progression_status(self, package: SeasonEventMatchPackage) -> TournamentProgressionStatus:
        qualification_status, winners_ready = self._draw_status(package.qualification_matches, qualification=True)
        main_status, _ = self._draw_status(package.main_draw_matches, qualification=False)
        all_matches = self._all_matches(package)
        pending = sum(1 for m in all_matches if m.status == "pending")
        blocked = sum(1 for m in all_matches if m.status == "blocked_waiting_for_sources")
        bye_pending = sum(1 for m in all_matches if m.status == "bye_auto_advance_pending")
        completed = sum(1 for m in all_matches if m.status == "completed")
        champion = self._final_match(package.main_draw_matches)
        champion_id = champion.winner_player_id if champion and champion.status == "completed" else None
        finalist_id = champion.loser_player_id if champion and champion.status == "completed" else None
        if main_status == "completed":
            event_status: EventProgressionStatusValue = "completed"
        elif pending == 0 and (blocked > 0 or bye_pending > 0):
            event_status = "blocked"
        elif completed > 0 or pending > 0:
            event_status = "in_progress"
        else:
            event_status = "not_started"
        return TournamentProgressionStatus(
            event_id=package.event_id,
            season=package.season,
            qualification_status=qualification_status,
            main_draw_status=main_status,
            event_status=event_status,
            qualification_winners_ready=winners_ready,
            qualification_winners_promoted=package.metadata.qualification_winners_promoted,
            pending_matches=pending,
            blocked_matches=blocked,
            completed_matches=completed,
            bye_auto_advances_pending=bye_pending,
            champion_player_id=champion_id,
            champion_name=self._player_name_from_match(champion, champion_id),
            finalist_player_id=finalist_id,
            finalist_name=self._player_name_from_match(champion, finalist_id),
            warnings=package.validation_warnings,
            errors=package.validation_errors,
        )

    def _draw_status(self, matches: list[SeasonMatchRecord], *, qualification: bool) -> tuple[ProgressionStatusValue, bool]:
        if not matches:
            return ("not_applicable" if qualification else "not_started", False)
        final = self._final_match(matches)
        winners_ready = bool(final and final.status == "completed" and final.winner_player_id)
        if qualification:
            max_round = max(m.round_number for m in matches)
            finals = [m for m in matches if m.round_number == max_round]
            winners_ready = bool(finals) and all(m.status == "completed" and m.winner_player_id for m in finals)
            if winners_ready and not any(m.status in {"pending", "blocked_waiting_for_sources", "bye_auto_advance_pending"} for m in matches):
                return "completed", True
        elif winners_ready:
            return "completed", winners_ready
        completed = any(m.status == "completed" for m in matches)
        actionable = any(m.status in {"pending", "blocked_waiting_for_sources", "bye_auto_advance_pending"} for m in matches)
        if not completed and actionable:
            return "not_started", winners_ready
        return "in_progress", winners_ready

    @staticmethod
    def _final_match(matches: list[SeasonMatchRecord]) -> SeasonMatchRecord | None:
        if not matches:
            return None
        max_round = max(m.round_number for m in matches)
        finals = [m for m in matches if m.round_number == max_round]
        return sorted(finals, key=lambda m: (m.bracket_position, m.match_id))[0] if finals else None

    @staticmethod
    def _player_name_from_match(match: SeasonMatchRecord | None, player_id: str | None) -> str | None:
        if match is None or player_id is None:
            return None
        if match.top_player_id == player_id:
            return match.top_player_name
        if match.bottom_player_id == player_id:
            return match.bottom_player_name
        return None

    def _target_state(self, package: SeasonEventMatchPackage, match_id: str | None) -> tuple[str | None, str | None, str | None] | None:
        if not match_id:
            return None
        target = next((m for m in self._all_matches(package) if m.match_id == match_id), None)
        if target is None:
            return None
        return (target.top_player_id, target.bottom_player_id, target.status)

    @staticmethod
    def _append_note(existing: str | None, note: str) -> str:
        if not existing:
            return note
        if note in existing:
            return existing
        return f"{existing}; {note}"

    def _refresh_package(self, package: SeasonEventMatchPackage) -> None:
        package.summary = self._summary(event_id=package.event_id, qualification_matches=package.qualification_matches, main_draw_matches=package.main_draw_matches, warnings=package.validation_warnings, errors=package.validation_errors)
        package.metadata.build_fingerprint = self._fingerprint({
            "event_id": package.event_id,
            "seed": package.seed,
            "draw_package_fingerprint": package.metadata.draw_package_fingerprint,
            "active_players_fingerprint": package.metadata.active_players_fingerprint,
            "qualification_matches": [m.model_dump(mode="json") for m in package.qualification_matches],
            "main_draw_matches": [m.model_dump(mode="json") for m in package.main_draw_matches],
        })

    def _persisted_package(self, event_id: str) -> tuple[SeasonMatchesRegistry, SeasonEventMatchPackage]:
        registry = self._load_registry()
        package = registry.matches_by_event_id.get(event_id)
        if package is None:
            raise ValueError(f"No persisted match package exists for event '{event_id}'. Generate and persist matches before simulation.")
        if not package.persisted:
            raise ValueError(f"Match package for event '{event_id}' is not persisted; simulation requires persisted state.")
        return registry, package

    @staticmethod
    def _find_match(package: SeasonEventMatchPackage, match_id: str) -> SeasonMatchRecord:
        for match in package.qualification_matches + package.main_draw_matches:
            if match.match_id == match_id:
                return match
        raise ValueError(f"Selected match '{match_id}' was not found.")

    def _active_players_for_season(self, season: str) -> list[SeasonActivePlayer]:
        response = self.active_players_service.get_active_players(season=season)
        if not response.players:
            raise ValueError(f"No active season players exist for season '{season}'. Bootstrap active players first.")
        return response.players

    @staticmethod
    def _to_domain_player(player: SeasonActivePlayer) -> Player:
        return Player(
            player_id=player.player_id,
            name=player.name,
            age=player.age_years_at_season_start,
            nationality=player.nationality,
            technique=player.attributes.technique,
            movement=player.attributes.movement,
            physical=player.attributes.physical,
            mental=player.attributes.mental,
            consistency=player.attributes.consistency,
            clutch=player.attributes.clutch,
            recovery=player.attributes.recovery,
            play_style=player.play_style,
            archetype=player.archetype,
            hidden_career_traits=player.hidden_career_traits,
        )

    @staticmethod
    def _scoreline(winner_id: str, sets: list[Any]) -> str:
        parts: list[str] = []
        for set_result in sets:
            if set_result.winner_player_id == winner_id:
                parts.append(f"{set_result.winner_games}-{set_result.loser_games}")
            else:
                parts.append(f"{set_result.loser_games}-{set_result.winner_games}")
        return ", ".join(parts)

    @staticmethod
    def _all_matches(package: SeasonEventMatchPackage) -> list[SeasonMatchRecord]:
        return package.qualification_matches + package.main_draw_matches

    @staticmethod
    def _node_ref_from_match_id(match_id: str) -> str:
        # EVT:MAIN:R1:M2 -> R1-N2, preserving draw engine source references.
        parts = match_id.split(":")
        try:
            round_part = next(part for part in parts if part.startswith("R") and part[1:].isdigit())
            match_part = next(part for part in parts if part.startswith("M") and part[1:].isdigit())
            return f"{round_part}-N{match_part[1:]}"
        except StopIteration:
            return match_id

    def _load_registry(self) -> SeasonMatchesRegistry:
        if not self.matches_path.exists():
            return SeasonMatchesRegistry()
        return SeasonMatchesRegistry.model_validate(json.loads(self.matches_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonMatchesRegistry) -> None:
        self.matches_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.matches_path.with_suffix(f"{self.matches_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.matches_path)

    @classmethod
    def _active_players_fingerprint(cls, players: list[SeasonActivePlayer]) -> str:
        return cls._fingerprint([player.model_dump(mode="json") for player in sorted(players, key=lambda p: p.player_id)])

    @staticmethod
    def _simulation_seed(*, base_seed: int, event_id: str, match_id: str) -> int:
        material = f"match-sim-v1|{base_seed}|{event_id}|{match_id}"
        return int.from_bytes(hashlib.blake2b(material.encode("utf-8"), digest_size=8).digest(), byteorder="big", signed=False)

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(severity: MatchValidationSeverity, code: str, message: str, *, event_id: str | None = None, match_id: str | None = None, player_id: str | None = None, field: str | None = None) -> MatchValidationIssue:
        return MatchValidationIssue(severity=severity, code=code, message=message, event_id=event_id, match_id=match_id, player_id=player_id, field=field)

    @staticmethod
    def _summary(*, event_id: str, qualification_matches: list[SeasonMatchRecord], main_draw_matches: list[SeasonMatchRecord], warnings: list[MatchValidationIssue], errors: list[MatchValidationIssue]) -> MatchPackageSummary:
        all_matches = qualification_matches + main_draw_matches
        return MatchPackageSummary(
            event_id=event_id,
            total_matches=len(all_matches),
            qualification_matches=len(qualification_matches),
            main_draw_matches=len(main_draw_matches),
            pending_matches=sum(1 for m in all_matches if m.status == "pending"),
            completed_matches=sum(1 for m in all_matches if m.status == "completed"),
            blocked_matches=sum(1 for m in all_matches if m.status == "blocked_waiting_for_sources"),
            bye_auto_advances=sum(1 for m in all_matches if m.status == "bye_auto_advance_pending"),
            validation_warning_count=len(warnings),
            validation_error_count=len(errors),
        )

    @staticmethod
    def _assert_no_ranking_updates(before: dict[str, tuple[int, int]], after_players: list[SeasonActivePlayer]) -> None:
        after = {p.player_id: (p.ranking_points, p.race_points) for p in after_players}
        if before != after:
            raise RuntimeError("Match simulation attempted to mutate active player ranking/race points, which is out of scope.")
