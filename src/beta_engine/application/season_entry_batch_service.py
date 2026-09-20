"""Atomic shared-snapshot Entry generation for overlapping tournament clusters."""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import BaseModel, Field

from beta_engine.application.season_entry_list_service import (
    EntryListMetadata,
    EntryListSummary,
    EntryListValidationIssue,
    SeasonEntryListService,
    SeasonEntryListsRegistry,
    SeasonEventEntry,
    SeasonEventEntryList,
)
from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.entries import EntryDecision, EntryEngine, EntryTarget
from beta_engine.domain.tournaments import SeasonCalendarEvent
from beta_engine.infrastructure.entry_config import load_entry_tuning_config


class EntryBatchGenerateRequest(BaseModel):
    seed: int = 12345
    dry_run: bool = True
    overwrite_existing: bool = False
    max_alternates: int = Field(default=16, ge=0, le=256)
    include_not_entered: bool = False


class EntryBatchMetadata(BaseModel):
    event_ids: tuple[str, ...]
    season: str
    seed: int
    dry_run: bool
    persisted: bool
    active_players_fingerprint: str
    # Kept for wire compatibility with the short-lived #737 resolver contract.
    # Canonical entry batching no longer auto-resolves competing applications.
    resolved_conflict_player_count: int = Field(default=0, ge=0)
    unresolved_conflict_player_count: int = Field(default=0, ge=0)
    application_decisions_fingerprint: str
    build_fingerprint: str
    persistence_path: str | None = None


class SeasonEntryBatchResult(BaseModel):
    entry_lists_by_event_id: dict[str, SeasonEventEntryList]
    application_decisions: tuple[EntryDecision, ...] = ()
    metadata: EntryBatchMetadata


