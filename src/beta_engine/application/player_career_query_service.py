"""Read-side query service for longitudinal player career exploration."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Literal

from beta_engine.domain.players import Player
from beta_engine.infrastructure.db import SimulationPersistenceRepository, SimulationRunInfo
from beta_engine.infrastructure.db.repositories import PersistedGeneratedPlayerProvenanceRecord


@dataclass(frozen=True)
class PlayerCareerHistoryEntry:
    run_id: str
    season: int
    age: int
    overall: int
    technique: int
    movement: int
    physical: int
    mental: int
    source_type: Literal["rollover_carried", "planner_generated", "manual_override"] | None
    quality_band: str | None
    is_top_band: bool | None
    origin_source_type: Literal["planner_generated", "manual_override"] | None
    origin_quality_band: str | None
    origin_override_id: str | None
    origin_season: int | None


@dataclass(frozen=True)
class PlayerCareerHistory:
    requested_run_id: str
    player_id: str
    player_name: str | None
    country_code: str | None
    entries: list[PlayerCareerHistoryEntry]


class PlayerCareerQueryService:
    """Builds chronological player snapshots across a connected run lineage tree."""

    def __init__(
        self,
        *,
        repository: SimulationPersistenceRepository,
        load_players_for_run: Callable[[SimulationRunInfo], dict[str, Player]],
    ) -> None:
        self._repository = repository
        self._load_players_for_run = load_players_for_run

    def get_player_career_history(self, *, run_id: str, player_id: str) -> PlayerCareerHistory:
        requested_run = self._repository.get_simulation_run(run_id=run_id)
        if requested_run is None:
            raise KeyError(f"run_id {run_id} was not found")

        requested_players = self._load_players_for_run(requested_run)
        requested_player = requested_players.get(player_id)
        if requested_player is None:
            raise KeyError(f"player_id {player_id} was not found in run_id {run_id}")

        connected_runs = self._resolve_connected_lineage_runs(run_id=run_id)
        entries: list[PlayerCareerHistoryEntry] = []

        for run_info in connected_runs:
            players_by_id = self._load_players_for_run(run_info)
            player = players_by_id.get(player_id)
            if player is None:
                continue
            provenance = self._repository.get_generated_player_provenance(run_id=run_info.run_id, player_id=player_id)
            entries.append(self._to_entry(run_info=run_info, player=player, provenance=provenance))

        ordered_entries = sorted(entries, key=lambda entry: (entry.season, entry.run_id))
        return PlayerCareerHistory(
            requested_run_id=run_id,
            player_id=player_id,
            player_name=requested_player.name,
            country_code=requested_player.nationality,
            entries=ordered_entries,
        )

    def _resolve_connected_lineage_runs(self, *, run_id: str) -> list[SimulationRunInfo]:
        all_runs = self._repository.list_simulation_runs()
        runs_by_id = {run.run_id: run for run in all_runs}

        requested = runs_by_id.get(run_id)
        if requested is None:
            return []

        root = requested
        while root.parent_run_id is not None and root.parent_run_id in runs_by_id:
            root = runs_by_id[root.parent_run_id]

        children_by_parent: dict[str, list[SimulationRunInfo]] = defaultdict(list)
        for run in all_runs:
            if run.parent_run_id is not None:
                children_by_parent[run.parent_run_id].append(run)

        ordered: list[SimulationRunInfo] = []
        stack = [root]
        visited: set[str] = set()
        while stack:
            current = stack.pop()
            if current.run_id in visited:
                continue
            visited.add(current.run_id)
            ordered.append(current)
            for child in sorted(children_by_parent.get(current.run_id, []), key=lambda item: item.run_id, reverse=True):
                stack.append(child)

        return ordered

    @staticmethod
    def _to_entry(
        *,
        run_info: SimulationRunInfo,
        player: Player,
        provenance: PersistedGeneratedPlayerProvenanceRecord | None,
    ) -> PlayerCareerHistoryEntry:
        return PlayerCareerHistoryEntry(
            run_id=run_info.run_id,
            season=run_info.season,
            age=player.age,
            overall=round((player.technique + player.movement + player.physical + player.mental) / 4),
            technique=player.technique,
            movement=player.movement,
            physical=player.physical,
            mental=player.mental,
            source_type=provenance.source_type if provenance is not None else None,
            quality_band=provenance.quality_band if provenance is not None else None,
            is_top_band=provenance.is_top_band if provenance is not None else None,
            origin_source_type=provenance.origin_source_type if provenance is not None else None,
            origin_quality_band=provenance.origin_quality_band if provenance is not None else None,
            origin_override_id=provenance.origin_override_id if provenance is not None else None,
            origin_season=provenance.origin_season if provenance is not None else None,
        )
