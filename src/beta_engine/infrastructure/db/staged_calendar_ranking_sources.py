"""SQLite staging of calendar-owned ranking sources, NOT Official publication.

This module deliberately owns distinct tables from legacy FAX RankingWeek and
RankingRevisionState. Rows survive restart, but are NOT yet part of user-visible
Saved Revision/restore/fork. They MUST NOT be used as authoritative match facts
or published to Viewer. Internal callers provide reviewed/proven source records.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import CalendarRankingWeek
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
    CalendarRankingZeroVersion,
    ResolvedCalendarRankingSources,
    resolve_calendar_ranking_sources,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    StagedCalendarRankingResultVersionModel,
    StagedCalendarRankingZeroVersionModel,
)


class CalendarRankingStagingConflict(ValueError):
    """Existing immutable staging data is different from this request."""


class StagedCalendarRankingSourceStore:
    """Transaction-owned, fail-closed store for *unpublished* source evidence.

    All reads require a caller-owned physical SQLite read snapshot (BEGIN).
    Writes additionally require the caller to acquire BEGIN IMMEDIATE before
    loading any rows. No transaction is committed here. SQLite unique keys
    protect a concurrent duplicate, which the caller must roll back and retry
    in a new transaction. The caller must independently verify source receipts.
    """

    def __init__(self, session: Session):
        self.session = session

    def _transaction(self) -> None:
        if not self.session.in_transaction():
            raise ValueError("Calendar ranking staging requires a caller transaction")
        connection = self.session.connection()
        raw = connection.connection.driver_connection
        if (
            connection.dialect.name != "sqlite"
            or raw is None
            or not raw.in_transaction
        ):
            raise ValueError("Calendar ranking staging requires a physical SQLite transaction")

    def _scope(
        self, *, run_id: str, branch_id: str,
        expected_saved_head_revision_id: str, writing: bool = False,
    ) -> RunCalendar:
        self._transaction()
        if not expected_saved_head_revision_id:
            raise ValueError("Expected Saved HEAD is required")
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Calendar ranking staging Run/Branch scope does not exist")
        if branch.saved_head_revision_id != expected_saved_head_revision_id:
            raise ValueError("Calendar ranking staging uses a stale Saved HEAD")
        if branch.forked_from_branch_id is not None:
            raise ValueError("Forked calendar staging requires a dedicated ancestry adapter")
        clock = resolve_saved_run_calendar(
            self.session, run_id=run_id, branch_id=branch_id,
        )
        if clock.schema_version != "run_calendar.v1":
            raise ValueError("Legacy FAX source records cannot be reinterpreted as calendar staging")
        if writing:
            if run.read_only or branch.read_only:
                raise ValueError("Calendar ranking staging scope is read-only")
            # This staging store has no Saved publication/restore integration.
            # Never permit writes alongside already authoritative sporting history.
            if (
                self.session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
                is not None
                or self.session.scalar(
                    select(PublishedOfficialRankingModel.week_ordinal).where(
                        PublishedOfficialRankingModel.run_id == run_id,
                        PublishedOfficialRankingModel.branch_id == branch_id,
                    ).limit(1)
                ) is not None
            ):
                raise ValueError("Published sporting state cannot use unpublished calendar staging")
        return clock

    def _load(
        self, *, run_id: str, branch_id: str, clock: RunCalendar,
    ) -> tuple[
        tuple[CalendarRankingResultVersion, ...],
        tuple[CalendarRankingZeroVersion, ...],
    ]:
        result_rows = self.session.scalars(
            select(StagedCalendarRankingResultVersionModel)
            .where(
                StagedCalendarRankingResultVersionModel.run_id == run_id,
                StagedCalendarRankingResultVersionModel.branch_id == branch_id,
            )
            .order_by(
                StagedCalendarRankingResultVersionModel.edition_id,
                StagedCalendarRankingResultVersionModel.player_id,
                StagedCalendarRankingResultVersionModel.effective_ordinal,
            )
        ).all()
        zero_rows = self.session.scalars(
            select(StagedCalendarRankingZeroVersionModel)
            .where(
                StagedCalendarRankingZeroVersionModel.run_id == run_id,
                StagedCalendarRankingZeroVersionModel.branch_id == branch_id,
            )
            .order_by(
                StagedCalendarRankingZeroVersionModel.zero_id,
                StagedCalendarRankingZeroVersionModel.effective_ordinal,
            )
        ).all()
        results = []
        zeros = []
        for row in result_rows:
            version = CalendarRankingResultVersion.model_validate_json(row.payload_json)
            if (
                (version.run_id, version.branch_id, version.result.edition_id,
                 version.result.player_id, clock.ordinal(
                     version.effective_week.season_index, version.effective_week.week
                 ), version.fingerprint)
                != (run_id, branch_id, row.edition_id, row.player_id,
                    row.effective_ordinal, row.fingerprint)
            ):
                raise ValueError("Stored calendar result source identity/hash mismatch")
            results.append(version)
        for row in zero_rows:
            version = CalendarRankingZeroVersion.model_validate_json(row.payload_json)
            if (
                (version.zero.run_id, version.zero.branch_id, version.zero.zero_id,
                 clock.ordinal(
                     version.effective_week.season_index, version.effective_week.week
                 ), version.fingerprint)
                != (run_id, branch_id, row.zero_id, row.effective_ordinal,
                    row.fingerprint)
            ):
                raise ValueError("Stored calendar zero source identity/hash mismatch")
            zeros.append(version)
        # Validate complete histories, including future-dated corrections,
        # before handing any subset to a ranking calculation.
        ordinals = [row.effective_ordinal for row in (*result_rows, *zero_rows)]
        check_at = max(ordinals, default=0)
        position = clock.position_at_ordinal(check_at)
        resolve_calendar_ranking_sources(
            run_calendar=clock, run_id=run_id, branch_id=branch_id,
            week=CalendarRankingWeek(
                season_index=position.season_index, week=position.season_week,
            ),
            result_versions=tuple(results), zero_versions=tuple(zeros),
        )
        return tuple(results), tuple(zeros)

    def history(
        self, *, run_id: str, branch_id: str,
        expected_saved_head_revision_id: str,
    ) -> tuple[
        tuple[CalendarRankingResultVersion, ...],
        tuple[CalendarRankingZeroVersion, ...],
    ]:
        clock = self._scope(
            run_id=run_id, branch_id=branch_id,
            expected_saved_head_revision_id=expected_saved_head_revision_id,
        )
        return self._load(run_id=run_id, branch_id=branch_id, clock=clock)

    def resolve(
        self, *, run_id: str, branch_id: str,
        expected_saved_head_revision_id: str, week: CalendarRankingWeek,
    ) -> ResolvedCalendarRankingSources:
        clock = self._scope(
            run_id=run_id, branch_id=branch_id,
            expected_saved_head_revision_id=expected_saved_head_revision_id,
        )
        results, zeros = self._load(
            run_id=run_id, branch_id=branch_id, clock=clock,
        )
        return resolve_calendar_ranking_sources(
            run_calendar=clock, run_id=run_id, branch_id=branch_id,
            week=week, result_versions=results, zero_versions=zeros,
        )

    def append_result(
        self, version: CalendarRankingResultVersion, *,
        expected_saved_head_revision_id: str,
    ) -> CalendarRankingResultVersion:
        version = CalendarRankingResultVersion.model_validate_json(
            version.model_dump_json()
        )
        clock = self._scope(
            run_id=version.run_id, branch_id=version.branch_id,
            expected_saved_head_revision_id=expected_saved_head_revision_id,
            writing=True,
        )
        existing_results, zeros = self._load(
            run_id=version.run_id, branch_id=version.branch_id, clock=clock,
        )
        for existing in existing_results:
            if (
                existing.result.edition_id, existing.result.player_id,
                existing.effective_week,
            ) == (
                version.result.edition_id, version.result.player_id,
                version.effective_week,
            ):
                if existing.fingerprint != version.fingerprint:
                    raise CalendarRankingStagingConflict(
                        "Conflicting calendar ranking result at effective week"
                    )
                return existing
        candidate = tuple(sorted(
            (*existing_results, version),
            key=lambda v: (
                v.result.edition_id, v.result.player_id,
                clock.ordinal(v.effective_week.season_index, v.effective_week.week),
            ),
        ))
        resolve_calendar_ranking_sources(
            run_calendar=clock, run_id=version.run_id,
            branch_id=version.branch_id, week=version.effective_week,
            result_versions=candidate, zero_versions=zeros,
        )
        self.session.add(StagedCalendarRankingResultVersionModel(
            run_id=version.run_id, branch_id=version.branch_id,
            edition_id=version.result.edition_id, player_id=version.result.player_id,
            effective_ordinal=clock.ordinal(
                version.effective_week.season_index, version.effective_week.week,
            ),
            fingerprint=version.fingerprint, payload_json=version.model_dump_json(),
        ))
        self.session.flush()
        return version

    def append_zero(
        self, version: CalendarRankingZeroVersion, *,
        expected_saved_head_revision_id: str,
    ) -> CalendarRankingZeroVersion:
        version = CalendarRankingZeroVersion.model_validate_json(
            version.model_dump_json()
        )
        zero = version.zero
        clock = self._scope(
            run_id=zero.run_id, branch_id=zero.branch_id,
            expected_saved_head_revision_id=expected_saved_head_revision_id,
            writing=True,
        )
        results, existing_zeros = self._load(
            run_id=zero.run_id, branch_id=zero.branch_id, clock=clock,
        )
        for existing in existing_zeros:
            if (existing.zero.zero_id, existing.effective_week) == (
                zero.zero_id, version.effective_week,
            ):
                if existing.fingerprint != version.fingerprint:
                    raise CalendarRankingStagingConflict(
                        "Conflicting calendar ranking zero at effective week"
                    )
                return existing
        candidate = tuple(sorted(
            (*existing_zeros, version),
            key=lambda v: (
                v.zero.zero_id,
                clock.ordinal(v.effective_week.season_index, v.effective_week.week),
            ),
        ))
        resolve_calendar_ranking_sources(
            run_calendar=clock, run_id=zero.run_id, branch_id=zero.branch_id,
            week=version.effective_week,
            result_versions=results, zero_versions=candidate,
        )
        self.session.add(StagedCalendarRankingZeroVersionModel(
            run_id=zero.run_id, branch_id=zero.branch_id,
            zero_id=zero.zero_id,
            effective_ordinal=clock.ordinal(
                version.effective_week.season_index, version.effective_week.week,
            ),
            fingerprint=version.fingerprint, payload_json=version.model_dump_json(),
        ))
        self.session.flush()
        return version
