"""Real SQLite checkpoint roundtrip for *unpublished* calendar source staging."""

from __future__ import annotations

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_source_bundle import (
    CalendarRankingSourceBundle, load_calendar_ranking_source_bundle,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion, CalendarRankingZeroVersion,
)
from beta_engine.infrastructure.db.models import (
    StagedCalendarRankingResultVersionModel,
    StagedCalendarRankingZeroVersionModel,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    CalendarRankingStagingConflict, StagedCalendarRankingSourceStore,
)
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)
from tests.infrastructure.test_staged_calendar_ranking_sources import (
    rv, zv, scope, w,
)

pytestmark = pytest.mark.pr_critical
HEAD = "revision-1"


def _new_db(path, clock):
    path.mkdir()
    engine, factory, repository = _setup(path)
    _signed_test_calendar(factory, clock)
    return engine, factory, repository


def _install_sources(factory, W):
    first = rv(W)
    corrected = rv(W, after=first, at=w(1, 1), pts=145)
    zero = zv(W=W)
    revised = zv(W=W, after=zero, at=w(1, 2), duration=1)
    with factory.begin() as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        store = StagedCalendarRankingSourceStore(session)
        store.append_result(first, expected_saved_head_revision_id=HEAD)
        store.append_result(corrected, expected_saved_head_revision_id=HEAD)
        store.append_zero(zero, expected_saved_head_revision_id=HEAD)
        store.append_zero(revised, expected_saved_head_revision_id=HEAD)
    return (first, corrected), (zero, revised)


@pytest.mark.parametrize("W,offset", [(52, 1), (61, 37), (80, 37)])
def test_exact_source_bundle_copy_restart_idempotency_and_asof_replay(tmp_path, W, offset):
    clock = RunCalendar(W, offset, 2030, 3)
    original_engine, original_factory, original_repo = _new_db(tmp_path / "src", clock)
    new_engine, new_factory, new_repo = _new_db(tmp_path / "target", clock)
    try:
        expected_results, expected_zeros = _install_sources(original_factory, W)
        before = original_repo.get_branch_revision_state(branch_id="branch-1")
        with original_factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            source_bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
            assert source_bundle.results == expected_results
            assert source_bundle.zeros == expected_zeros
            payload_json = source_bundle.model_dump_json()
            expected_hash = source_bundle.fingerprint
        # The imported bundle is pinned to the *external* expected hash and
        # the target's *own* exact signed Saved HEAD + calendar identity.
        with new_factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            dest = StagedCalendarRankingSourceStore(session)
            assert dest.import_bundle(
                payload_json, expected_fingerprint=expected_hash, **scope(),
            ) == source_bundle
            assert dest.import_bundle(
                payload_json, expected_fingerprint=expected_hash, **scope(),
            ) == source_bundle
        new_engine.dispose()
        from beta_engine.infrastructure.db import (
            DatabaseSettings, create_session_factory, create_sqlite_engine,
        )
        reread_engine = create_sqlite_engine(DatabaseSettings(
            url=f"sqlite:///{tmp_path / 'target' / 'calendar-authority.db'}"
        ))
        try:
            reread_factory = create_session_factory(reread_engine)
            with reread_factory() as session:
                session.connection().exec_driver_sql("BEGIN")
                dest = StagedCalendarRankingSourceStore(session)
                assert dest.export_bundle(**scope()).fingerprint == expected_hash
                earlier = dest.resolve(**scope(week=w(0, W)))
                after = dest.resolve(**scope(week=w(1, 1)))
                assert earlier.results[0].main_points == 75
                assert earlier.disciplinary_zeros == ()
                assert after.results[0].main_points == 145
                assert after.disciplinary_zeros[0].zero_id == "sanction"
        finally:
            reread_engine.dispose()
        assert original_repo.get_branch_revision_state(branch_id="branch-1") == before
        assert original_repo.verify_branch_saved_revision_hash(revision_id=HEAD)
        assert new_repo.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        original_engine.dispose()
        new_engine.dispose()


def test_bundle_loader_rejects_hash_scope_calendar_and_source_history_tamper(tmp_path):
    clock = RunCalendar(52, 1, 2030, 3)
    engine, factory, _ = _new_db(tmp_path / "src", clock)
    try:
        _install_sources(factory, 52)
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
        kwargs = dict(
            expected_fingerprint=bundle.fingerprint,
            run_id="run-1", branch_id="branch-1",
            saved_head_revision_id=HEAD,
            saved_head_content_hash=bundle.saved_head_content_hash,
            run_calendar=clock,
        )
        assert load_calendar_ranking_source_bundle(bundle.model_dump_json(), **kwargs) == bundle
        with pytest.raises(ValueError, match="fingerprint"):
            load_calendar_ranking_source_bundle(
                bundle.model_dump_json(), **{**kwargs, "expected_fingerprint": "0" * 64},
            )
        with pytest.raises(ValueError, match="Saved origin/scope/clock"):
            load_calendar_ranking_source_bundle(
                bundle.model_dump_json(), **{**kwargs, "run_id": "foreign"},
            )
        with pytest.raises(ValueError, match="Saved origin/scope/clock"):
            load_calendar_ranking_source_bundle(
                bundle.model_dump_json(), **{**kwargs, "run_calendar": clock.extend_to(4)},
            )
        with pytest.raises(ValueError, match="Saved origin/scope/clock"):
            load_calendar_ranking_source_bundle(
                bundle.model_dump_json(), **{**kwargs, "saved_head_content_hash": "f" * 64},
            )
        raw = json.loads(bundle.model_dump_json())
        raw["results"][1]["previous_fingerprint"] = "a" * 64
        with pytest.raises(ValueError, match="lineage"):
            load_calendar_ranking_source_bundle(
                json.dumps(raw), **kwargs,
            )
        raw = json.loads(bundle.model_dump_json())
        raw["results"][0]["result"]["main_points"] = 10000
        with pytest.raises(ValueError, match="fingerprint"):
            load_calendar_ranking_source_bundle(
                json.dumps(raw), **kwargs,
            )
        with pytest.raises(ValueError, match="external bundle fingerprint"):
            load_calendar_ranking_source_bundle(
                bundle.model_dump_json(),
                **{**kwargs, "expected_fingerprint": "not-a-sha"},
            )
    finally:
        engine.dispose()


