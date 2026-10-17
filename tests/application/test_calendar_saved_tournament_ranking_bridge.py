"""Real signed Saved + canonical SQLite owned tournament -> calendar candidate."""

from __future__ import annotations

import json

import pytest

from beta_engine.application.calendar_saved_tournament_ranking_bridge import (
    preview_saved_canonical_tournament_ranking,
    saved_canonical_tournament_ranking_sources,
)
from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding, prepare_canonical_tournament_ranking_sources,
)
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer, CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.domain.tournaments.result_authority import (
    TournamentResultAuthority, TournamentPlayerResultAuthority,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel, OwnedTournamentRankingSourceModel, RunBranchModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)


pytestmark = pytest.mark.pr_critical
RUN, BRANCH, HEAD = "run-1", "branch-1", "revision-1"


def w(s: int, n: int) -> CalendarRankingWeek:
    return CalendarRankingWeek(season_index=s, week=n)


def _source(*, closing: bool = False, legacy_schema: str = "owned_tournament_ranking_source.v4"):
    completed = RankingWeek(season_index=0, week=1)
    result = TournamentResultAuthority(
        run_id=RUN, branch_id=BRANCH, event_id="event",
        completed_week=completed,
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="A", finalist_player_id="B",
        players=(
            TournamentPlayerResultAuthority(
                player_id="A", draw_type="main",
                reached_stage="champion",
            ),
            TournamentPlayerResultAuthority(
                player_id="B", draw_type="main",
                reached_stage="finalist",
            ),
        ),
        matches=(),
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={"champion": 100, "finalist": 60},
            point_distribution_source="calendar_event.ranking_points_table",
        ),
        seed=77,
    )
    binding = TournamentRankingBinding(
        run_id=RUN, branch_id=BRANCH,
        edition_id="event", event_id="event",
        completed_week=completed,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )
    return OwnedTournamentRankingSource(
        schema_version=legacy_schema,
        binding=binding,
        canonical_result=result,
        canonical_awards=awards,
        adopted_by_command_id="close-event",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )


def _sign_ranking_component(factory, source, *, versions=()):
    state = RankingRevisionState(
        run_id=RUN, branch_id=BRANCH, entries=(),
        sources=versions, tournament_sources=(source,),
    )
    with factory.begin() as session:
        rev = session.get(BranchSavedRevisionModel, HEAD)
        payload = json.loads(rev.payload_json)
        payload["content"]["ranking_preparation"] = {
            "fingerprint": state.fingerprint,
            "state": state.model_dump(mode="json"),
        }
        rev.payload_json = json.dumps(payload)
        rev.content_hash = saved_revision_content_hash(
            revision_id=rev.revision_id, run_id=rev.run_id,
            branch_id=rev.branch_id, sequence=rev.sequence,
            parent_revision_id=rev.parent_revision_id,
            kind=rev.kind, payload_schema_version=rev.payload_schema_version,
            payload=payload,
            change_summary=json.loads(rev.change_summary_json),
        )


def _setup_saved(tmp_path, *, saved=True, live=True, clock=None, saved_versions=()):
    engine, factory, repo = _setup(tmp_path)
    _signed_test_calendar(
        factory, clock or RunCalendar.fax_default(),
    )
    source = _source()
    if saved:
        _sign_ranking_component(factory, source, versions=saved_versions)
    if live:
        with factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(source)
    return engine, factory, repo, source


def scope(**kwargs):
    return dict(run_id=RUN, branch_id=BRANCH,
                expected_saved_head_revision_id=HEAD,
                edition_id="event", **kwargs)


def _read(factory, **kwargs):
    with factory() as session:
        session.connection().exec_driver_sql("BEGIN")
        return saved_canonical_tournament_ranking_sources(session, **scope(**kwargs))


@pytest.mark.parametrize("source_schema", ["v4"])
def test_canonical_saved_tournament_bridge_real_sqlite_and_candidate_replay(tmp_path, source_schema):
    engine, factory, repo, source = _setup_saved(tmp_path)
    try:
        before = repo.get_branch_revision_state(branch_id=BRANCH)
        versions = _read(factory)
        assert len(versions) == 2
        assert [v.result.player_id for v in versions] == ["A", "B"]
        expected = prepare_canonical_tournament_ranking_sources(
            source.binding, source.canonical_result, source.canonical_awards,
        )
        assert [v.result.main_points for v in versions] == [
            v.result.main_points for v in expected
        ]
        assert versions[0].result.source_fingerprint == expected[0].result.source_fingerprint
        assert versions[0].effective_week == w(0, 2)
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            candidate, manifest = preview_saved_canonical_tournament_ranking(
                session, **scope(), week=w(0, 2),
                policy=OfficialRankingPolicy(policy_id="best2", best_n=2),
                players=(
                    CalendarRankingPlayer(
                        player_id="A", tie_break_token="A",
                        tour_entry_week=w(0, 1),
                    ),
                    CalendarRankingPlayer(
                        player_id="B", tie_break_token="B",
                        tour_entry_week=w(0, 1),
                    ),
                ),
            )
            assert [(r.player_id, r.points) for r in candidate.rows] == [
                ("A", 100), ("B", 60),
            ]
            assert manifest.results == tuple(v.result for v in versions)
            assert candidate.run_calendar == RunCalendar.fax_default().to_metadata()
            assert saved_canonical_tournament_ranking_sources(
                session, **scope(),
            ) == versions
        assert repo.get_branch_revision_state(branch_id=BRANCH) == before
        assert repo.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