@dataclass(slots=True)
class SeasonEntryBatchService:
    """Generate one overlapping event cluster from one frozen player snapshot.

    Each event is evaluated independently from the same pre-slot sporting/world
    snapshot and the resulting entry lists are committed together. A player may be
    provisionally accepted into more than one overlapping event: that is historical
    Entry/Application state, not authority to compete twice. This layer therefore
    records unresolved conflicts but never invents a preferred tournament. A later
    commitment/Week Tournament Lock boundary must resolve them before play.
    """

    entry_list_service: SeasonEntryListService

    def generate_overlapping_entry_lists(
        self, *, event_ids: list[str], request: EntryBatchGenerateRequest
    ) -> SeasonEntryBatchResult:
        if len(event_ids) < 2 or len(set(event_ids)) != len(event_ids):
            raise ValueError(
                "overlapping Entry batch requires at least two unique event IDs"
            )
        ordered_event_ids = tuple(sorted(event_ids))
        service = self.entry_list_service
        registry = service._load_registry()
        if not request.dry_run and not request.overwrite_existing:
            existing = [
                event_id
                for event_id in ordered_event_ids
                if event_id in registry.entry_lists_by_event_id
            ]
            if existing:
                raise ValueError(
                    "Entry batch contains existing event lists; set "
                    f"overwrite_existing=true: {', '.join(existing)}"
                )

        events = {event_id: service._find_event(event_id) for event_id in ordered_event_ids}
        seasons = {str(event.season) for event in events.values()}
        if len(seasons) != 1:
            raise ValueError("overlapping Entry batch must belong to one season")
        season = next(iter(seasons))
        for left_index, left_id in enumerate(ordered_event_ids):
            for right_id in ordered_event_ids[left_index + 1 :]:
                if not self._overlaps(events[left_id], events[right_id]):
                    raise ValueError(
                        "Entry batch must be one pairwise-overlapping event cluster"
                    )
        for event in events.values():
            if event.ranking_status.value == "ranked" and not event.points_table_complete:
                missing = ", ".join(event.missing_required_point_stages)
                raise ValueError(
                    "Ranked Edition has an incomplete points table; "
                    f"ranking-dependent entries are blocked. Missing required stages: {missing}"
                )

        active_players = sorted(
            service.active_players_service.get_active_players(season=season).players,
            key=lambda player: player.player_id,
        )
        if not active_players:
            raise ValueError(
                f"No active season players found for season '{season}'. "
                "Bootstrap active players before generating entries."
            )
        active_fp = service._fingerprint(
            [player.model_dump(mode="json") for player in active_players]
        )
        active_by_id = {player.player_id: player for player in active_players}
        countries_by_code = {
            country.code: country for country in service.countries_service.list_countries()
        }
        players = [service._adapt_player(player) for player in active_players]
        engine = EntryEngine(
            rng=DeterministicRng(request.seed),
            tuning=load_entry_tuning_config(service.entry_tuning_path),
        )

        calendar = service.calendar_service.get_calendar(season=season).calendar
        calendar_events = {
            event.event_id: event for event in (calendar.events if calendar else [])
        }
        external_lists = {
            event_id: entry_list
            for event_id, entry_list in registry.entry_lists_by_event_id.items()
            if event_id not in ordered_event_ids
        }
        # Persisted overlapping EntryLists are not treated as irrevocable commitments.
        # They participate in unresolved-conflict evidence below; the product permits
        # overlapping provisional applications until an explicit commitment boundary.
        decisions_by_event: dict[str, dict[str, EntryDecision]] = {}
        warnings_by_event: dict[str, list[EntryListValidationIssue]] = {}
        for event_id, event in events.items():
            template = service._template_from_event_snapshot(event)
            event_rng = engine.rng.branch(
                SeedScope.WEEK,
                service._season_seed_component(event.season),
                event.week,
                event.event_id,
            )
            decisions: dict[str, EntryDecision] = {}
            warnings: list[EntryListValidationIssue] = []
            for player in players:
                country = countries_by_code.get(player.nationality)
                if country is None:
                    warnings.append(
                        service._issue(
                            "warning",
                            "country_missing",
                            f"player country '{player.nationality}' is missing from country config",
                            event_id=event_id,
                            player_id=player.player_id,
                            field="country_code",
                        )
                    )
                    continue
                decisions[player.player_id] = engine.decide_entry(
                    player=player,
                    player_country=country,
                    event=event,
                    template=template,
                    event_rng=event_rng,
                )
            decisions_by_event[event_id] = decisions
            warnings_by_event[event_id] = warnings

        application_decisions = tuple(
            sorted(
                (
                    decision
                    for event_id in ordered_event_ids
                    for decision in decisions_by_event[event_id].values()
                    if decision.target in {
                        EntryTarget.MAIN,
                        EntryTarget.QUALIFICATION,
                    }
                ),
                key=lambda decision: (
                    decision.event_id,
                    decision.player_id,
                    decision.target.value,
                ),
            )
        )
        application_decisions_fingerprint = service._fingerprint(
            [
                decision.model_dump(mode="json")
                for decision in application_decisions
            ]
        )

        pool_capacity: dict[tuple[str, str], int] = {}
        pool_candidates: dict[tuple[str, str], list[EntryDecision]] = {}
        for event_id, event in events.items():
            direct_slots = max(
                0,
                event.main_draw_size
                - event.qualifier_spots
                - event.wild_cards
                - event.byes,
            )
            for target, capacity, enum_target in (
                ("main", direct_slots, EntryTarget.MAIN),
                ("qualification", event.qualification_draw_size, EntryTarget.QUALIFICATION),
            ):
                key = (event_id, target)
                pool_capacity[key] = capacity
                pool_candidates[key] = service._sort_decisions(
                    [
                        decision
                        for decision in decisions_by_event[event_id].values()
                        if decision.target == enum_target
                    ],
                    active_by_id,
                )

        accepted_ids_by_event: dict[str, set[str]] = {}
        for event_id in ordered_event_ids:
            accepted_ids_by_event[event_id] = {
                decision.player_id
                for target in ("main", "qualification")
                for decision in pool_candidates[(event_id, target)][
                    : pool_capacity[(event_id, target)]
                ]
            }

        accepting_events_by_player: dict[str, set[str]] = {}
        for event_id, player_ids in accepted_ids_by_event.items():
            for player_id in player_ids:
                accepting_events_by_player.setdefault(player_id, set()).add(event_id)

        # Existing overlapping lists are also provisional state. Include them in
        # conflict evidence without silently treating them as a Week Tournament Lock.
        for external in external_lists.values():
            external_event = calendar_events.get(external.event_id)
            external_accepted = {
                entry.player_id
                for entry in external.entries
                if entry.decision in {"accepted_main_draw", "accepted_qualification"}
            }
            for event_id, event in events.items():
                if external.season != season:
                    continue
                if external_event is not None:
                    overlaps = self._overlaps(event, external_event)
                else:
                    start, end = self._interval(event)
                    overlaps = start <= external.season_week <= end
                if not overlaps:
                    continue
                for player_id in accepted_ids_by_event[event_id] & external_accepted:
                    accepting_events_by_player.setdefault(player_id, set()).update(
                        {event_id, external.event_id}
                    )

        conflicted_players = {
            player_id
            for player_id, accepting_events in accepting_events_by_player.items()
            if len(accepting_events) > 1
        }

        lists: dict[str, SeasonEventEntryList] = {}
        for event_id, event in events.items():
            decisions = decisions_by_event[event_id]
            entries: list[SeasonEventEntry] = []
            priority = 1
            accepted_ids: set[str] = set()
            for target, decision_name in (
                ("main", "accepted_main_draw"),
                ("qualification", "accepted_qualification"),
            ):
                key = (event_id, target)
                for decision in pool_candidates[key][: pool_capacity[key]]:
                    entries.append(
                        service._entry_from_decision(
                            decision,
                            active_by_id[decision.player_id],
                            decision_name,
                            priority,
                            reason="provisional acceptance from shared entry snapshot",
                        )
                    )
                    accepted_ids.add(decision.player_id)
                    priority += 1

            remaining = service._sort_decisions(
                [
                    decision
                    for decision in decisions.values()
                    if decision.target in {EntryTarget.MAIN, EntryTarget.QUALIFICATION}
                    and decision.player_id not in accepted_ids
                ],
                active_by_id,
            )
            alternate_ids: set[str] = set()
            for decision in remaining[: request.max_alternates]:
                entries.append(
                    service._entry_from_decision(
                        decision,
                        active_by_id[decision.player_id],
                        "alternate",
                        priority,
                        reason="provisional waitlist alternate from shared entry snapshot",
                    )
                )
                alternate_ids.add(decision.player_id)
                priority += 1

            if request.include_not_entered:
                for decision in service._sort_decisions(
                    list(decisions.values()), active_by_id
                ):
                    if (
                        decision.player_id in accepted_ids
                        or decision.player_id in alternate_ids
                    ):
                        continue
                    if decision.target in {EntryTarget.MAIN, EntryTarget.QUALIFICATION}:
                        decision_name = "rejected"
                        reason = "entered but outside the current event cut"
                    else:
                        decision_name = "not_entered"
                        reason = "entry roll did not enter tournament"
                    entries.append(
                        service._entry_from_decision(
                            decision,
                            active_by_id[decision.player_id],
                            decision_name,
                            priority,
                            reason=reason,
                        )
                    )
                    priority += 1

            warnings = list(warnings_by_event[event_id])
            event_conflicts = sorted(accepted_ids & conflicted_players)
            for player_id in event_conflicts:
                other_events = sorted(
                    accepting_events_by_player[player_id] - {event_id}
                )
                warnings.append(
                    service._issue(
                        "warning",
                        "player_week_overlap_unresolved",
                        (
                            f"player '{player_id}' is provisionally accepted into overlapping "
                            f"event(s) {', '.join(other_events)}; no preferred tournament was "
                            "invented and commitment authority is still required before play"
                        ),
                        event_id=event_id,
                        player_id=player_id,
                        field="season_week",
                    )
                )
            validation_warnings, validation_errors = service.validate_event_entry_constraints(
                event=event,
                entries=entries,
                existing_entry_lists={},
            )
            warnings.extend(validation_warnings)
            summary: EntryListSummary = service._summary(
                active_players=active_players,
                considered=len(decisions),
                entries=entries,
                warnings=warnings,
                errors=validation_errors,
            )
            event_fp = (
                event.calendar_fingerprint
                or event.template_snapshot_fingerprint
                or service._fingerprint(event.model_dump(mode="json"))
            )
            build_fp = service._fingerprint(
                {
                    "event_id": event_id,
                    "seed": request.seed,
                    "active_players_fingerprint": active_fp,
                    "calendar_event_fingerprint": event_fp,
                    "entries": [entry.model_dump(mode="json") for entry in entries],
                    "summary": summary.model_dump(mode="json"),
                    "batch_event_ids": ordered_event_ids,
                }
            )
            metadata = EntryListMetadata(
                event_id=event_id,
                season=season,
                seed=request.seed,
                dry_run=request.dry_run,
                persisted=not request.dry_run,
                build_fingerprint=build_fp,
                active_players_fingerprint=active_fp,
                calendar_event_fingerprint=event_fp,
                persistence_path=(
                    None if request.dry_run else str(service.entry_lists_path)
                ),
            )
            lists[event_id] = SeasonEventEntryList(
                event_id=event_id,
                season=season,
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

        if any(item.validation_errors for item in lists.values()):
            first = next(
                issue
                for item in lists.values()
                for issue in item.validation_errors
            )
            raise ValueError(
                f"Entry batch validation failed: {first.code}: {first.message}"
            )
        batch_fp = service._fingerprint(
            {
                "event_ids": ordered_event_ids,
                "season": season,
                "seed": request.seed,
                "active_players_fingerprint": active_fp,
                "application_decisions_fingerprint": application_decisions_fingerprint,
                "entry_lists": [
                    lists[event_id].metadata.build_fingerprint
                    for event_id in ordered_event_ids
                ],
                "unresolved_conflict_players": sorted(conflicted_players),
            }
        )
        metadata = EntryBatchMetadata(
            event_ids=ordered_event_ids,
            season=season,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            active_players_fingerprint=active_fp,
            resolved_conflict_player_count=0,
            unresolved_conflict_player_count=len(conflicted_players),
            application_decisions_fingerprint=application_decisions_fingerprint,
            build_fingerprint=batch_fp,
            persistence_path=(
                None if request.dry_run else str(service.entry_lists_path)
            ),
        )
        if not request.dry_run:
            next_lists = dict(registry.entry_lists_by_event_id)
            next_lists.update(lists)
            service._save_registry(
                SeasonEntryListsRegistry(entry_lists_by_event_id=next_lists)
            )
        return SeasonEntryBatchResult(
            entry_lists_by_event_id=lists,
            application_decisions=application_decisions,
            metadata=metadata,
        )

    @staticmethod
    def _interval(event: SeasonCalendarEvent) -> tuple[int, int]:
        start = event.start_season_week or event.season_week
        end = event.end_season_week or start
        return start, end

    @staticmethod
    def _overlaps(left: SeasonCalendarEvent, right: SeasonCalendarEvent) -> bool:
        left_start, left_end = SeasonEntryBatchService._interval(left)
        right_start, right_end = SeasonEntryBatchService._interval(right)
        return max(left_start, right_start) <= min(left_end, right_end)
