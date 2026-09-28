"""Persistence and dependency validation for canonical World Tour Finals Race."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.domain.finals.race import (
    WorldTourFinalsRaceEventAwards,
    WorldTourFinalsRacePlayerAward,
    WorldTourFinalsRaceSnapshot,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import load_official_ranking_snapshot
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    WorldTourFinalsRaceSnapshotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


class WorldTourFinalsRaceConflict(ValueError):
    """A season already owns a different immutable Finals Race snapshot."""


def _season_label(season_index: int) -> str:
    start = 2000 + season_index
    return f"{start}/{start + 1}"


class WorldTourFinalsRaceSnapshotStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("World Tour Finals Race Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("World Tour Finals Race scope is not writable")

    def _dependencies(
        self, snapshot: WorldTourFinalsRaceSnapshot
    ) -> tuple[WorldTourFinalsRaceEventAwards, ...]:
        publication = self.session.get(
            PublishedOfficialRankingModel,
            (snapshot.run_id, snapshot.branch_id, snapshot.cutoff_week.ordinal),
        )
        if publication is None:
            raise ValueError(
                "World Tour Finals Race cutoff requires a published Official Ranking"
            )
        cutoff = load_official_ranking_snapshot(
            publication.payload_json,
            expected_fingerprint=publication.snapshot_fingerprint,
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            week=snapshot.cutoff_week,
        )
        if cutoff.fingerprint != snapshot.cutoff_ranking_fingerprint:
            raise ValueError("World Tour Finals Race cutoff publication fingerprint mismatch")

        package_state = get_run_package_state(
            self.session, run_id=snapshot.run_id, branch_id=snapshot.branch_id
        )
        if package_state is None:
            raise ValueError("World Tour Finals Race requires Run Package state")
        season = _season_label(snapshot.season_index)
        projection = CalendarPackageRunAdapter.project_calendar(
            package_state,
            package_id=CalendarPackageRunAdapter.package_id_for_season(season),
        )
        if projection.content_fingerprint != snapshot.calendar_projection_fingerprint:
            raise ValueError("World Tour Finals Race Calendar projection fingerprint mismatch")
        calendar_ids = {event.event_id for event in projection.calendar.events}
        if not set(snapshot.eligible_event_ids) <= calendar_ids:
            raise ValueError("World Tour Finals Race eligible event is absent from Run-owned Calendar")

        sources = OwnedTournamentRankingSourceStore(self.session).history(
            run_id=snapshot.run_id, branch_id=snapshot.branch_id
        )
        by_event = {}
        for source in sources:
            if source is None:
                raise ValueError("World Tour Finals Race tournament source identity is missing")
            event_id = source.binding.event_id
            if event_id in by_event:
                raise ValueError("World Tour Finals Race has ambiguous tournament source identity")
            by_event[event_id] = source

        resolved = []
        for event_id, source_fingerprint in snapshot.source_tournament_fingerprints:
            source = by_event.get(event_id)
            if source is None or source.fingerprint != source_fingerprint:
                raise ValueError("World Tour Finals Race tournament source fingerprint mismatch")
            binding = source.binding
            awards = source.canonical_awards
            if awards is None:
                raise ValueError("World Tour Finals Race requires canonical point awards")
            if (
                binding.completed_week.season_index != snapshot.season_index
                or binding.first_publication_week is None
                or binding.first_publication_week.ordinal > snapshot.cutoff_week.ordinal
                or awards.completed_week != binding.completed_week
                or awards.event_id != event_id
            ):
                raise ValueError("World Tour Finals Race tournament source boundary mismatch")
            resolved.append(
                WorldTourFinalsRaceEventAwards(
                    event_id=event_id,
                    completed_week=binding.completed_week,
                    first_publication_week=binding.first_publication_week,
                    source_fingerprint=source.fingerprint,
                    awards=tuple(
                        WorldTourFinalsRacePlayerAward(
                            player_id=award.player_id,
                            race_points=award.race_points_awarded,
                            award_fingerprint=award.award_fingerprint,
                        )
                        for award in awards.awards
                    ),
                )
            )
        return tuple(resolved)

    def _load_row(
        self, row: WorldTourFinalsRaceSnapshotModel
    ) -> WorldTourFinalsRaceSnapshot:
        snapshot = WorldTourFinalsRaceSnapshot.model_validate_json(row.payload_json)
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.season_index,
            snapshot.cutoff_week.ordinal,
            snapshot.fingerprint,
            snapshot.command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.season_index,
            row.cutoff_week_ordinal,
            row.snapshot_fingerprint,
            row.command_id,
        ):
            raise ValueError("Stored World Tour Finals Race snapshot is corrupt")
        event_sources = self._dependencies(snapshot)
        rebuilt = calculate_world_tour_finals_race(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=snapshot.season_index,
            cutoff_week=snapshot.cutoff_week,
            cutoff_ranking_fingerprint=snapshot.cutoff_ranking_fingerprint,
            best_result_count=snapshot.best_result_count,
            eligible_event_ids=snapshot.eligible_event_ids,
            calendar_projection_fingerprint=snapshot.calendar_projection_fingerprint,
            event_sources=event_sources,
            command_id=snapshot.command_id,
        )
        if rebuilt != snapshot:
            raise ValueError("Stored World Tour Finals Race snapshot differs from canonical sources")
        return snapshot

    def get(
        self, *, run_id: str, branch_id: str, season_index: int
    ) -> WorldTourFinalsRaceSnapshot | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            WorldTourFinalsRaceSnapshotModel, (run_id, branch_id, season_index)
        )
        return None if row is None else self._load_row(row)

    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[WorldTourFinalsRaceSnapshot, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(WorldTourFinalsRaceSnapshotModel)
            .where(
                WorldTourFinalsRaceSnapshotModel.run_id == run_id,
                WorldTourFinalsRaceSnapshotModel.branch_id == branch_id,
            )
            .order_by(WorldTourFinalsRaceSnapshotModel.season_index)
        ).all()
        return tuple(self._load_row(row) for row in rows)

    def append(
        self, snapshot: WorldTourFinalsRaceSnapshot
    ) -> WorldTourFinalsRaceSnapshot:
        snapshot = WorldTourFinalsRaceSnapshot.model_validate_json(
            snapshot.model_dump_json()
        )
        self._scope(snapshot.run_id, snapshot.branch_id, writing=True)
        self._dependencies(snapshot)
        existing = self.session.get(
            WorldTourFinalsRaceSnapshotModel,
            (snapshot.run_id, snapshot.branch_id, snapshot.season_index),
        )
        if existing is not None:
            current = self._load_row(existing)
            if current.fingerprint != snapshot.fingerprint:
                raise WorldTourFinalsRaceConflict(
                    "World Tour Finals Race season already has a different snapshot"
                )
            return current
        self.session.add(
            WorldTourFinalsRaceSnapshotModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                season_index=snapshot.season_index,
                cutoff_week_ordinal=snapshot.cutoff_week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                command_id=snapshot.command_id,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        stored = self.get(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=snapshot.season_index,
        )
        if stored != snapshot:
            raise ValueError("World Tour Finals Race snapshot write could not be verified")
        return stored
