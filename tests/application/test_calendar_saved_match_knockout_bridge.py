"""Real seeded Run-owned Simulation Slot matches as Signed Saved ranking evidence."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import sessionmaker

from beta_engine.application.authoritative_slot_matches import (
    execute_supported_four_player_tournament,
)
from beta_engine.application.calendar_saved_match_knockout_bridge import (
    preview_saved_slot_verified_knockout_ranking,
    saved_slot_verified_knockout_evidence,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy, RankingWeek,
)
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.domain.tournaments.calendar_knockout_engine_witness import (
    prepare_calendar_engine_knockout_versions,
)
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutMatch, CalendarKnockoutRankingEvidence,
)
from beta_engine.infrastructure.db import SimulationPersistenceRepository
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel, RunBranchModel, RunContainerModel,
    SimulationEventGroupModel,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
)
from tests.application.test_authoritative_slot_matches import session_at

pytestmark = pytest.mark.pr_critical

RUN, BRANCH, HEAD = "run", "branch", "revision"
EVENT = "saved-engine-open"


def w(s, n):
    return CalendarRankingWeek(season_index=s, week=n)


def _resign_saved(session, modify):
    revision = session.get(BranchSavedRevisionModel, HEAD)
    payload = json.loads(revision.payload_json)
    modify(payload)
    revision.payload_json = json.dumps(payload)
    revision.content_hash = saved_revision_content_hash(
        revision_id=revision.revision_id, run_id=revision.run_id,
        branch_id=revision.branch_id, sequence=revision.sequence,
        parent_revision_id=revision.parent_revision_id, kind=revision.kind,
        payload_schema_version=revision.payload_schema_version,
        payload=payload,
        change_summary=json.loads(revision.change_summary_json),
    )


def _setup_real_completed_saved(tmp_path):
    session = session_at(tmp_path / "real-slots.db")
    engine = session.get_bind()
    factory = sessionmaker(bind=engine)
    repository = SimulationPersistenceRepository(
        engine=engine, session_factory=factory,
    )
    ids = iter((RUN, BRANCH, HEAD, "draft"))
    RunContainerCreationService(
        repository=repository, id_factory=lambda _: next(ids),
    ).create_empty_run(display_name="Saved match authority",calendar=RunCalendar.fax_default())
    result = execute_supported_four_player_tournament(
        session, run_id=RUN, branch_id=BRANCH,
        week=RankingWeek(season_index=0, week=1),
        event_id=EVENT, ordered_player_ids=("a","b","c","d"),
        seed=83017,
    )
    session.commit()
    session.close()
    # Build an authentic Saved component using the same production capture
    # path as Run Save. Fixture-only manual revision rehash is not a product API.
    with factory.begin() as s:
        _resign_saved(s,lambda payload: capture_saved_simulation_slots(
            s,payload,run_id=RUN,branch_id=BRANCH,
        ))
    source_matches = (
        *result.semifinal_groups, result.final_group,
    )
    bracket = CalendarKnockoutRankingEvidence(
        run_id=RUN, branch_id=BRANCH, edition_id=EVENT,
        run_calendar=RunCalendar.fax_default().to_metadata(),
        completed_week=w(0,1), first_publication_week=w(0,2),
        entrants_by_bracket_position=("a","b","c","d"),
        matches=tuple(CalendarKnockoutMatch(
            match_id=group.result.match_id,
            round_number=1 if i<2 else 2,
            bracket_position=i+1 if i<2 else 1,
            winner_player_id=group.result.winner_player_id,
            loser_player_id=group.result.loser_player_id,
            scoreline=(
                f"{group.result.sets_won[group.result.winner_player_id]}-"
                f"{group.result.sets_won[group.result.loser_player_id]}"
            ),
        ) for i,group in enumerate(source_matches)),
        point_distribution=(
            ("champion", 100), ("finalist", 60), ("semifinal", 30),
        ),
        point_distribution_source="authored:signed-test-table",
    )
    return engine, factory, repository, bracket, result


def _read(factory,bracket,**kwargs):
    with factory() as s:
        s.connection().exec_driver_sql("BEGIN")
        args=dict(bracket=bracket,expected_saved_head_revision_id=HEAD)
        args.update(kwargs)
        return saved_slot_verified_knockout_evidence(s,**args)


def test_real_saved_slot_groups_and_live_match_receipts_produce_ranked_preview_after_restart(tmp_path):
    engine,factory,repository,bracket,source=_setup_real_completed_saved(tmp_path)
    try:
        before=repository.get_branch_revision_state(branch_id=BRANCH)
        proof=_read(factory,bracket)
        assert proof.bracket==bracket
        assert tuple(x.result.match_id for x in proof.witnesses)==(
            *(group.result.match_id for group in (*source.semifinal_groups,source.final_group)),
        )
        assert tuple(x.authoritative_result_fingerprint for x in proof.witnesses)==(
            *source.match_result_fingerprints,
        )
        for witness in proof.witnesses:
            assert witness.result.rally_log is not None
            assert witness.result.rally_log.events
            assert witness.result.timeline_log is not None
        versions=prepare_calendar_engine_knockout_versions(
            proof,run_calendar=RunCalendar.fax_default(),
            expected_evidence_fingerprint=proof.fingerprint,
        )
        assert len(versions)==4
        assert {v.result.source_fingerprint for v in versions}=={proof.fingerprint}
        engine.dispose()
        from sqlalchemy import create_engine
        reopened=create_engine(f"sqlite:///{tmp_path / 'real-slots.db'}")
        reopened_factory=sessionmaker(bind=reopened)
        try:
            with reopened_factory() as s:
                s.connection().exec_driver_sql("BEGIN")
                snapshot,manifest,after=preview_saved_slot_verified_knockout_ranking(
                    s,bracket=bracket,expected_saved_head_revision_id=HEAD,
                    week=w(0,2),
                    policy=OfficialRankingPolicy(policy_id="top-four",best_n=4),
                    players=tuple(
                        CalendarRankingPlayer(
                            player_id=p,tie_break_token=p,
                            tour_entry_week=w(0,1),
                        ) for p in ("a","b","c","d")
                    ),
                )
                assert after==proof
                assert snapshot.rows[0].points==100
                assert sorted(row.points for row in snapshot.rows)==[30,30,60,100]
                assert {r.source_fingerprint for r in manifest.results}=={proof.fingerprint}
                assert preview_saved_slot_verified_knockout_ranking(
                    s,bracket=bracket,expected_saved_head_revision_id=HEAD,
                    week=w(0,2),
                    policy=OfficialRankingPolicy(policy_id="top-four",best_n=4),
                    players=tuple(
                        CalendarRankingPlayer(
                            player_id=p,tie_break_token=p,
                            tour_entry_week=w(0,1),
                        ) for p in ("a","b","c","d")
                    ),
                )[0]==snapshot
        finally:
            reopened.dispose()
        assert repository.get_branch_revision_state(branch_id=BRANCH)==before
        assert repository.verify_branch_saved_revision_hash(revision_id=HEAD)
    finally:
        engine.dispose()


def test_unsigned_or_unsaved_matched_event_never_becomes_source(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with factory.begin() as s:
            _resign_saved(s,lambda p:p["content"].pop("simulation_slot_match_state",None))
        with pytest.raises(ValueError,match="no completed match evidence"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_corrupt_saved_component_and_invalid_saved_head_rejected(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with pytest.raises(ValueError,match="stale Saved HEAD"):
            _read(factory,bracket,expected_saved_head_revision_id="old-head")
        with factory.begin() as s:
            revision=s.get(BranchSavedRevisionModel,HEAD)
            revision.content_hash="f"*64
        with pytest.raises(ValueError,match="content-hash"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_stored_group_mutation_cannot_change_saved_outcome(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with factory.begin() as s:
            row=s.get(SimulationEventGroupModel,(
                RUN,BRANCH,0,f"{EVENT}:slot:1",f"{EVENT}:sf1",
            ))
            assert row is not None
            row.result_fingerprint="f"*64
        with pytest.raises(ValueError,match="differs from the live group"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_saved_group_component_fingerprint_rejects_rehashed_revision_tamper(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with factory.begin() as s:
            def alter(p):
                p["content"]["simulation_slot_match_state"]["fingerprint"]="f"*64
            _resign_saved(s,alter)
        with pytest.raises(ValueError,match="component fingerprint"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_falsified_bracket_winners_and_completion_week_fail_closed(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        fake=bracket.model_copy(update={
            "matches":tuple(
                m.model_copy(update={
                    "winner_player_id":m.loser_player_id,
                    "loser_player_id":m.winner_player_id,
                }) if i==2 else m
                for i,m in enumerate(bracket.matches)
            ),
        })
        with pytest.raises(ValueError,match="invalid progression|contradicts"):
            _read(factory,fake)
        later=bracket.model_copy(update={
            "completed_week":w(0,2),
            "first_publication_week":w(0,3),
        })
        with pytest.raises(ValueError,match="cross-week"):
            _read(factory,later)
    finally:
        engine.dispose()


@pytest.mark.parametrize("W,offset",[(52,1),(80,37)])
def test_fax_saved_match_authority_is_not_reinterpreted_for_nonfax_run_clock(
    tmp_path,W,offset,
):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        clock=RunCalendar(W,offset,2000,50)
        with factory.begin() as s:
            run=s.get(RunContainerModel,RUN)
            run.metadata_json=json.dumps({"run_calendar":clock.to_metadata()})
            run.timeline_start_season=clock.start_year
            run.timeline_end_season=clock.start_year+clock.season_count-1
            def alter(p):
                p["run"]["run_calendar"]=clock.to_metadata()
                p["run"]["timeline_start_season"]=clock.start_year
                p["run"]["timeline_end_season"]=clock.start_year+clock.season_count-1
            _resign_saved(s,alter)
        with pytest.raises(ValueError,match="only support the FAX W61"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_forked_branch_requires_separate_ancestry_proof(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with factory.begin() as s:
            s.get(RunBranchModel,BRANCH).forked_from_branch_id="parent"
        with pytest.raises(ValueError,match="fork needs"):
            _read(factory,bracket)
    finally:
        engine.dispose()


def test_rehashed_saved_match_payload_still_rejects_invalid_group_receipt(tmp_path):
    engine,factory,_,bracket,_=_setup_real_completed_saved(tmp_path)
    try:
        with factory.begin() as s:
            def alter(p):
                p["content"]["simulation_slot_match_state"]["groups"][0]["result_fingerprint"]="f"*64
            _resign_saved(s,alter)
        with pytest.raises(ValueError,match="persisted match input/result fingerprint mismatch"):
            _read(factory,bracket)
    finally:
        engine.dispose()
