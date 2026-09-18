"""Atomic, order-independent Entry resolution for overlapping tournament clusters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
    resolved_conflict_player_count: int = Field(ge=0)
    build_fingerprint: str
    persistence_path: str | None = None


class SeasonEntryBatchResult(BaseModel):
    entry_lists_by_event_id: dict[str, SeasonEventEntryList]
    metadata: EntryBatchMetadata


PoolTarget = Literal["main", "qualification"]
PoolKey = tuple[str, PoolTarget]


@dataclass(slots=True)
class SeasonEntryBatchService:
    """Resolve one pairwise-overlapping event cluster from one player snapshot.

    Event pools rank applicants by the existing Entry service ordering. Pools propose
    in that ranking order and a player keeps the most attractive concurrent offer by
    EntryEngine ``entry_score`` (then Main over Qualification and event identity as a
    deterministic final tie-break). The resulting assignment is independent of the
    caller's event ordering and all entry lists are persisted in one registry replace.
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
        external_blocked: dict[str, set[str]] = {
            event_id: set() for event_id in ordered_event_ids
        }
        for event_id, event in events.items():
            for existing in external_lists.values():
                if existing.season != season:
                    continue
                existing_event = calendar_events.get(existing.event_id)
                if existing_event is not None:
                    overlaps = self._overlaps(event, existing_event)
                else:
                    start, end = self._interval(event)
                    overlaps = start <= existing.season_week <= end
                if not overlaps:
                    continue
                external_blocked[event_id].update(
                    entry.player_id
                    for entry in existing.entries
                    if entry.decision
                    in {"accepted_main_draw", "accepted_qualification"}
                )

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

        pool_capacity: dict[PoolKey, int] = {}
        pool_candidates: dict[PoolKey, list[EntryDecision]] = {}
        decision_lookup: dict[tuple[PoolKey, str], EntryDecision] = {}
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
                (
                    "qualification",
                    event.qualification_draw_size,
                    EntryTarget.QUALIFICATION,
                ),
            ):
                key: PoolKey = (event_id, target)
                pool_capacity[key] = capacity
                candidates = service._sort_decisions(
                    [
                        decision
                        for decision in decisions_by_event[event_id].values()
                        if decision.target == enum_target
                        and decision.player_id not in external_blocked[event_id]
                    ],
                    active_by_id,
                )
                pool_candidates[key] = candidates
                decision_lookup.update(
                    {(key, decision.player_id): decision for decision in candidates}
                )

        accepted_by_pool, held_by_player, conflicted_players = self._resolve_pools(
            pool_capacity=pool_capacity,
            pool_candidates=pool_candidates,
            decision_lookup=decision_lookup,
        )

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
                key: PoolKey = (event_id, target)
                for decision in pool_candidates[key]:
                    if decision.player_id not in accepted_by_pool[key]:
                        continue
                    entries.append(
                        service._entry_from_decision(
                            decision,
                            active_by_id[decision.player_id],
                            decision_name,
                            priority,
                            reason="accepted by shared overlapping-event resolver",
                        )
                    )
                    accepted_ids.add(decision.player_id)
                    priority += 1

            assigned_elsewhere = {
                player_id
                for player_id, pool in held_by_player.items()
                if pool[0] != event_id
            }
            remaining = service._sort_decisions(
                [
                    decision
                    for decision in decisions.values()
                    if decision.target in {EntryTarget.MAIN, EntryTarget.QUALIFICATION}
                    and decision.player_id not in accepted_ids
                    and decision.player_id not in assigned_elsewhere
                    and decision.player_id not in external_blocked[event_id]
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
                        reason="waitlist alternate after shared conflict resolution",
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
                        if decision.player_id in assigned_elsewhere:
                            reason = "accepted into another overlapping event"
                        elif decision.player_id in external_blocked[event_id]:
                            reason = "already committed to a persisted overlapping event"
                        else:
                            reason = "entered but not accepted"
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
            validation_warnings, validation_errors = service.validate_event_entry_constraints(
                event=event,
                entries=entries,
                existing_entry_lists=external_lists,
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

        self._assert_no_batch_overlap(lists)
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
                "entry_lists": [
                    lists[event_id].metadata.build_fingerprint
                    for event_id in ordered_event_ids
                ],
                "resolved_conflict_players": sorted(conflicted_players),
            }
        )
        metadata = EntryBatchMetadata(
            event_ids=ordered_event_ids,
            season=season,
            seed=request.seed,
            dry_run=request.dry_run,
            persisted=not request.dry_run,
            active_players_fingerprint=active_fp,
            resolved_conflict_player_count=len(conflicted_players),
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
            metadata=metadata,
        )

    @staticmethod
    def _resolve_pools(
        *,
        pool_capacity: dict[PoolKey, int],
        pool_candidates: dict[PoolKey, list[EntryDecision]],
        decision_lookup: dict[tuple[PoolKey, str], EntryDecision],
    ) -> tuple[dict[PoolKey, set[str]], dict[str, PoolKey], set[str]]:
        accepted: dict[PoolKey, set[str]] = {
            key: set() for key in pool_capacity
        }
        next_candidate = {key: 0 for key in pool_capacity}
        held_by_player: dict[str, PoolKey] = {}
        conflicted_players: set[str] = set()

        while True:
            proposals: dict[str, list[PoolKey]] = {}
            for key in sorted(pool_capacity):
                vacancies = pool_capacity[key] - len(accepted[key])
                while vacancies > 0 and next_candidate[key] < len(pool_candidates[key]):
                    decision = pool_candidates[key][next_candidate[key]]
                    next_candidate[key] += 1
                    proposals.setdefault(decision.player_id, []).append(key)
                    vacancies -= 1
            if not proposals:
                break

            for player_id in sorted(proposals):
                options = list(proposals[player_id])
                incumbent = held_by_player.get(player_id)
                if incumbent is not None:
                    options.append(incumbent)
                unique_options = sorted(set(options))
                if len(unique_options) > 1:
                    conflicted_players.add(player_id)
                chosen = min(
                    unique_options,
                    key=lambda key: SeasonEntryBatchService._player_preference_key(
                        decision_lookup[(key, player_id)], key
                    ),
                )
                if incumbent is not None and incumbent != chosen:
                    accepted[incumbent].remove(player_id)
                held_by_player[player_id] = chosen
                accepted[chosen].add(player_id)
        return accepted, held_by_player, conflicted_players

    @staticmethod
    def _player_preference_key(decision: EntryDecision, pool: PoolKey) -> tuple:
        return (
            -decision.entry_score,
            0 if pool[1] == "main" else 1,
            -decision.quality_score,
            pool[0],
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

    @staticmethod
    def _assert_no_batch_overlap(
        entry_lists: dict[str, SeasonEventEntryList],
    ) -> None:
        owner: dict[str, str] = {}
        for event_id in sorted(entry_lists):
            for entry in entry_lists[event_id].entries:
                if entry.decision not in {
                    "accepted_main_draw",
                    "accepted_qualification",
                }:
                    continue
                previous = owner.setdefault(entry.player_id, event_id)
                if previous != event_id:
                    raise ValueError(
                        "shared Entry resolver produced an overlapping player acceptance"
                    )