def test_bundle_import_conflict_is_atomic_and_does_not_merge_partial_history(tmp_path):
    clock = RunCalendar(80, 37, 2030, 3)
    a, fa, _ = _new_db(tmp_path / "src", clock)
    b, fb, _ = _new_db(tmp_path / "target", clock)
    try:
        _install_sources(fa, 80)
        with fa() as session:
            session.connection().exec_driver_sql("BEGIN")
            bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
        with fb.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            StagedCalendarRankingSourceStore(session).append_result(
                rv(80, edition="other-edition"), expected_saved_head_revision_id=HEAD,
            )
        with pytest.raises(CalendarRankingStagingConflict, match="different sources"):
            with fb.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).import_bundle(
                    bundle.model_dump_json(), expected_fingerprint=bundle.fingerprint,
                    **scope(),
                )
        with fb() as session:
            session.connection().exec_driver_sql("BEGIN")
            results, zeros = StagedCalendarRankingSourceStore(session).history(**scope())
            assert len(results) == 1
            assert results[0].result.edition_id == "other-edition"
            assert zeros == ()
    finally:
        a.dispose()
        b.dispose()


def test_bundle_import_rolls_back_after_partial_insert_error(tmp_path, monkeypatch):
    clock = RunCalendar(52, 1, 2030, 3)
    a, fa, _ = _new_db(tmp_path / "src", clock)
    b, fb, _ = _new_db(tmp_path / "target", clock)
    try:
        _install_sources(fa, 52)
        with fa() as session:
            session.connection().exec_driver_sql("BEGIN")
            bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
        original_export = StagedCalendarRankingSourceStore.export_bundle
        calls = []
        def interrupted(self, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("injected failure after flush")
            return original_export(self, **kwargs)
        monkeypatch.setattr(StagedCalendarRankingSourceStore, "export_bundle", interrupted)
        with pytest.raises(RuntimeError, match="injected failure"):
            with fb.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).import_bundle(
                    bundle.model_dump_json(), expected_fingerprint=bundle.fingerprint,
                    **scope(),
                )
        monkeypatch.setattr(StagedCalendarRankingSourceStore, "export_bundle", original_export)
        with fb() as session:
            session.connection().exec_driver_sql("BEGIN")
            assert StagedCalendarRankingSourceStore(session).history(**scope()) == ((), ())
        with fb.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            assert StagedCalendarRankingSourceStore(session).import_bundle(
                bundle.model_dump_json(), expected_fingerprint=bundle.fingerprint,
                **scope(),
            ).fingerprint == bundle.fingerprint
    finally:
        a.dispose()
        b.dispose()


def test_import_fails_after_saved_clock_changes_and_rejects_corrupt_storage(tmp_path):
    clock = RunCalendar(52, 1, 2030, 3)
    a, fa, _ = _new_db(tmp_path / "src", clock)
    b, fb, _ = _new_db(tmp_path / "target", clock)
    try:
        _install_sources(fa, 52)
        with fa() as session:
            session.connection().exec_driver_sql("BEGIN")
            bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
        _signed_test_calendar(fb, clock.extend_to(4))
        with pytest.raises(ValueError, match="Saved origin/scope/clock"):
            with fb.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                StagedCalendarRankingSourceStore(session).import_bundle(
                    bundle.model_dump_json(), expected_fingerprint=bundle.fingerprint,
                    **scope(),
                )
        # On the unchanged source, corrupting one SQLite record must make
        # export fail closed instead of producing a fresh valid bundle.
        with fa.begin() as session:
            row = session.get(StagedCalendarRankingResultVersionModel, (
                "run-1", "branch-1", "event", "p", 51,
            ))
            row.fingerprint = "f" * 64
        with fa() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="identity/hash"):
                StagedCalendarRankingSourceStore(session).export_bundle(**scope())
    finally:
        a.dispose()
        b.dispose()


def test_import_requires_real_sqlite_transaction(tmp_path):
    clock = RunCalendar(52, 1, 2030, 3)
    a, fa, _ = _new_db(tmp_path / "src", clock)
    b, fb, _ = _new_db(tmp_path / "target", clock)
    try:
        _install_sources(fa, 52)
        with fa() as session:
            session.connection().exec_driver_sql("BEGIN")
            bundle = StagedCalendarRankingSourceStore(session).export_bundle(**scope())
        with fb() as session:
            with pytest.raises(ValueError, match="caller transaction"):
                StagedCalendarRankingSourceStore(session).import_bundle(
                    bundle.model_dump_json(), expected_fingerprint=bundle.fingerprint,
                    **scope(),
                )
    finally:
        a.dispose()
        b.dispose()
