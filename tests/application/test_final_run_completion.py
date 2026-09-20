import json

import pytest

from beta_engine.application.final_run_completion import stage_final_run_completion
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.run_containers import (
    ARCHIVED_RUN_STATUS,
    COMPLETED_RUN_STATUS,
    LEGACY_ACTIVE_RUN_STATUS,
    WORKING_RUN_STATUS,
)
from beta_engine.domain.run_revisions import CONTENT_HASH_ALGORITHM
from beta_engine.domain.season_closure import (
    ClosureRuleVersionRef,
    SeasonClosureMarkerCandidate,
    SeasonClosurePackage,
    SeasonSummarySnapshot,
    bind_season_closure_marker,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    BranchSavedRevisionModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'final-run-completion.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    yield factory
    engine.dispose()


def _closure_payload(*, revision_id: str, season_index: int = 49) -> dict:
    week = RankingWeek(season_index=season_index, week=61)
    summary = SeasonSummarySnapshot(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        closing_ranking_fingerprint="a" * 64,
    )
    candidate = SeasonClosureMarkerCandidate(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        season_summary_fingerprint=summary.fingerprint,
        closing_ranking_fingerprint=summary.closing_ranking_fingerprint,
        rule_versions=(
            ClosureRuleVersionRef(
                rule_kind="official_ranking_policy",
                rule_id="final-policy",
                fingerprint="b" * 64,
            ),
        ),
    )
    package = SeasonClosurePackage(summary=summary, marker=candidate)
    marker = bind_season_closure_marker(
        candidate,
        final_saved_revision_id=revision_id,
    )
    payload = {
        "run": {"run_id": "run", "status": WORKING_RUN_STATUS},
        "branch": {"branch_id": "branch"},
        "content": {},
    }
    install_saved_revision_season_closure(
        payload,
        package=package,
        marker=marker,
    )
    return payload


def _install_scope(
    session,
    *,
    status: str,
    revision_id: str = "final-revision",
    season_index: int = 49,
    with_closure: bool = True,
    head_revision_id: str | None = None,
):
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Final Run",
            storage_kind="custom_local",
            read_only=0,
            timeline_start_season=2000,
            timeline_end_season=2049,
            official_branch_id="branch",
            status=status,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
            status="active",
            read_only=0,
            saved_head_revision_id=head_revision_id or revision_id,
        )
    )
    payload = (
        _closure_payload(revision_id=revision_id, season_index=season_index)
        if with_closure
        else {"run": {}, "branch": {}, "content": {}}
    )
    session.add(
        BranchSavedRevisionModel(
            revision_id=revision_id,
            run_id="run",
            branch_id="branch",
            sequence=2,
            parent_revision_id="previous",
            kind="final_run_closure",
            payload_schema_version="run_saved_revision_v1",
            content_hash_algorithm=CONTENT_HASH_ALGORITHM,
            content_hash="c" * 64,
            payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            change_summary_json="{}",
        )
    )
    session.flush()


@pytest.mark.pr_critical
@pytest.mark.parametrize("status", [WORKING_RUN_STATUS, LEGACY_ACTIVE_RUN_STATUS])
def test_final_run_completion_accepts_canonical_and_legacy_precompletion_status(
    database,
    status,
):
    with database.begin() as session:
        _install_scope(session, status=status)
        result = stage_final_run_completion(
            session,
            run_id="run",
            branch_id="branch",
            final_saved_revision_id="final-revision",
        )
        assert result.previous_status == status
        assert result.status == COMPLETED_RUN_STATUS
        assert result.completed_week == RankingWeek(season_index=49, week=61)
        assert session.get(RunContainerModel, "run").status == COMPLETED_RUN_STATUS


@pytest.mark.pr_critical
def test_final_run_completion_exact_retry_is_idempotent(database):
    with database.begin() as session:
        _install_scope(session, status=WORKING_RUN_STATUS)
        first = stage_final_run_completion(
            session,
            run_id="run",
            branch_id="branch",
            final_saved_revision_id="final-revision",
        )
        second = stage_final_run_completion(
            session,
            run_id="run",
            branch_id="branch",
            final_saved_revision_id="final-revision",
        )
        assert first.previous_status == WORKING_RUN_STATUS
        assert second.previous_status == COMPLETED_RUN_STATUS
        assert second.status == COMPLETED_RUN_STATUS


@pytest.mark.parametrize(
    ("status", "season_index", "with_closure", "head_revision_id", "message"),
    [
        (
            ARCHIVED_RUN_STATUS,
            49,
            True,
            None,
            "cannot transition to Completed",
        ),
        (
            WORKING_RUN_STATUS,
            48,
            True,
            None,
            "only after 2049/50 Week 61",
        ),
        (
            WORKING_RUN_STATUS,
            49,
            False,
            None,
            "requires Season Closure evidence",
        ),
        (
            WORKING_RUN_STATUS,
            49,
            True,
            "other-revision",
            "not the Branch head",
        ),
    ],
)
def test_final_run_completion_fails_closed(
    database,
    status,
    season_index,
    with_closure,
    head_revision_id,
    message,
):
    with database.begin() as session:
        _install_scope(
            session,
            status=status,
            season_index=season_index,
            with_closure=with_closure,
            head_revision_id=head_revision_id,
        )
        with pytest.raises(ValueError, match=message):
            stage_final_run_completion(
                session,
                run_id="run",
                branch_id="branch",
                final_saved_revision_id="final-revision",
            )
