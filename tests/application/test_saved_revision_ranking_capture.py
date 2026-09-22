"""Production Save embeds the complete ranking preparation atomically."""

import json

import pytest
from sqlalchemy import event
from test_saved_revision_restore import _repository, _run_with_saved_viewer_change, _id_factory
from test_saved_revision_ranking_guard import dump

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.domain.rankings.official import (
    DisciplinaryZero,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
)
from beta_engine.infrastructure.db import WorkingDraftConflictError, SavedRevisionBranchForkConflictError, SavedRevisionHistoryConflictError
from beta_engine.infrastructure.db.models import BranchRevisionAuditEventModel, BranchSavedRevisionModel, OfficialRankingCandidateModel
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.zero_history import RankingZeroVersion
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
    load_saved_run_entry_decision_slots,
)
from beta_engine.infrastructure.db.application_validation_slots import (
    ApplicationValidationSlotStore,
    load_saved_application_validation_slots,
    record_resolved_application_validation_slot,
)


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "saved-ranking.db"
    repo = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repo)
    runner = RankingWeekCommandRunner(repo._session_factory)
    command = RankingBootstrapCommand(command_id="bootstrap", run_id="run-one", branch_id="branch-one",
                                      policy=OfficialRankingPolicy(policy_id="policy"), players=(), discipline="none")
    runner.execute(command)
    service = RunWorkingDraftService(repository=repo, id_factory=_id_factory("revision-three", "audit-two"))
    staged = service.stage_viewer_branch(run_id="run-one", branch_id="branch-one", viewer_branch_id="branch-one", expected_draft_version=2)
    return path, repo, runner, command, service, staged.draft_version


def save(prepared):
    _, _, _, _, service, version = prepared
    return service.save(run_id="run-one", branch_id="branch-one", expected_draft_version=version)


@pytest.mark.smoke
def test_save_captures_frozen_inputs_and_refreshes_without_mutating_history(prepared):
    path, repo, runner, command, _, _ = prepared
    result = save(prepared)
    saved = load_saved_ranking_component(result.saved_revision.payload, run_id="run-one", branch_id="branch-one")
    assert len(saved.entries) == 1
    assert saved.entries[0].receipts[0].command_id == "bootstrap"
    assert repo.verify_branch_saved_revision_hash(revision_id="revision-three")
    before_payload = result.saved_revision.payload
    runner.execute(RankingWeekCommand(command_id="week-2", tournaments=(), context=RankingTransitionContext(
        run_id="run-one", branch_id="branch-one", completed_week=RankingWeek(season_index=0, week=1),
        target_week=RankingWeek(season_index=0, week=2), policy=command.policy, players=(), discipline="none",
    )))
    service = RunWorkingDraftService(repository=repo, id_factory=_id_factory("revision-four", "audit-three"))
    staged = service.stage_viewer_branch(run_id="run-one", branch_id="branch-one", viewer_branch_id="branch-two", expected_draft_version=4)
    latest = service.save(run_id="run-one", branch_id="branch-one", expected_draft_version=staged.draft_version)
    assert len(load_saved_ranking_component(latest.saved_revision.payload, run_id="run-one", branch_id="branch-one").entries) == 2
    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_saved_revision(revision_id="revision-three").payload == before_payload
    assert reloaded.get_branch_saved_revision(revision_id="revision-one").payload["content"] == {}


@pytest.mark.smoke
def test_failed_save_rolls_back_revision_draft_viewer_and_audit(prepared):
    path, repo, *_ = prepared
    before = dump(path)
    def fail(*args):
        raise RuntimeError("audit failure")
    event.listen(BranchRevisionAuditEventModel, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="audit failure"):
            save(prepared)
    finally:
        event.remove(BranchRevisionAuditEventModel, "before_insert", fail)
    assert dump(path) == before


def test_malformed_live_ranking_blocks_save_without_changes(prepared):
    path, repo, *_ = prepared
    with repo._session_factory.begin() as session:
        session.get(OfficialRankingCandidateModel, ("run-one", "branch-one", 0)).payload_json = "broken"
    before = dump(path)
    with pytest.raises(WorkingDraftConflictError, match="ranking"):
        save(prepared)
    assert dump(path) == before


