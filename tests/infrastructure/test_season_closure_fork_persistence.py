"""Cross-Branch Season Closure identity and transactional archive installation.

Real SQLite / model storage; no production Season Transition fork is enabled yet.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from test_season_closing_fork_proof import _case
from test_season_closing_ranking_fork_remap import _ledger

from beta_engine.domain.season_closure import (
    bind_season_closure_marker,
    build_season_closure_package,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
    rebind_cross_branch_season_closure,
)
from beta_engine.infrastructure.db.season_closing_fork_install import (
    install_verified_fork_season_closings,
)
from beta_engine.infrastructure.db.season_closing_fork_proof import (
    rebind_verified_season_closing_ranking,
)
from beta_engine.infrastructure.db.ranking_fork_remap import (
    _remap_season_closing_archives,
)
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingStore,
)


pytestmark = pytest.mark.pr_critical


def _closure_case():
    original, proof = _case()
    target = rebind_verified_season_closing_ranking(original, **proof)
    package = build_season_closure_package(closing_ranking=original)
    marker = bind_season_closure_marker(
        package.marker, final_saved_revision_id="source-season-revision",
    )
    source_payload = {"content": {}}
    install_saved_revision_season_closure(
        source_payload, package=package, marker=marker,
    )
    return source_payload, original, target


def test_cross_branch_closure_binds_verified_target_revision_without_mutating_source():
    source, original, target = _closure_case()
    original_copy = deepcopy(source)
    target_payload = deepcopy(source)
    new = rebind_cross_branch_season_closure(
        source, target_payload,
        run_id="run", source_branch_id="source",
        source_revision_id="source-season-revision",
        target_branch_id="target", target_revision_id="target-fork-root",
        source_closing=original, target_closing=target,
    )
    assert source == original_copy
    assert new.parsed_summary.closing_ranking_fingerprint == target.fingerprint
    assert new.parsed_marker.final_saved_revision_id == "target-fork-root"
    assert new.parsed_marker.branch_id == "target"
    assert new.parsed_summary.fingerprint != (
        load_saved_revision_season_closure(
            source, run_id="run", branch_id="source",
            revision_id="source-season-revision",
        ).parsed_summary.fingerprint
    )
    assert load_saved_revision_season_closure(
        target_payload, run_id="run", branch_id="target",
        revision_id="target-fork-root",
    ) == new


@pytest.mark.parametrize("tamper", ["wrong_source_revision", "forged_marker", "different_result"])
def test_cross_branch_closure_rejects_unproven_source_and_sporting_changes(tamper):
    source, original, target = _closure_case()
    candidate = deepcopy(source)
    original_target = deepcopy(candidate)
    source_revision_id = "source-season-revision"
    if tamper == "wrong_source_revision":
        source_revision_id = "foreign-source"
    elif tamper == "forged_marker":
        candidate["content"]["season_closure"]["fingerprint"] = "0" * 64
    else:
        target = target.model_copy(update={"rows": ()})
    with pytest.raises(ValueError, match="(?i)season closure|cross-branch"):
        rebind_cross_branch_season_closure(
            candidate, original_target,
            run_id="run", source_branch_id="source",
            source_revision_id=source_revision_id,
            target_branch_id="target", target_revision_id="fork-revision",
            source_closing=original, target_closing=target,
        )
    # Failed construction cannot partly overwrite the copied target content.
    assert original_target == source


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'season-fork.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(RunContainerModel(
            run_id="run", timeline_start_season=2000,
            timeline_end_season=2049,
        ))
        session.add(RunBranchModel(
            run_id="run", branch_id="source", display_name="Timeline 1",
        ))
        session.add(RunBranchModel(
            run_id="run", branch_id="target", display_name="Timeline 2",
            forked_from_branch_id="source",
        ))
    yield factory
    engine.dispose()


def _ranking_case():
    source, entries, results = _ledger()
    source.run_id, source.branch_id = "run", "source"
    target = SimpleNamespace(
        run_id="run", branch_id="target", entries=entries,
        sources=results, zero_sources=(), season_closing_rankings=(),
    )
    expected = _remap_season_closing_archives(
        source, target_entries=entries,
        target_sources=results, target_zero_sources=(),
        target_branch_id="target",
    )
    return source, target, expected


def _publish_week61(session, state):
    snapshot = state.entries[0].snapshot
    session.add(PublishedOfficialRankingModel(
        run_id="run", branch_id="target",
        week_ordinal=snapshot.week.ordinal,
        snapshot_fingerprint=snapshot.fingerprint,
        payload_json=snapshot.model_dump_json(),
    ))
    session.flush()


def test_sqlite_installs_verified_target_archive_against_real_publication(database):
    source, target, expected = _ranking_case()
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        _publish_week61(session, target)
        assert install_verified_fork_season_closings(
            session, source_state=source, target_state=target,
            proposed_archives=expected,
            run_id="run", source_branch_id="source",
            target_branch_id="target",
        ) == expected
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="target",
        ) == expected
    with database() as session:
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="target",
        ) == expected


def test_sqlite_fork_rejects_forged_archive_and_rolls_back_on_later_error(database):
    source, target, expected = _ranking_case()
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        _publish_week61(session, target)
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        forged = (expected[0].model_copy(update={"input_fingerprint": "0" * 64}),)
        with pytest.raises(ValueError, match="verified ranking replay"):
            install_verified_fork_season_closings(
                session, source_state=source, target_state=target,
                proposed_archives=forged,
                run_id="run", source_branch_id="source",
                target_branch_id="target",
            )
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="target",
        ) == ()
    with pytest.raises(RuntimeError, match="abort outer fork"):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            install_verified_fork_season_closings(
                session, source_state=source, target_state=target,
                proposed_archives=expected,
                run_id="run", source_branch_id="source",
                target_branch_id="target",
            )
            raise RuntimeError("abort outer fork")
    with database() as session:
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="target",
        ) == ()
