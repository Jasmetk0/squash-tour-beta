"""Application service for deterministic season event draw-package generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_entry_list_service import SeasonEntryListService, SeasonEventEntry, SeasonEventEntryList
from beta_engine.core import DeterministicRng
from beta_engine.domain.draws import DrawEngine
from beta_engine.domain.draws.models import DrawEntrantType, DrawType, GeneratedDraw
from beta_engine.domain.entries.models import AcceptanceList, AcceptanceStatus, EntryTarget, TournamentEntry
from beta_engine.domain.tournaments import LuckyLoserRules, SeasonCalendarEvent, TournamentTemplate

DrawSlotDecision = Literal["accepted_main_draw", "accepted_qualification", "qualifier_placeholder", "bye", "wild_card_reserved", "wild_card_assigned", "pre_draw_replacement"]
DrawValidationSeverity = Literal["warning", "error"]
DrawRecordType = Literal["qualification", "main"]
DrawMatchStatus = Literal["pending", "bye_pending", "completed_placeholder"]


class DrawValidationIssue(BaseModel):
    severity: DrawValidationSeverity
    code: str
    message: str
    event_id: str | None = None
    player_id: str | None = None
    field: str | None = None


class DrawMatchRecord(BaseModel):
    match_id: str
    round_number: int = Field(ge=1)
    bracket_position: int = Field(ge=1)
    top_slot_id: str
    bottom_slot_id: str
    top_source: str
    bottom_source: str
    winner_to_match_id: str | None = None
    status: DrawMatchStatus = "pending"


class DrawRound(BaseModel):
    round_number: int = Field(ge=1)
    round_name: str
    match_count: int = Field(ge=0)
    matches: list[DrawMatchRecord] = Field(default_factory=list)


class DrawSlotRecord(BaseModel):
    slot_id: str
    bracket_position: int = Field(ge=1)
    player_id: str | None = None
    player_name: str | None = None
    country_code: str | None = None
    entry_decision: DrawSlotDecision
    seed_number: int | None = Field(default=None, ge=1)
    source_entry_id: str | None = None
    source_entry_fingerprint: str | None = None
    is_bye: bool = False
    is_qualifier_placeholder: bool = False
    withdrawn_player_id: str | None = None
    replacement_source_entry_id: str | None = None
    replacement_authority_fingerprint: str | None = None


class DrawSeedRecord(BaseModel):
    seed_number: int = Field(ge=1)
    player_id: str
    player_name: str
    ranking_priority: int
    placement_position: int = Field(ge=1)


class DrawByeRecord(BaseModel):
    slot_id: str
    bracket_position: int = Field(ge=1)


class QualifierPlaceholderRecord(BaseModel):
    placeholder_id: str
    slot_id: str
    bracket_position: int = Field(ge=1)
    qualifier_index: int = Field(ge=1)


class DrawBracket(BaseModel):
    draw_id: str
    draw_type: DrawRecordType
    draw_size: int = Field(gt=0)
    round_count: int = Field(ge=0)
    rounds: list[DrawRound] = Field(default_factory=list)
    slots: list[DrawSlotRecord] = Field(default_factory=list)
    seeds: list[DrawSeedRecord] = Field(default_factory=list)
    byes: list[DrawByeRecord] = Field(default_factory=list)
    qualifier_placeholders: list[QualifierPlaceholderRecord] = Field(default_factory=list)
    generated_fingerprint: str


class DrawPackageSummary(BaseModel):
    event_id: str | None = None
    main_draw_size: int = 0
    qualification_draw_size: int = 0
    main_draw_players: int = 0
    qualification_draw_players: int = 0
    qualifier_placeholders: int = 0
    byes: int = 0
    seeds: int = 0
    validation_warning_count: int = 0
    validation_error_count: int = 0


class DrawPackageMetadata(BaseModel):
    event_id: str
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    build_fingerprint: str
    entry_list_fingerprint: str
    calendar_event_fingerprint: str
    draw_engine_version: str | None = "draw_engine_v1"
    persistence_path: str | None = None
    ranking_basis: str
    wild_card_assignments_fingerprint: str | None = None
    pre_draw_withdrawals_fingerprint: str | None = None


class SeasonEventDrawPackage(BaseModel):
    event_id: str
    season: str
    template_id: str
    season_week: int = Field(ge=1, le=61)
    calendar_year: int | None = Field(default=None, ge=1900, le=2100)
    year_week: int | None = Field(default=None, ge=1, le=61)
    seed: int
    dry_run: bool
    persisted: bool
    qualification_draw: DrawBracket | None = None
    main_draw: DrawBracket
    summary: DrawPackageSummary
    metadata: DrawPackageMetadata
    validation_warnings: list[DrawValidationIssue] = Field(default_factory=list)
    validation_errors: list[DrawValidationIssue] = Field(default_factory=list)


class SeasonEventDrawPackageResult(BaseModel):
    draw_package: SeasonEventDrawPackage | None = None
    summary: DrawPackageSummary = Field(default_factory=DrawPackageSummary)
    metadata: DrawPackageMetadata | None = None
    validation_warnings: list[DrawValidationIssue] = Field(default_factory=list)
    validation_errors: list[DrawValidationIssue] = Field(default_factory=list)
    draw_package_exists: bool = False


class DrawGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False


class SeasonDrawsRegistry(BaseModel):
    draws_by_event_id: dict[str, SeasonEventDrawPackage] = Field(default_factory=dict)


class WildCardAssignment(BaseModel):
    event_id: str
    wildcard_index: int = Field(ge=1)
    player_id: str
    player_name: str
    country_code: str
    entry_list_fingerprint: str
    active_players_fingerprint: str
    assignment_fingerprint: str


class SeasonWildCardAssignmentsRegistry(BaseModel):
    assignments_by_event_id: dict[str, list[WildCardAssignment]] = Field(default_factory=dict)


class PreDrawWithdrawalReplacement(BaseModel):
    event_id: str
    withdrawn_entry_id: str
    withdrawn_player_id: str
    withdrawn_player_name: str
    withdrawn_country_code: str
    replacement_entry_id: str
    replacement_player_id: str
    replacement_player_name: str
    replacement_country_code: str
    replacement_source: Literal["alternate_waitlist"] = "alternate_waitlist"
    entry_list_fingerprint: str
    active_players_fingerprint: str
    authority_fingerprint: str


class SeasonPreDrawWithdrawalsRegistry(BaseModel):
    replacements_by_event_id: dict[str, list[PreDrawWithdrawalReplacement]] = Field(default_factory=dict)


@dataclass(slots=True)
class SeasonDrawService:
    entry_list_service: SeasonEntryListService
    calendar_service: SeasonCalendarService
    draws_path: Path = Path("config/simulation/season_draws.json")
    wildcard_assignments_path: Path = Path("config/simulation/season_wildcard_assignments.json")
    pre_draw_withdrawals_path: Path = Path("config/simulation/season_pre_draw_withdrawals.json")

    def __post_init__(self) -> None:
        if not isinstance(self.draws_path, Path):
            self.draws_path = Path(self.draws_path)
        if not isinstance(self.wildcard_assignments_path, Path):
            self.wildcard_assignments_path = Path(self.wildcard_assignments_path)
        if not isinstance(self.pre_draw_withdrawals_path, Path):
            self.pre_draw_withdrawals_path = Path(self.pre_draw_withdrawals_path)
        default_wildcards = Path("config/simulation/season_wildcard_assignments.json")
        default_withdrawals = Path("config/simulation/season_pre_draw_withdrawals.json")
        default_draws = Path("config/simulation/season_draws.json")
        if self.wildcard_assignments_path == default_wildcards and self.draws_path != default_draws:
            self.wildcard_assignments_path = self.draws_path.with_name("season_wildcard_assignments.json")
        if self.pre_draw_withdrawals_path == default_withdrawals and self.draws_path != default_draws:
            self.pre_draw_withdrawals_path = self.draws_path.with_name("season_pre_draw_withdrawals.json")

    def get_draw_package(self, *, event_id: str) -> SeasonEventDrawPackageResult:
        registry = self._load_registry()
        package = registry.draws_by_event_id.get(event_id)
        if package is None:
            return SeasonEventDrawPackageResult(draw_package=None, draw_package_exists=False)
        return SeasonEventDrawPackageResult(
            draw_package=package,
            summary=package.summary,
            metadata=package.metadata,
            validation_warnings=package.validation_warnings,
            validation_errors=package.validation_errors,
            draw_package_exists=True,
        )

    def get_wild_card_assignments(self, *, event_id: str) -> tuple[WildCardAssignment, ...]:
        registry = self._load_wildcard_registry()
        return tuple(sorted(registry.assignments_by_event_id.get(event_id, []), key=lambda item: item.wildcard_index))

    def assign_wild_card(
        self,
        *,
        event_id: str,
        wildcard_index: int,
        player_id: str,
        overwrite_existing: bool = False,
    ) -> WildCardAssignment:
        if self.get_draw_package(event_id=event_id).draw_package_exists:
            raise ValueError("Wild-card authority is locked after the DrawPackage is persisted.")

        event = self._find_event(event_id)
        if wildcard_index < 1 or wildcard_index > event.wild_cards:
            raise ValueError(
                f"wildcard_index must be between 1 and {event.wild_cards} for event '{event_id}'."
            )

        entry_result = self.entry_list_service.get_entry_list(event_id=event_id)
        if entry_result.entry_list is None:
            raise ValueError("Persist an EntryList before assigning a wild card.")
        entry_list = entry_result.entry_list

        active_players = sorted(
            self.entry_list_service.active_players_service.get_active_players(
                season=str(event.season)
            ).players,
            key=lambda player: player.player_id,
        )
        active_fp = self._fingerprint(
            [player.model_dump(mode="json") for player in active_players]
        )
        if active_fp != entry_list.metadata.active_players_fingerprint:
            raise ValueError(
                "EntryList active-player authority is stale; regenerate entries before assigning wild cards."
            )
        player = next((item for item in active_players if item.player_id == player_id), None)
        if player is None:
            raise ValueError(
                f"Player '{player_id}' is not active in season '{event.season}'."
            )
        if any(
            item.player_id == player_id
            and item.decision in {"accepted_main_draw", "accepted_qualification"}
            for item in entry_list.entries
        ):
            raise ValueError(
                f"Player '{player_id}' is already accepted into event '{event_id}'."
            )
        if self._player_committed_to_overlapping_event(
            event=event, player_id=player_id
        ):
            raise ValueError(
                f"Player '{player_id}' is already committed to an overlapping event."
            )

        registry = self._load_wildcard_registry()
        current = list(registry.assignments_by_event_id.get(event_id, []))
        by_index = {item.wildcard_index: item for item in current}
        existing = by_index.get(wildcard_index)
        if existing is not None:
            if existing.player_id == player_id:
                return existing
            if not overwrite_existing:
                raise ValueError(
                    f"Wild-card slot {wildcard_index} already has an assignment."
                )
        duplicate = next(
            (
                item
                for item in current
                if item.player_id == player_id and item.wildcard_index != wildcard_index
            ),
            None,
        )
        if duplicate is not None:
            raise ValueError(
                f"Player '{player_id}' is already assigned to wild-card slot {duplicate.wildcard_index}."
            )

        payload = {
            "event_id": event_id,
            "wildcard_index": wildcard_index,
            "player_id": player.player_id,
            "player_name": player.name,
            "country_code": player.country_code,
            "entry_list_fingerprint": entry_list.metadata.build_fingerprint,
            "active_players_fingerprint": active_fp,
        }
        assignment = WildCardAssignment(
            **payload,
            assignment_fingerprint=self._fingerprint(payload),
        )
        by_index[wildcard_index] = assignment
        next_registry = dict(registry.assignments_by_event_id)
        next_registry[event_id] = [
            by_index[index] for index in sorted(by_index)
        ]
        self._save_wildcard_registry(
            SeasonWildCardAssignmentsRegistry(
                assignments_by_event_id=next_registry
            )
        )
        return assignment

    def get_pre_draw_withdrawal_replacements(
        self, *, event_id: str
    ) -> tuple[PreDrawWithdrawalReplacement, ...]:
        registry = self._load_pre_draw_withdrawals_registry()
        return tuple(
            sorted(
                registry.replacements_by_event_id.get(event_id, []),
                key=lambda item: (
                    item.withdrawn_entry_id,
                    item.withdrawn_player_id,
                ),
            )
        )

    def withdraw_main_draw_player(
        self,
        *,
        event_id: str,
        withdrawn_player_id: str,
    ) -> PreDrawWithdrawalReplacement:
        if self.get_draw_package(event_id=event_id).draw_package_exists:
            raise ValueError(
                "Pre-draw withdrawal authority is locked after the DrawPackage is persisted."
            )

        event = self._find_event(event_id)
        entry_result = self.entry_list_service.get_entry_list(event_id=event_id)
        if entry_result.entry_list is None:
            raise ValueError("Persist an EntryList before recording a pre-draw withdrawal.")
        entry_list = entry_result.entry_list

        active_players = sorted(
            self.entry_list_service.active_players_service.get_active_players(
                season=str(event.season)
            ).players,
            key=lambda player: player.player_id,
        )
        active_fp = self._fingerprint(
            [player.model_dump(mode="json") for player in active_players]
        )
        if active_fp != entry_list.metadata.active_players_fingerprint:
            raise ValueError(
                "EntryList active-player authority is stale; regenerate entries before recording withdrawals."
            )

        direct_by_player = {
            item.player_id: item
            for item in entry_list.entries
            if item.decision == "accepted_main_draw"
        }
        if withdrawn_player_id not in direct_by_player:
            raise ValueError(
                f"Player '{withdrawn_player_id}' is not a direct Main Draw acceptance for event '{event_id}'."
            )

        registry = self._load_pre_draw_withdrawals_registry()
        existing = list(registry.replacements_by_event_id.get(event_id, []))
        if any(
            item.entry_list_fingerprint != entry_list.metadata.build_fingerprint
            or item.active_players_fingerprint != active_fp
            for item in existing
        ):
            raise ValueError(
                "Persisted pre-draw withdrawal authority is stale; clear it before recording a new withdrawal."
            )
        withdrawn_ids = {
            item.withdrawn_player_id for item in existing
        } | {withdrawn_player_id}

        withdrawn_entries = sorted(
            (direct_by_player[player_id] for player_id in withdrawn_ids),
            key=lambda item: (item.ranking_priority, item.player_id, item.entry_id),
        )

        wildcard_players = {
            item.player_id
            for item in self.get_wild_card_assignments(event_id=event_id)
        }
        alternates = sorted(
            (
                item
                for item in entry_list.entries
                if item.decision == "alternate"
                and item.player_id not in wildcard_players
                and item.player_id not in withdrawn_ids
                and not self._player_committed_to_overlapping_event(
                    event=event, player_id=item.player_id
                )
            ),
            key=lambda item: (item.ranking_priority, item.player_id, item.entry_id),
        )
        if len(alternates) < len(withdrawn_entries):
            raise ValueError(
                "No eligible alternate remains for every recorded pre-draw withdrawal."
            )

        replacements: list[PreDrawWithdrawalReplacement] = []
        for withdrawn, replacement in zip(
            withdrawn_entries, alternates, strict=True
        ):
            payload = {
                "event_id": event_id,
                "withdrawn_entry_id": withdrawn.entry_id,
                "withdrawn_player_id": withdrawn.player_id,
                "withdrawn_player_name": withdrawn.name,
                "withdrawn_country_code": withdrawn.country_code,
                "replacement_entry_id": replacement.entry_id,
                "replacement_player_id": replacement.player_id,
                "replacement_player_name": replacement.name,
                "replacement_country_code": replacement.country_code,
                "replacement_source": "alternate_waitlist",
                "entry_list_fingerprint": entry_list.metadata.build_fingerprint,
                "active_players_fingerprint": active_fp,
            }
            replacements.append(
                PreDrawWithdrawalReplacement(
                    **payload,
                    authority_fingerprint=self._fingerprint(payload),
                )
            )

        next_registry = dict(registry.replacements_by_event_id)
        next_registry[event_id] = replacements
        self._save_pre_draw_withdrawals_registry(
            SeasonPreDrawWithdrawalsRegistry(
                replacements_by_event_id=next_registry
            )
        )
        return next(
            item
            for item in replacements
            if item.withdrawn_player_id == withdrawn_player_id
        )

    def generate_draw_package(self, *, event_id: str, request: DrawGenerateRequest) -> SeasonEventDrawPackageResult:
        registry = self._load_registry()
        exists = event_id in registry.draws_by_event_id
        if not request.dry_run and exists and not request.overwrite_existing:
            raise ValueError(f"Draw package already exists for event '{event_id}'. Set overwrite_existing=true to replace only that event.")

        event = self._find_event(event_id)
        entry_result = self.entry_list_service.get_entry_list(event_id=event_id)
        if entry_result.entry_list is None:
            raise ValueError(f"No persisted entry list exists for event '{event_id}'. Persist an entry list first.")
        entry_list = entry_result.entry_list

        warnings, errors = self.validate_draw_inputs(event=event, entry_list=entry_list)
        template = self._template_from_event_snapshot(event)
        template = self._template_with_engine_byes(event=event, template=template, warnings=warnings)
        wildcard_assignments = self._validated_wildcard_assignments(
            event=event, entry_list=entry_list
        )
        pre_draw_replacements = self._validated_pre_draw_replacements(
            event=event,
            entry_list=entry_list,
            wildcard_assignments=wildcard_assignments,
        )
        wildcard_assignments_fp = (
            self._fingerprint(
                [
                    wildcard_assignments[index].model_dump(mode="json")
                    for index in sorted(wildcard_assignments)
                ]
            )
            if wildcard_assignments
            else None
        )
        pre_draw_replacements_fp = (
            self._fingerprint(
                [
                    pre_draw_replacements[key].model_dump(mode="json")
                    for key in sorted(pre_draw_replacements)
                ]
            )
            if pre_draw_replacements
            else None
        )
        acceptance = self._acceptance_from_entry_list(
            event=event,
            entry_list=entry_list,
            wildcard_assignments=wildcard_assignments,
            pre_draw_replacements=pre_draw_replacements,
        )
        engine = DrawEngine(rng=DeterministicRng(request.seed))

        qualification_bracket: DrawBracket | None = None
        if event.qualification_draw_size > 0:
            qualification_bracket = self._bracket_from_generated_draw(
                generated=engine.generate_qualification_draw(acceptance_list=acceptance, template=template),
                entry_list=entry_list,
                event=event,
                draw_type="qualification",
                warnings=warnings,
                wildcard_assignments=wildcard_assignments,
                pre_draw_replacements=pre_draw_replacements,
            )
        else:
            warnings.append(self._issue("warning", "no_qualification_draw", "event has no qualification draw", event_id=event.event_id, field="qualification_draw_size"))

        main_bracket = self._bracket_from_generated_draw(
            generated=engine.generate_main_draw(acceptance_list=acceptance, template=template),
            entry_list=entry_list,
            event=event,
            draw_type="main",
            warnings=warnings,
            wildcard_assignments=wildcard_assignments,
            pre_draw_replacements=pre_draw_replacements,
        )
        if event.wild_cards > len(wildcard_assignments):
            warnings.append(
                self._issue(
                    "warning",
                    "wildcards_unassigned",
                    "one or more reserved wild-card slots do not have persisted assignment authority",
                    event_id=event.event_id,
                    field="wild_cards",
                )
            )
        if any(entry.decision == "alternate" for entry in entry_list.entries):
            warnings.append(self._issue("warning", "alternates_not_consumed", "alternates are not consumed by draw generation yet", event_id=event.event_id))
        if event.qualifier_spots > 0 and event.qualification_draw_size == 0:
            warnings.append(self._issue("warning", "qualifier_spots_without_qualification", "qualifier spots exist but there is no qualification draw", event_id=event.event_id, field="qualifier_spots"))
        if event.qualifier_spots > max(0, len([e for e in entry_list.entries if e.decision == "accepted_qualification"])):
            warnings.append(self._issue("warning", "qualifier_spots_exceed_possible_winners", "qualifier_spots exceeds currently accepted qualification entrants", event_id=event.event_id, field="qualifier_spots"))
        if all(entry.ranking_points == 0 for entry in entry_list.entries if entry.decision == "accepted_main_draw"):
            warnings.append(self._issue("warning", "zero_points_seeding_fallback", "ranking seeding is using zero-points bootstrap fallback", event_id=event.event_id, field="ranking_points"))
        if template.lucky_loser_rules.enabled:
            warnings.append(self._issue("warning", "lucky_loser_not_connected", "lucky loser rules are not connected to draw replacement flow yet", event_id=event.event_id))

        entry_fp = entry_list.metadata.build_fingerprint
        calendar_fp = event.calendar_fingerprint or event.template_snapshot_fingerprint or self._fingerprint(event.model_dump(mode="json"))
        build_fp = self._fingerprint(
            {
                "event_id": event.event_id,
                "seed": request.seed,
                "entry_list_fingerprint": entry_fp,
                "calendar_event_fingerprint": calendar_fp,
                "wild_card_assignments_fingerprint": wildcard_assignments_fp,
                "pre_draw_withdrawals_fingerprint": pre_draw_replacements_fp,
                "qualification_draw": qualification_bracket.model_dump(mode="json") if qualification_bracket else None,
                "main_draw": main_bracket.model_dump(mode="json"),
            }
        )
        summary = self._summary(event=event, main_draw=main_bracket, qualification_draw=qualification_bracket, warnings=warnings, errors=errors)
        metadata = DrawPackageMetadata(
            event_id=event.event_id,
            season=str(event.season),
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            build_fingerprint=build_fp,
            entry_list_fingerprint=entry_fp,
            calendar_event_fingerprint=calendar_fp,
            persistence_path=None if request.dry_run else str(self.draws_path),
            ranking_basis=entry_list.metadata.ranking_basis,
            wild_card_assignments_fingerprint=wildcard_assignments_fp,
            pre_draw_withdrawals_fingerprint=pre_draw_replacements_fp,
        )
        package = SeasonEventDrawPackage(
            event_id=event.event_id,
            season=str(event.season),
            template_id=event.template_id,
            season_week=event.season_week,
            calendar_year=event.calendar_year,
            year_week=event.year_week,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            qualification_draw=qualification_bracket,
            main_draw=main_bracket,
            summary=summary,
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=errors,
        )
        if not request.dry_run:
            if errors:
                first = errors[0]
                raise ValueError(f"Draw package validation failed: {first.code}: {first.message}")
            next_draws = dict(registry.draws_by_event_id)
            next_draws[event_id] = package
            self._save_registry(SeasonDrawsRegistry(draws_by_event_id=next_draws))
        return SeasonEventDrawPackageResult(
            draw_package=package,
            summary=summary,
            metadata=metadata,
            validation_warnings=warnings,
            validation_errors=errors,
            draw_package_exists=exists or not request.dry_run,
        )

    def validate_draw_inputs(self, *, event: SeasonCalendarEvent, entry_list: SeasonEventEntryList) -> tuple[list[DrawValidationIssue], list[DrawValidationIssue]]:
        warnings: list[DrawValidationIssue] = []
        errors: list[DrawValidationIssue] = []
        if entry_list.validation_errors:
            errors.append(self._issue("error", "entry_list_has_validation_errors", "entry list has validation errors; fix or regenerate entries before drawing", event_id=event.event_id))
        if event.main_draw_size <= 0:
            errors.append(self._issue("error", "draw_size_invalid", "main_draw_size must be greater than 0", event_id=event.event_id, field="main_draw_size"))
        if event.seeds_count > event.main_draw_size:
            errors.append(self._issue("error", "seeds_count_exceeds_main_draw", "seeds_count cannot exceed main_draw_size", event_id=event.event_id, field="seeds_count"))
        if event.qualifier_spots > event.main_draw_size:
            errors.append(self._issue("error", "qualifier_spots_exceeds_main_draw", "qualifier_spots cannot exceed main_draw_size", event_id=event.event_id, field="qualifier_spots"))
        if event.byes > event.main_draw_size:
            errors.append(self._issue("error", "byes_exceed_main_draw", "byes cannot exceed main_draw_size", event_id=event.event_id, field="byes"))
        accepted = [entry for entry in entry_list.entries if entry.decision in {"accepted_main_draw", "accepted_qualification"}]
        seen: set[str] = set()
        for entry in accepted:
            if entry.player_id in seen:
                errors.append(self._issue("error", "duplicate_player_id", f"duplicate accepted player_id '{entry.player_id}'", event_id=event.event_id, player_id=entry.player_id, field="player_id"))
            seen.add(entry.player_id)
        direct_capacity = max(0, event.main_draw_size - event.qualifier_spots - event.wild_cards - event.byes)
        main_count = sum(1 for entry in entry_list.entries if entry.decision == "accepted_main_draw")
        qual_count = sum(1 for entry in entry_list.entries if entry.decision == "accepted_qualification")
        if main_count > direct_capacity:
            errors.append(self._issue("error", "main_draw_acceptances_exceed_capacity", "accepted_main_draw count exceeds direct main draw capacity", event_id=event.event_id, field="accepted_main_draw"))
        if qual_count > event.qualification_draw_size:
            errors.append(self._issue("error", "qualification_acceptances_exceed_capacity", "accepted_qualification count exceeds qualification draw size", event_id=event.event_id, field="accepted_qualification"))
        if qual_count and event.qualifier_spots == 0:
            warnings.append(self._issue("warning", "qualification_entries_without_qualifier_spots", "qualification draw has entrants but qualifier_spots=0", event_id=event.event_id, field="qualifier_spots"))
        return warnings, errors

    def _find_event(self, event_id: str) -> SeasonCalendarEvent:
        registry = self.calendar_service._load_registry()  # application-layer persisted calendar registry reuse
        if not registry.calendars_by_season:
            raise ValueError("No persisted season calendar exists. Persist a season calendar before generating draws.")
        for calendar in registry.calendars_by_season.values():
            for event in calendar.events:
                if event.event_id == event_id:
                    return event
        raise ValueError(f"Unknown persisted season calendar event '{event_id}'.")

    def _acceptance_from_entry_list(
        self,
        *,
        event: SeasonCalendarEvent,
        entry_list: SeasonEventEntryList,
        wildcard_assignments: dict[int, WildCardAssignment],
        pre_draw_replacements: dict[str, PreDrawWithdrawalReplacement],
    ) -> AcceptanceList:
        season_year = self._season_seed_component(event.season)
        main_entries: list[TournamentEntry] = []
        qualification_entries: list[TournamentEntry] = []
        for entry in sorted(entry_list.entries, key=lambda item: (item.ranking_priority, item.player_id, item.entry_id)):
            if entry.decision == "accepted_main_draw":
                replacement = pre_draw_replacements.get(entry.entry_id)
                if replacement is None:
                    main_entries.append(
                        self._tournament_entry(
                            event=event,
                            entry=entry,
                            season_year=season_year,
                            slot=EntryTarget.MAIN,
                            status=AcceptanceStatus.DIRECT_ACCEPTANCE,
                        )
                    )
                else:
                    source_entry = next(
                        item
                        for item in entry_list.entries
                        if item.entry_id == replacement.replacement_entry_id
                    )
                    main_entries.append(
                        TournamentEntry(
                            entry_id=entry.entry_id,
                            event_id=event.event_id,
                            season=season_year,
                            week=event.season_week,
                            player_id=replacement.replacement_player_id,
                            slot=EntryTarget.MAIN,
                            status=AcceptanceStatus.DIRECT_ACCEPTANCE,
                            tour_level=event.tour_level or "WORLD_TOUR",
                            category=event.category or "UNKNOWN",
                            quality_score=source_entry.quality_score,
                            entry_score=source_entry.entry_score,
                            ranking_priority=source_entry.ranking_priority,
                            placeholder_reason=f"pre_draw_replacement:{replacement.replacement_entry_id}",
                        )
                    )
            elif entry.decision == "accepted_qualification":
                qualification_entries.append(self._tournament_entry(event=event, entry=entry, season_year=season_year, slot=EntryTarget.QUALIFICATION, status=AcceptanceStatus.QUALIFICATION_ACCEPTANCE))
        for index in range(1, event.qualifier_spots + 1):
            main_entries.append(self._placeholder_entry(event=event, season_year=season_year, index=index, status=AcceptanceStatus.QUALIFIER_PLACEHOLDER, reason=f"Q{index}"))
        for index in range(1, event.wild_cards + 1):
            assignment = wildcard_assignments.get(index)
            main_entries.append(
                self._placeholder_entry(
                    event=event,
                    season_year=season_year,
                    index=index,
                    status=AcceptanceStatus.WILD_CARD_PLACEHOLDER,
                    reason=f"WC{index}",
                    player_id=assignment.player_id if assignment is not None else None,
                )
            )
        return AcceptanceList(
            event_id=event.event_id,
            template_id=event.template_id,
            season=season_year,
            week=event.season_week,
            main_draw_size=event.main_draw_size,
            qualification_draw_size=event.qualification_draw_size,
            qualifier_spots=event.qualifier_spots,
            wild_card_slots=event.wild_cards,
            main_draw_applicants=[],
            qualification_applicants=[],
            main_draw_entries=main_entries,
            qualification_entries=qualification_entries,
        )

    @staticmethod
    def _tournament_entry(*, event: SeasonCalendarEvent, entry: SeasonEventEntry, season_year: int, slot: EntryTarget, status: AcceptanceStatus) -> TournamentEntry:
        return TournamentEntry(
            entry_id=entry.entry_id,
            event_id=event.event_id,
            season=season_year,
            week=event.season_week,
            player_id=entry.player_id,
            slot=slot,
            status=status,
            tour_level=event.tour_level or "WORLD_TOUR",
            category=event.category or "UNKNOWN",
            quality_score=entry.quality_score,
            entry_score=entry.entry_score,
            ranking_priority=entry.ranking_priority,
        )

    @staticmethod
    def _placeholder_entry(*, event: SeasonCalendarEvent, season_year: int, index: int, status: AcceptanceStatus, reason: str, player_id: str | None = None) -> TournamentEntry:
        return TournamentEntry(
            entry_id=f"{event.event_id}:{status.value}:{index}",
            event_id=event.event_id,
            season=season_year,
            week=event.season_week,
            player_id=player_id,
            slot=EntryTarget.MAIN,
            status=status,
            tour_level=event.tour_level or "WORLD_TOUR",
            category=event.category or "UNKNOWN",
            ranking_priority=10_000 + index,
            placeholder_reason=reason,
        )

    def _bracket_from_generated_draw(
        self,
        *,
        generated: GeneratedDraw,
        entry_list: SeasonEventEntryList,
        event: SeasonCalendarEvent,
        draw_type: DrawRecordType,
        warnings: list[DrawValidationIssue],
        wildcard_assignments: dict[int, WildCardAssignment],
        pre_draw_replacements: dict[str, PreDrawWithdrawalReplacement],
    ) -> DrawBracket:
        entries_by_id = {entry.entry_id: entry for entry in entry_list.entries}
        wildcard_by_entry_id = {
            f"{event.event_id}:{AcceptanceStatus.WILD_CARD_PLACEHOLDER.value}:{index}": assignment
            for index, assignment in wildcard_assignments.items()
        }
        slots: list[DrawSlotRecord] = []
        seeds: list[DrawSeedRecord] = []
        byes: list[DrawByeRecord] = []
        qualifier_placeholders: list[QualifierPlaceholderRecord] = []
        qualifier_index = 1
        for slot in generated.slots:
            entry = entries_by_id.get(slot.entry_id or "")
            wildcard_assignment = wildcard_by_entry_id.get(slot.entry_id or "")
            replacement = pre_draw_replacements.get(slot.entry_id or "")
            replacement_entry = (
                entries_by_id.get(replacement.replacement_entry_id)
                if replacement is not None
                else None
            )
            is_tbd = slot.entrant_type == DrawEntrantType.TBD
            is_bye = slot.entrant_type == DrawEntrantType.BYE or is_tbd
            if is_tbd:
                warnings.append(self._issue("warning", "fewer_entrants_than_draw_size", "fewer entrants than draw size; BYE placeholders inserted", event_id=event.event_id, field=draw_type))
            decision: DrawSlotDecision
            if is_bye:
                decision = "bye"
            elif slot.entrant_type == DrawEntrantType.QUALIFIER_PLACEHOLDER:
                decision = "qualifier_placeholder"
            elif replacement is not None:
                decision = "pre_draw_replacement"
            elif (
                wildcard_assignment is not None
                or slot.entrant_type == DrawEntrantType.WILD_CARD_PLACEHOLDER
            ):
                decision = (
                    "wild_card_assigned"
                    if wildcard_assignment is not None and slot.player_id is not None
                    else "wild_card_reserved"
                )
            elif draw_type == "qualification":
                decision = "accepted_qualification"
            else:
                decision = "accepted_main_draw"
            record = DrawSlotRecord(
                slot_id=f"{generated.event_id}:{draw_type}:S{slot.slot_index}",
                bracket_position=slot.slot_index,
                player_id=slot.player_id,
                player_name=(
                    replacement.replacement_player_name
                    if replacement is not None
                    else entry.name
                    if entry is not None
                    else wildcard_assignment.player_name
                    if wildcard_assignment is not None
                    else None
                ),
                country_code=(
                    replacement.replacement_country_code
                    if replacement is not None
                    else entry.country_code
                    if entry is not None
                    else wildcard_assignment.country_code
                    if wildcard_assignment is not None
                    else None
                ),
                entry_decision=decision,
                seed_number=slot.seed_number,
                source_entry_id=slot.entry_id,
                source_entry_fingerprint=(
                    replacement.authority_fingerprint
                    if replacement is not None
                    else entry.generated_fingerprint
                    if entry is not None
                    else wildcard_assignment.assignment_fingerprint
                    if wildcard_assignment is not None
                    else self._fingerprint({"entry_id": slot.entry_id})
                    if slot.entry_id
                    else None
                ),
                is_bye=is_bye,
                is_qualifier_placeholder=slot.entrant_type == DrawEntrantType.QUALIFIER_PLACEHOLDER,
                withdrawn_player_id=(
                    replacement.withdrawn_player_id
                    if replacement is not None
                    else None
                ),
                replacement_source_entry_id=(
                    replacement.replacement_entry_id
                    if replacement is not None
                    else None
                ),
                replacement_authority_fingerprint=(
                    replacement.authority_fingerprint
                    if replacement is not None
                    else None
                ),
            )
            slots.append(record)
            if record.is_bye:
                byes.append(DrawByeRecord(slot_id=record.slot_id, bracket_position=record.bracket_position))
            if record.is_qualifier_placeholder:
                qualifier_placeholders.append(QualifierPlaceholderRecord(placeholder_id=f"Q{qualifier_index}", slot_id=record.slot_id, bracket_position=record.bracket_position, qualifier_index=qualifier_index))
                qualifier_index += 1
            seed_entry = replacement_entry if replacement_entry is not None else entry
            if slot.seed_number is not None and seed_entry is not None and slot.player_id is not None:
                seeds.append(
                    DrawSeedRecord(
                        seed_number=slot.seed_number,
                        player_id=slot.player_id,
                        player_name=seed_entry.name,
                        ranking_priority=seed_entry.ranking_priority,
                        placement_position=slot.slot_index,
                    )
                )
        rounds = self._rounds_from_nodes(generated=generated, slots_by_index={slot.bracket_position: slot for slot in slots})
        fingerprint = self._fingerprint(
            {
                "event_id": generated.event_id,
                "draw_type": draw_type,
                "draw_size": generated.bracket_size,
                "slots": [slot.model_dump(mode="json") for slot in slots],
                "seeds": [seed.model_dump(mode="json") for seed in seeds],
                "rounds": [round_.model_dump(mode="json") for round_ in rounds],
            }
        )
        return DrawBracket(
            draw_id=f"{generated.event_id}:{draw_type}",
            draw_type=draw_type,
            draw_size=generated.bracket_size,
            round_count=len(rounds),
            rounds=rounds,
            slots=slots,
            seeds=seeds,
            byes=byes,
            qualifier_placeholders=qualifier_placeholders,
            generated_fingerprint=fingerprint,
        )

    @staticmethod
    def _rounds_from_nodes(*, generated: GeneratedDraw, slots_by_index: dict[int, DrawSlotRecord]) -> list[DrawRound]:
        winner_to_by_node: dict[str, str] = {}
        for node in generated.nodes:
            for source in (node.source_top, node.source_bottom):
                if source.startswith("R"):
                    winner_to_by_node[source] = node.node_id
        matches_by_round: dict[int, list[DrawMatchRecord]] = {}
        for node in generated.nodes:
            top_slot = _slot_id_from_source(source=node.source_top, generated=generated, slots_by_index=slots_by_index)
            bottom_slot = _slot_id_from_source(source=node.source_bottom, generated=generated, slots_by_index=slots_by_index)
            status: DrawMatchStatus = "pending"
            if node.source_top.startswith("SLOT:") and node.source_bottom.startswith("SLOT:"):
                top = slots_by_index[int(node.source_top.split(":", maxsplit=1)[1])]
                bottom = slots_by_index[int(node.source_bottom.split(":", maxsplit=1)[1])]
                if top.is_bye or bottom.is_bye:
                    status = "bye_pending"
            matches_by_round.setdefault(node.round_number, []).append(
                DrawMatchRecord(
                    match_id=f"{generated.event_id}:{generated.draw_type.value}:R{node.round_number}:M{node.round_sequence}",
                    round_number=node.round_number,
                    bracket_position=node.round_sequence,
                    top_slot_id=top_slot,
                    bottom_slot_id=bottom_slot,
                    top_source=node.source_top,
                    bottom_source=node.source_bottom,
                    winner_to_match_id=winner_to_by_node.get(node.node_id),
                    status=status,
                )
            )
        return [DrawRound(round_number=round_number, round_name=f"Round {round_number}", match_count=len(matches), matches=matches) for round_number, matches in sorted(matches_by_round.items())]


    @staticmethod
    def _template_with_engine_byes(*, event: SeasonCalendarEvent, template: TournamentTemplate, warnings: list[DrawValidationIssue]) -> TournamentTemplate:
        bracket_size = event.main_draw_size + event.byes
        if bracket_size > 0 and (bracket_size & (bracket_size - 1)) == 0:
            return template
        power_size = 1
        while power_size < max(1, event.main_draw_size):
            power_size *= 2
        required_byes = max(0, power_size - event.main_draw_size)
        warnings.append(
            DrawValidationIssue(
                severity="warning",
                code="power_of_two_byes_inserted",
                message="main_draw_size + byes is not a power-of-two bracket; deterministic BYE placeholders inserted for DrawEngine compatibility",
                event_id=event.event_id,
                field="byes",
            )
        )
        return template.model_copy(update={"byes": required_byes})

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
            "point_distribution_ref": event.point_distribution_ref or snapshot.get("point_distribution_ref") or "event_snapshot",
            "point_distribution": event.point_distribution or snapshot.get("point_distribution"),
            "event_duration_days": snapshot.get("event_duration_days") or 1,
            "qualification_duration_days": snapshot.get("qualification_duration_days") or 0,
            "prize_money": event.prize_money,
            "prestige": event.prestige,
            "duration_in_season_weeks": event.duration_in_season_weeks,
            "active": snapshot.get("active", True),
        }
        return TournamentTemplate.model_validate(payload)

    def _validated_wildcard_assignments(
        self,
        *,
        event: SeasonCalendarEvent,
        entry_list: SeasonEventEntryList,
    ) -> dict[int, WildCardAssignment]:
        assignments = {
            item.wildcard_index: item
            for item in self.get_wild_card_assignments(event_id=event.event_id)
        }
        if any(index > event.wild_cards for index in assignments):
            raise ValueError("Persisted wild-card assignment exceeds current event capacity.")
        active_players = sorted(
            self.entry_list_service.active_players_service.get_active_players(
                season=str(event.season)
            ).players,
            key=lambda player: player.player_id,
        )
        active_fp = self._fingerprint(
            [player.model_dump(mode="json") for player in active_players]
        )
        seen_players: set[str] = set()
        for index, assignment in sorted(assignments.items()):
            if assignment.entry_list_fingerprint != entry_list.metadata.build_fingerprint:
                raise ValueError(
                    "Persisted wild-card assignment is stale for the current EntryList."
                )
            if assignment.active_players_fingerprint != active_fp:
                raise ValueError(
                    "Persisted wild-card assignment is stale for the active-player snapshot."
                )
            if assignment.player_id in seen_players:
                raise ValueError("Duplicate player across persisted wild-card assignments.")
            seen_players.add(assignment.player_id)
            if not any(player.player_id == assignment.player_id for player in active_players):
                raise ValueError(
                    f"Wild-card player '{assignment.player_id}' is no longer active."
                )
            if any(
                item.player_id == assignment.player_id
                and item.decision in {"accepted_main_draw", "accepted_qualification"}
                for item in entry_list.entries
            ):
                raise ValueError(
                    f"Wild-card player '{assignment.player_id}' is already accepted into the event."
                )
            if self._player_committed_to_overlapping_event(
                event=event, player_id=assignment.player_id
            ):
                raise ValueError(
                    f"Wild-card player '{assignment.player_id}' is committed to an overlapping event."
                )
        return assignments

    def _player_committed_to_overlapping_event(
        self, *, event: SeasonCalendarEvent, player_id: str
    ) -> bool:
        registry = self.entry_list_service._load_registry()
        event_start = event.start_season_week or event.season_week
        event_end = event.end_season_week or event_start
        for other in registry.entry_lists_by_event_id.values():
            if other.event_id == event.event_id or other.season != str(event.season):
                continue
            try:
                other_event = self._find_event(other.event_id)
            except ValueError:
                continue
            other_start = other_event.start_season_week or other_event.season_week
            other_end = other_event.end_season_week or other_start
            if max(event_start, other_start) > min(event_end, other_end):
                continue
            if any(
                item.player_id == player_id
                and item.decision in {"accepted_main_draw", "accepted_qualification"}
                for item in other.entries
            ):
                return True
        return False

    def _validated_pre_draw_replacements(
        self,
        *,
        event: SeasonCalendarEvent,
        entry_list: SeasonEventEntryList,
        wildcard_assignments: dict[int, WildCardAssignment],
    ) -> dict[str, PreDrawWithdrawalReplacement]:
        replacements = self.get_pre_draw_withdrawal_replacements(
            event_id=event.event_id
        )
        active_players = sorted(
            self.entry_list_service.active_players_service.get_active_players(
                season=str(event.season)
            ).players,
            key=lambda player: player.player_id,
        )
        active_fp = self._fingerprint(
            [player.model_dump(mode="json") for player in active_players]
        )
        entries_by_id = {item.entry_id: item for item in entry_list.entries}
        wildcard_players = {item.player_id for item in wildcard_assignments.values()}
        seen_withdrawn: set[str] = set()
        seen_replacements: set[str] = set()
        by_entry: dict[str, PreDrawWithdrawalReplacement] = {}

        for replacement in replacements:
            if replacement.entry_list_fingerprint != entry_list.metadata.build_fingerprint:
                raise ValueError(
                    "Persisted pre-draw withdrawal authority is stale for the current EntryList."
                )
            if replacement.active_players_fingerprint != active_fp:
                raise ValueError(
                    "Persisted pre-draw withdrawal authority is stale for the active-player snapshot."
                )
            withdrawn = entries_by_id.get(replacement.withdrawn_entry_id)
            source = entries_by_id.get(replacement.replacement_entry_id)
            if (
                withdrawn is None
                or withdrawn.decision != "accepted_main_draw"
                or withdrawn.player_id != replacement.withdrawn_player_id
            ):
                raise ValueError(
                    "Persisted pre-draw withdrawn entry no longer matches direct Main Draw authority."
                )
            if (
                source is None
                or source.decision != "alternate"
                or source.player_id != replacement.replacement_player_id
            ):
                raise ValueError(
                    "Persisted pre-draw replacement no longer matches alternate waitlist authority."
                )
            if replacement.withdrawn_player_id in seen_withdrawn:
                raise ValueError("Duplicate withdrawn player in pre-draw authority.")
            if replacement.replacement_player_id in seen_replacements:
                raise ValueError("Duplicate replacement player in pre-draw authority.")
            if replacement.replacement_player_id in wildcard_players:
                raise ValueError(
                    "Pre-draw replacement player is also assigned as a Wild Card."
                )
            if self._player_committed_to_overlapping_event(
                event=event, player_id=replacement.replacement_player_id
            ):
                raise ValueError(
                    "Pre-draw replacement player is committed to an overlapping event."
                )
            payload = replacement.model_dump(
                mode="json", exclude={"authority_fingerprint"}
            )
            if self._fingerprint(payload) != replacement.authority_fingerprint:
                raise ValueError("Persisted pre-draw withdrawal authority is corrupt.")
            seen_withdrawn.add(replacement.withdrawn_player_id)
            seen_replacements.add(replacement.replacement_player_id)
            by_entry[replacement.withdrawn_entry_id] = replacement
        return by_entry

    def _load_pre_draw_withdrawals_registry(
        self,
    ) -> SeasonPreDrawWithdrawalsRegistry:
        if not self.pre_draw_withdrawals_path.exists():
            return SeasonPreDrawWithdrawalsRegistry()
        return SeasonPreDrawWithdrawalsRegistry.model_validate(
            json.loads(self.pre_draw_withdrawals_path.read_text(encoding="utf-8"))
        )

    def _save_pre_draw_withdrawals_registry(
        self, registry: SeasonPreDrawWithdrawalsRegistry
    ) -> None:
        self.pre_draw_withdrawals_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.pre_draw_withdrawals_path.with_suffix(
            f"{self.pre_draw_withdrawals_path.suffix}.tmp"
        )
        tmp_path.write_text(
            json.dumps(registry.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.pre_draw_withdrawals_path)

    def _load_wildcard_registry(self) -> SeasonWildCardAssignmentsRegistry:
        if not self.wildcard_assignments_path.exists():
            return SeasonWildCardAssignmentsRegistry()
        return SeasonWildCardAssignmentsRegistry.model_validate(
            json.loads(self.wildcard_assignments_path.read_text(encoding="utf-8"))
        )

    def _save_wildcard_registry(
        self, registry: SeasonWildCardAssignmentsRegistry
    ) -> None:
        self.wildcard_assignments_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.wildcard_assignments_path.with_suffix(
            f"{self.wildcard_assignments_path.suffix}.tmp"
        )
        tmp_path.write_text(
            json.dumps(registry.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.wildcard_assignments_path)

    @staticmethod
    def _summary(*, event: SeasonCalendarEvent, main_draw: DrawBracket, qualification_draw: DrawBracket | None, warnings: list[DrawValidationIssue], errors: list[DrawValidationIssue]) -> DrawPackageSummary:
        return DrawPackageSummary(
            event_id=event.event_id,
            main_draw_size=main_draw.draw_size,
            qualification_draw_size=qualification_draw.draw_size if qualification_draw is not None else 0,
            main_draw_players=sum(1 for slot in main_draw.slots if slot.player_id is not None),
            qualification_draw_players=sum(1 for slot in (qualification_draw.slots if qualification_draw is not None else []) if slot.player_id is not None),
            qualifier_placeholders=len(main_draw.qualifier_placeholders),
            byes=len(main_draw.byes) + (len(qualification_draw.byes) if qualification_draw is not None else 0),
            seeds=len(main_draw.seeds),
            validation_warning_count=len(warnings),
            validation_error_count=len(errors),
        )

    def _load_registry(self) -> SeasonDrawsRegistry:
        if not self.draws_path.exists():
            return SeasonDrawsRegistry()
        return SeasonDrawsRegistry.model_validate(json.loads(self.draws_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: SeasonDrawsRegistry) -> None:
        self.draws_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.draws_path.with_suffix(f"{self.draws_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.draws_path)

    @staticmethod
    def _season_seed_component(season: str | int) -> int:
        if isinstance(season, int):
            return season
        try:
            return int(str(season).split("/", maxsplit=1)[0])
        except (TypeError, ValueError):
            return 1900

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(severity: DrawValidationSeverity, code: str, message: str, *, event_id: str | None = None, player_id: str | None = None, field: str | None = None) -> DrawValidationIssue:
        return DrawValidationIssue(severity=severity, code=code, message=message, event_id=event_id, player_id=player_id, field=field)


def _slot_id_from_source(*, source: str, generated: GeneratedDraw, slots_by_index: dict[int, DrawSlotRecord]) -> str:
    if source.startswith("SLOT:"):
        index = int(source.split(":", maxsplit=1)[1])
        return slots_by_index[index].slot_id
    return f"{generated.event_id}:{generated.draw_type.value}:{source}"