@pytest.mark.pr_critical
def test_bootstrap_ranking_revision_forks_with_target_branch_identity_and_can_diverge(prepared):
    path, repo, _, command, *_ = prepared
    source_saved = save(prepared)
    source_ranking = load_saved_ranking_component(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_ranking is not None
    assert len(source_ranking.entries) == 1

    created = RunBranchCreationService(
        repository=repo,
        id_factory=_id_factory(
            "branch-three",
            "draft-three",
            "revision-fork-root",
        ),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-three",
        display_name="Ranking Fork",
    )

    assert created.branch_id == "branch-three"
    assert created.forked_from_branch_id == "branch-one"
    assert created.forked_from_saved_revision_id == "revision-three"
    assert created.saved_head_revision_id == "revision-fork-root"

    fork_root = repo.get_branch_saved_revision(revision_id="revision-fork-root")
    assert fork_root is not None
    assert fork_root.branch_id == "branch-three"
    assert fork_root.parent_revision_id == "revision-three"
    assert fork_root.sequence == source_saved.saved_revision.sequence + 1
    assert fork_root.kind == "branch_fork_materialized"
    assert repo.verify_branch_saved_revision_hash(revision_id="revision-fork-root")

    target_ranking = load_saved_ranking_component(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-three",
    )
    assert target_ranking is not None
    assert target_ranking.branch_id == "branch-three"
    assert target_ranking.fingerprint != source_ranking.fingerprint
    assert target_ranking.entries[0].snapshot.branch_id == "branch-three"
    assert (
        target_ranking.entries[0].receipts[0].request_fingerprint
        != source_ranking.entries[0].receipts[0].request_fingerprint
    )

    target_live = repo.get_branch_revision_state(branch_id="branch-three")
    assert target_live.saved_head_revision_id == "revision-fork-root"
    assert target_live.working_draft.base_revision_id == "revision-fork-root"

    target_runner = RankingWeekCommandRunner(repo._session_factory)
    target_runner.execute(
        RankingWeekCommand(
            command_id="branch-three-week-2",
            tournaments=(),
            context=RankingTransitionContext(
                run_id="run-one",
                branch_id="branch-three",
                completed_week=RankingWeek(season_index=0, week=1),
                target_week=RankingWeek(season_index=0, week=2),
                policy=command.policy,
                players=(),
                discipline="none",
            ),
        )
    )
    preview = repo.preview_ranking_save(run_id="run-one", branch_id="branch-three")
    assert preview["can_save"] is True
    target_save = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory("revision-branch-three-week-two", "audit-branch-three"),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-three",
        expected_draft_version=0,
        expected_ranking_fingerprint=preview["ranking_fingerprint"],
    )
    target_after = load_saved_ranking_component(
        target_save.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-three",
    )
    assert target_after is not None
    assert len(target_after.entries) == 2

    source_after = load_saved_ranking_component(
        repo.get_branch_saved_revision(revision_id="revision-three").payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_after is not None
    assert len(source_after.entries) == 1

    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_revision_state(
        branch_id="branch-three"
    ).saved_head_revision_id == "revision-branch-three-week-two"


@pytest.mark.pr_critical
def test_ranking_fork_remaps_resolved_all_invalid_entry_slot_identity(prepared):
    _, repo, *_ = prepared
    week = RankingWeek(season_index=0, week=1)
    source_slot = RunEntryDecisionSlotAuthority(
        run_id="run-one",
        branch_id="branch-one",
        week=week,
        decision_slot_ordinal=1,
        source_entry_batch_fingerprint="a" * 64,
        source_application_decisions_fingerprint="b" * 64,
        source_active_players_fingerprint="c" * 64,
        decisions=(
            EntryDecisionEvidence(
                event_id="entry-event",
                player_id="prospect-entry",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
        ),
    )
    validation = TournamentApplicationValidationAuthority(
        validation_id="validation-entry",
        application_id="application-entry",
        run_id="run-one",
        branch_id="branch-one",
        week=week,
        decision_slot_ordinal=1,
        source_slot_fingerprint=source_slot.fingerprint,
        event_id="entry-event",
        player_id="prospect-entry",
        entry_window="main",
        source_decision_fingerprint="d" * 64,
        outcome="invalid",
        nr_tie_break_token=None,
        validation_policy_id="fork-entry-policy.v1",
        validation_policy_fingerprint="e" * 64,
        reasons=("ineligible_under_resolved_policy",),
        provenance="materialized fork Entry validation regression",
    )
    source_resolved = ResolvedApplicationValidationSlot(
        slot=source_slot,
        validations=(validation,),
    )
    with repo._session_factory.begin() as session:
        RunEntryDecisionSlotStore(session).append(source_slot)
        committed = record_resolved_application_validation_slot(
            session,
            source_resolved,
        )
        assert committed.submission_commit is None

    source_saved = save(prepared)
    source_slots = load_saved_run_entry_decision_slots(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    source_validations = load_saved_application_validation_slots(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_slots == (source_slot,)
    assert source_validations == (source_resolved,)

    created = RunBranchCreationService(
        repository=repo,
        id_factory=_id_factory(
            "branch-entry-fork",
            "draft-entry-fork",
            "revision-entry-fork",
        ),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-three",
        display_name="Entry Validation Fork",
    )
    assert created.saved_head_revision_id == "revision-entry-fork"

    fork_root = repo.get_branch_saved_revision(revision_id="revision-entry-fork")
    assert fork_root is not None
    target_slots = load_saved_run_entry_decision_slots(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-entry-fork",
    )
    target_validations = load_saved_application_validation_slots(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-entry-fork",
    )
    assert target_slots is not None and len(target_slots) == 1
    assert target_validations is not None and len(target_validations) == 1
    target_slot = target_slots[0]
    target_resolved = target_validations[0]
    assert target_slot.branch_id == "branch-entry-fork"
    assert target_slot.fingerprint != source_slot.fingerprint
    assert target_resolved.slot == target_slot
    assert target_resolved.fingerprint != source_resolved.fingerprint
    assert target_resolved.validations[0].branch_id == "branch-entry-fork"
    assert target_resolved.validations[0].source_slot_fingerprint == (
        target_slot.fingerprint
    )
    assert repo.verify_branch_saved_revision_hash(
        revision_id="revision-entry-fork"
    )

    with repo._session_factory() as session:
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run-one",
            branch_id="branch-entry-fork",
        ) == (target_slot,)
        assert ApplicationValidationSlotStore(session).list(
            run_id="run-one",
            branch_id="branch-entry-fork",
        ) == (target_resolved,)


@pytest.mark.pr_critical
def test_source_free_multiweek_ranking_fork_rebuilds_full_lineage_and_diverges(prepared):
    path, repo, runner, command, *_ = prepared
    save(prepared)
    for week_number in (2, 3):
        runner.execute(
            RankingWeekCommand(
                command_id=f"source-week-{week_number}",
                tournaments=(),
                context=RankingTransitionContext(
                    run_id="run-one",
                    branch_id="branch-one",
                    completed_week=RankingWeek(
                        season_index=0,
                        week=week_number - 1,
                    ),
                    target_week=RankingWeek(
                        season_index=0,
                        week=week_number,
                    ),
                    policy=command.policy,
                    players=(),
                    discipline="none",
                ),
            )
        )
    preview = repo.preview_ranking_save(run_id="run-one", branch_id="branch-one")
    source_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory("revision-four", "audit-three"),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=4,
        expected_ranking_fingerprint=preview["ranking_fingerprint"],
    )
    source_state = load_saved_ranking_component(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_state is not None
    assert len(source_state.entries) == 3

    created = RunBranchCreationService(
        repository=repo,
        id_factory=_id_factory(
            "branch-four",
            "draft-four",
            "revision-fork-four",
        ),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-four",
        display_name="Multiweek Ranking Fork",
    )
    assert created.saved_head_revision_id == "revision-fork-four"

    fork_root = repo.get_branch_saved_revision(revision_id="revision-fork-four")
    assert fork_root is not None
    target_state = load_saved_ranking_component(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-four",
    )
    assert target_state is not None
    assert len(target_state.entries) == 3
    assert [entry.snapshot.week.week for entry in target_state.entries] == [1, 2, 3]
    assert all(
        entry.snapshot.branch_id == "branch-four"
        for entry in target_state.entries
    )
    assert all(
        target_entry.snapshot.fingerprint != source_entry.snapshot.fingerprint
        for target_entry, source_entry in zip(
            target_state.entries,
            source_state.entries,
            strict=True,
        )
    )
    assert all(
        target_entry.receipts[0].request_fingerprint
        != source_entry.receipts[0].request_fingerprint
        for target_entry, source_entry in zip(
            target_state.entries,
            source_state.entries,
            strict=True,
        )
    )
    assert target_state.entries[1].snapshot.previous_fingerprint == (
        target_state.entries[0].snapshot.fingerprint
    )
    assert target_state.entries[2].snapshot.previous_fingerprint == (
        target_state.entries[1].snapshot.fingerprint
    )

    target_runner = RankingWeekCommandRunner(repo._session_factory)
    target_runner.execute(
        RankingWeekCommand(
            command_id="branch-four-week-4",
            tournaments=(),
            context=RankingTransitionContext(
                run_id="run-one",
                branch_id="branch-four",
                completed_week=RankingWeek(season_index=0, week=3),
                target_week=RankingWeek(season_index=0, week=4),
                policy=command.policy,
                players=(),
                discipline="none",
            ),
        )
    )
    target_preview = repo.preview_ranking_save(
        run_id="run-one",
        branch_id="branch-four",
    )
    target_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory(
            "revision-branch-four-week-four",
            "audit-branch-four",
        ),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-four",
        expected_draft_version=0,
        expected_ranking_fingerprint=target_preview["ranking_fingerprint"],
    )
    target_after = load_saved_ranking_component(
        target_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-four",
    )
    assert target_after is not None
    assert len(target_after.entries) == 4

    source_after = load_saved_ranking_component(
        repo.get_branch_saved_revision(revision_id="revision-four").payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_after is not None
    assert len(source_after.entries) == 3

    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_revision_state(
        branch_id="branch-four"
    ).saved_head_revision_id == "revision-branch-four-week-four"


@pytest.mark.pr_critical
def test_zero_bearing_ranking_fork_remaps_zero_chain_and_can_diverge(tmp_path):
    path = tmp_path / "saved-ranking-zero-fork.db"
    repo = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repo)

    week_one = RankingWeek(season_index=0, week=1)
    week_two = RankingWeek(season_index=0, week=2)
    player = OfficialRankingPlayer(
        player_id="player-a",
        tie_break_token="token-a",
        tour_entry_week=week_one,
    )
    source_zero = RankingZeroVersion(
        effective_week=week_one,
        previous_fingerprint=None,
        zero=DisciplinaryZero(
            zero_id="zero-a",
            run_id="run-one",
            branch_id="branch-one",
            player_id="player-a",
            source_fingerprint="decision-one",
            effective_week=week_one,
            duration_weeks=3,
        ),
    )

    runner = RankingWeekCommandRunner(repo._session_factory)
    runner.execute(
        RankingBootstrapCommand(
            command_id="bootstrap-zero",
            run_id="run-one",
            branch_id="branch-one",
            policy=OfficialRankingPolicy(policy_id="policy"),
            players=(player,),
            discipline="stored_zeros",
            zero_versions=(source_zero,),
        )
    )

    source_preview = repo.preview_ranking_save(
        run_id="run-one",
        branch_id="branch-one",
    )
    source_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory("revision-zero-source", "audit-zero-source"),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=source_preview["draft_version"],
        expected_ranking_fingerprint=source_preview["ranking_fingerprint"],
    )

    source_state = load_saved_ranking_component(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_state is not None
    assert len(source_state.zero_sources) == 1

    created = RunBranchCreationService(
        repository=repo,
        id_factory=_id_factory(
            "branch-zero",
            "draft-zero",
            "revision-zero-fork-root",
        ),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id=source_saved.saved_revision.revision_id,
        display_name="Zero Ranking Fork",
    )
    assert created.saved_head_revision_id == "revision-zero-fork-root"

    fork_root = repo.get_branch_saved_revision(
        revision_id="revision-zero-fork-root"
    )
    assert fork_root is not None
    target_state = load_saved_ranking_component(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-zero",
    )
    assert target_state is not None
    assert len(target_state.zero_sources) == 1
    target_zero = target_state.zero_sources[0]
    assert target_zero.zero.branch_id == "branch-zero"
    assert target_zero.fingerprint != source_zero.fingerprint
    assert target_state.entries[0].inputs.zeros_from_history is True
    assert (
        target_state.entries[0].inputs.disciplinary_zeros[0].branch_id
        == "branch-zero"
    )

    target_zero_correction = RankingZeroVersion(
        effective_week=week_two,
        previous_fingerprint=target_zero.fingerprint,
        zero=target_zero.zero.model_copy(
            update={
                "source_fingerprint": "decision-two",
                "duration_weeks": 1,
            }
        ),
    )
    target_runner = RankingWeekCommandRunner(repo._session_factory)
    target_runner.execute(
        RankingWeekCommand(
            command_id="target-zero-week-two",
            tournaments=(),
            zero_versions=(target_zero_correction,),
            context=RankingTransitionContext(
                run_id="run-one",
                branch_id="branch-zero",
                completed_week=week_one,
                target_week=week_two,
                policy=OfficialRankingPolicy(policy_id="policy"),
                players=(player,),
                discipline="stored_zeros",
            ),
        )
    )
    target_preview = repo.preview_ranking_save(
        run_id="run-one",
        branch_id="branch-zero",
    )
    target_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory(
            "revision-zero-target-week-two",
            "audit-zero-target",
        ),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-zero",
        expected_draft_version=target_preview["draft_version"],
        expected_ranking_fingerprint=target_preview["ranking_fingerprint"],
    )
    target_after = load_saved_ranking_component(
        target_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-zero",
    )
    assert target_after is not None
    assert len(target_after.zero_sources) == 2

    source_after = load_saved_ranking_component(
        repo.get_branch_saved_revision(
            revision_id=source_saved.saved_revision.revision_id
        ).payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_after is not None
    assert len(source_after.zero_sources) == 1

    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_revision_state(
        branch_id="branch-zero"
    ).saved_head_revision_id == "revision-zero-target-week-two"


@pytest.mark.pr_critical
def test_result_history_ranking_fork_remaps_correction_chain_and_can_diverge(tmp_path):
    path = tmp_path / "saved-ranking-result-fork.db"
    repo = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repo)

    week_one = RankingWeek(season_index=0, week=1)
    week_two = RankingWeek(season_index=0, week=2)
    week_three = RankingWeek(season_index=0, week=3)
    player = OfficialRankingPlayer(
        player_id="player-a",
        tie_break_token="token-a",
        tour_entry_week=week_one,
    )

    runner = RankingWeekCommandRunner(repo._session_factory)
    runner.execute(
        RankingBootstrapCommand(
            command_id="bootstrap-result",
            run_id="run-one",
            branch_id="branch-one",
            policy=OfficialRankingPolicy(policy_id="policy"),
            players=(player,),
            discipline="none",
        )
    )

    source_result = RankingResultVersion(
        run_id="run-one",
        branch_id="branch-one",
        effective_week=week_two,
        previous_fingerprint=None,
        result=OfficialRankingResult(
            edition_id="edition-a",
            player_id="player-a",
            source_fingerprint="immutable-award-evidence",
            completed_week=week_one,
            first_publication_week=week_two,
            validity_weeks=61,
            main_points=100,
        ),
    )
    with repo._session_factory.begin() as session:
        OfficialRankingResultStore(session).append(source_result)

    runner.execute(
        RankingWeekCommand(
            command_id="source-result-week-two",
            tournaments=(),
            context=RankingTransitionContext(
                run_id="run-one",
                branch_id="branch-one",
                completed_week=week_one,
                target_week=week_two,
                policy=OfficialRankingPolicy(policy_id="policy"),
                players=(player,),
                discipline="none",
            ),
        )
    )
    source_preview = repo.preview_ranking_save(
        run_id="run-one",
        branch_id="branch-one",
    )
    source_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory("revision-result-source", "audit-result-source"),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=source_preview["draft_version"],
        expected_ranking_fingerprint=source_preview["ranking_fingerprint"],
    )

    source_state = load_saved_ranking_component(
        source_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_state is not None
    assert len(source_state.sources) == 1
    assert source_state.entries[-1].inputs.results[0].main_points == 100

    created = RunBranchCreationService(
        repository=repo,
        id_factory=_id_factory(
            "branch-result",
            "draft-result",
            "revision-result-fork-root",
        ),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id=source_saved.saved_revision.revision_id,
        display_name="Result Ranking Fork",
    )
    assert created.saved_head_revision_id == "revision-result-fork-root"

    fork_root = repo.get_branch_saved_revision(
        revision_id="revision-result-fork-root"
    )
    assert fork_root is not None
    target_state = load_saved_ranking_component(
        fork_root.payload,
        run_id="run-one",
        branch_id="branch-result",
    )
    assert target_state is not None
    assert len(target_state.sources) == 1
    target_result = target_state.sources[0]
    assert target_result.branch_id == "branch-result"
    assert target_result.fingerprint != source_result.fingerprint
    assert target_result.result == source_result.result
    assert target_state.entries[-1].inputs.results == (target_result.result,)

    target_correction = RankingResultVersion(
        run_id="run-one",
        branch_id="branch-result",
        effective_week=week_three,
        previous_fingerprint=target_result.fingerprint,
        result=target_result.result.model_copy(
            update={
                "main_points": 150,
                "source_fingerprint": "target-correction-evidence",
            }
        ),
    )
    target_runner = RankingWeekCommandRunner(repo._session_factory)
    target_runner.execute(
        RankingWeekCommand(
            command_id="target-result-week-three",
            tournaments=(),
            corrections=(target_correction,),
            context=RankingTransitionContext(
                run_id="run-one",
                branch_id="branch-result",
                completed_week=week_two,
                target_week=week_three,
                policy=OfficialRankingPolicy(policy_id="policy"),
                players=(player,),
                discipline="none",
            ),
        )
    )

    target_preview = repo.preview_ranking_save(
        run_id="run-one",
        branch_id="branch-result",
    )
    target_saved = RunWorkingDraftService(
        repository=repo,
        id_factory=_id_factory(
            "revision-result-target-week-three",
            "audit-result-target",
        ),
    ).save_ranking(
        run_id="run-one",
        branch_id="branch-result",
        expected_draft_version=target_preview["draft_version"],
        expected_ranking_fingerprint=target_preview["ranking_fingerprint"],
    )
    target_after = load_saved_ranking_component(
        target_saved.saved_revision.payload,
        run_id="run-one",
        branch_id="branch-result",
    )
    assert target_after is not None
    assert len(target_after.sources) == 2
    assert target_after.sources[-1].previous_fingerprint == target_result.fingerprint
    assert target_after.entries[-1].inputs.results[0].main_points == 150

    source_after = load_saved_ranking_component(
        repo.get_branch_saved_revision(
            revision_id=source_saved.saved_revision.revision_id
        ).payload,
        run_id="run-one",
        branch_id="branch-one",
    )
    assert source_after is not None
    assert len(source_after.sources) == 1
    assert source_after.entries[-1].inputs.results[0].main_points == 100

    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_revision_state(
        branch_id="branch-result"
    ).saved_head_revision_id == "revision-result-target-week-three"


@pytest.mark.parametrize("damage", ["hash", "scope", "shape"])
def test_history_rejects_invalid_embedded_ranking(prepared, damage):
    _, repo, *_ = prepared
    save(prepared)
    with repo._session_factory.begin() as session:
        model = session.get(BranchSavedRevisionModel, "revision-three")
        payload = json.loads(model.payload_json)
        component = payload["content"]["ranking_preparation"]
        if damage == "hash":
            component["fingerprint"] = "0" * 64
        elif damage == "scope":
            component["state"]["branch_id"] = "branch-two"
        else:
            component["extra"] = True
        model.payload_json = json.dumps(payload)
    with pytest.raises(SavedRevisionHistoryConflictError, match="ranking content"):
        repo.get_branch_saved_revision_history(run_id="run-one", branch_id="branch-one")