@pytest.mark.parametrize("saved,live,error", [
    (False, True, "lacks a ranking preparation component"),
    (True, False, "differs from its live owned row"),
])
def test_unsaved_or_missing_live_tournament_never_becomes_ranking_fact(tmp_path, saved, live, error):
    engine, factory, _, _ = _setup_saved(tmp_path, saved=saved, live=live)
    try:
        with pytest.raises(ValueError, match=error):
            _read(factory)
    finally:
        engine.dispose()


def test_stale_saved_head_and_invalid_clock_are_rejected_before_source_projection(tmp_path):
    engine, factory, _, _ = _setup_saved(tmp_path)
    try:
        with pytest.raises(ValueError, match="stale Saved HEAD"):
            _read(factory, expected_saved_head_revision_id="stale")
        _signed_test_calendar(factory, RunCalendar(52, 1, 2000, 50))
        with pytest.raises(ValueError, match="only supports explicit FAX"):
            _read(factory)
        _signed_test_calendar(factory, RunCalendar(80, 37, 2000, 50))
        with pytest.raises(ValueError, match="only supports explicit FAX"):
            _read(factory)
    finally:
        engine.dispose()


def test_live_row_corruption_or_missing_save_authority_is_rejected(tmp_path):
    engine, factory, _, source = _setup_saved(tmp_path)
    try:
        with factory.begin() as session:
            row = session.get(OwnedTournamentRankingSourceModel, (
                RUN, BRANCH, "event",
            ))
            row.source_fingerprint = "f" * 64
        with pytest.raises(ValueError, match="fingerprint"):
            _read(factory)
    finally:
        engine.dispose()


def test_signed_ranking_result_disagreement_is_rejected(tmp_path):
    source = _source()
    versions = prepare_canonical_tournament_ranking_sources(
        source.binding, source.canonical_result, source.canonical_awards,
    )
    bad = versions[0].model_copy(update={
        "result": versions[0].result.model_copy(update={"main_points": 999})
    })
    engine, factory, _, _ = _setup_saved(
        tmp_path, saved_versions=(bad, versions[1]),
    )
    try:
        with pytest.raises(ValueError, match="contradict canonical awards"):
            _read(factory)
    finally:
        engine.dispose()


def test_forked_branch_and_invalid_read_transaction_are_blocked(tmp_path):
    engine, factory, _, _ = _setup_saved(tmp_path)
    try:
        with factory() as session:
            with pytest.raises(ValueError, match="caller read transaction"):
                saved_canonical_tournament_ranking_sources(session, **scope())
        with factory.begin() as session:
            session.get(RunBranchModel, BRANCH).forked_from_branch_id = "parent-branch"
        with pytest.raises(ValueError, match="Forked tournament ranking"):
            _read(factory)
    finally:
        engine.dispose()


def test_saved_component_fingerprint_corruption_is_rejected(tmp_path):
    engine, factory, _, _ = _setup_saved(tmp_path)
    try:
        with factory.begin() as session:
            rev = session.get(BranchSavedRevisionModel, HEAD)
            payload = json.loads(rev.payload_json)
            payload["content"]["ranking_preparation"]["fingerprint"] = "0" * 64
            rev.payload_json = json.dumps(payload)
            rev.content_hash = saved_revision_content_hash(
                revision_id=rev.revision_id, run_id=rev.run_id,
                branch_id=rev.branch_id, sequence=rev.sequence,
                parent_revision_id=rev.parent_revision_id, kind=rev.kind,
                payload_schema_version=rev.payload_schema_version,
                payload=payload,
                change_summary=json.loads(rev.change_summary_json),
            )
        with pytest.raises(ValueError, match="fingerprint"):
            _read(factory)
    finally:
        engine.dispose()


def test_saved_revision_hash_corruption_is_rejected(tmp_path):
    engine, factory, _, _ = _setup_saved(tmp_path)
    try:
        with factory.begin() as session:
            session.get(BranchSavedRevisionModel, HEAD).content_hash = "f" * 64
        with pytest.raises(ValueError, match="hash"):
            _read(factory)
    finally:
        engine.dispose()
