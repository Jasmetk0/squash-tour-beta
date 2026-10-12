"""F79-08: adversarial real SQLite proof of fail-closed selected append boundaries.

Use the F79-06 real saved Run/InitialWorld fixture. Only World Package lookup is
isolated as in that original fixture; all HEAD/Draft and atomic DB writes are real.
"""
import pytest
from sqlalchemy import select

from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel, InitialWorldStateModel, PlayerHealthWeekStateModel,
    PlayerLifecycleWeekStateModel, PlayerSportingWeekStateModel,
    OfficialRankingCandidateModel, PublishedOfficialRankingModel,
    AuthoritativeWorldStateModel, AuthoritativeWorldEventModel,
    AuthoritativeWeekTransitionReceiptModel, CompletedWeekSportingContextModel,
    PlayerHealthAdminEditReceiptModel, PlayerTourEntryTriggerModel,
    OfficialRankingResultVersionModel, OfficialRankingZeroVersionModel,
    TournamentRankingSnapshotAuthorityModel, OwnedTournamentRankingSourceModel,
)
from tests.api.test_selected_initial_world_append import _prepared, _install, SHA

pytestmark = pytest.mark.pr_critical
OTHER_SHA = "b" * 64


def _pristine_bytes(repo, run_id, branch_id):
    """Compare persisted bytes of ALL affected roster projections and saved history."""
    models = (InitialWorldStateModel, PlayerLifecycleWeekStateModel,
              PlayerSportingWeekStateModel, PlayerHealthWeekStateModel)
    with repo._session_factory() as db:
        rosters = {}
        for model in models:
            rows = db.scalars(
                select(model).where(model.run_id == run_id, model.branch_id == branch_id)
            ).all()
            rosters[model.__tablename__] = tuple(sorted(
                (getattr(row, "week_ordinal", -1), row.fingerprint, row.payload_json)
                for row in rows
            ))
        revisions = db.scalars(
            select(BranchSavedRevisionModel).where(
                BranchSavedRevisionModel.branch_id == branch_id
            )
        ).all()
        lineage = tuple(sorted(
            (row.revision_id, row.sequence, row.content_hash, row.payload_json)
            for row in revisions
        ))
    return rosters, lineage


@pytest.mark.parametrize("boundary", (
    "stale_saved_head", "stale_draft_version", "wrong_world_fingerprint",
    "wrong_original_fingerprint", "changed_saved_world",
))
def test_stale_revision_world_or_initial_world_cannot_partially_append(
    tmp_path, monkeypatch, boundary
):
    repo, rid, bid, original, _, _, proposed, saved = _prepared(tmp_path, monkeypatch)
    before = _pristine_bytes(repo, rid, bid)
    kwargs = dict(
        appended=proposed, expected_initial_world_fingerprint=original.fingerprint,
        expected_saved_head=saved.saved_revision.revision_id,
        expected_draft_version=saved.working_draft.draft_version,
        expected_package_fingerprint=SHA,
    )
    if boundary == "stale_saved_head":
        kwargs["expected_saved_head"] = "stale-head-from-another-snapshot"
    elif boundary == "stale_draft_version":
        kwargs["expected_draft_version"] += 1
    elif boundary == "wrong_world_fingerprint":
        kwargs["expected_package_fingerprint"] = OTHER_SHA
    elif boundary == "wrong_original_fingerprint":
        kwargs["expected_initial_world_fingerprint"] = OTHER_SHA
    else:
        import beta_engine.infrastructure.db.run_package_state as package_state
        monkeypatch.setattr(
            package_state, "get_run_package_state",
            lambda *a, **kw: type("ChangedWorld", (), {"fingerprint": OTHER_SHA})()
        )
    with pytest.raises(ValueError, match="HEAD/Draft|World Package|saved InitialWorld"):
        repo.append_selected_initial_world(**kwargs)
    assert _pristine_bytes(repo, rid, bid) == before


def _activity_row(name, run_id, branch_id, old_player_id):
    base = dict(run_id=run_id, branch_id=branch_id)
    if name == "ranking_candidate":
        return OfficialRankingCandidateModel(**base, week_ordinal=0,
                                             fingerprint=SHA, payload_json="{}")
    if name == "published_ranking":
        return PublishedOfficialRankingModel(**base, week_ordinal=0,
                                             snapshot_fingerprint=SHA, payload_json="{}")
    if name == "world_clock":
        return AuthoritativeWorldStateModel(**base, current_ordinal=0,
                                            ranking_fingerprint=SHA)
    if name == "world_event":
        return AuthoritativeWorldEventModel(**base, command_id="world-event-1",
                                            week_ordinal=0, event_kind="week_transition",
                                            payload_json="{}")
    if name == "week_transition_receipt":
        return AuthoritativeWeekTransitionReceiptModel(
            **base, command_id="week-transition-1", request_fingerprint=SHA,
            request_payload_json="{}", result_json="{}")
    if name == "completed_sporting_context":
        return CompletedWeekSportingContextModel(
            **base, week_ordinal=0, fingerprint=SHA, payload_json="{}")
    if name == "health_edit_receipt":
        return PlayerHealthAdminEditReceiptModel(
            **base, command_id="health-edit-1", week_ordinal=0,
            player_id=old_player_id, request_fingerprint=SHA,
            before_state_fingerprint=SHA, after_state_fingerprint=OTHER_SHA,
            payload_json="{}")
    if name == "tour_entry":
        return PlayerTourEntryTriggerModel(
            **base, player_id=old_player_id, trigger_week_ordinal=0,
            decision_slot_ordinal=1, fingerprint=SHA, payload_json="{}")
    if name == "ranking_result":
        return OfficialRankingResultVersionModel(
            **base, edition_id="edition-1", player_id=old_player_id,
            effective_ordinal=0, fingerprint=SHA, payload_json="{}")
    if name == "ranking_zero":
        return OfficialRankingZeroVersionModel(
            **base, zero_id="zero-1", effective_ordinal=0,
            fingerprint=SHA, payload_json="{}")
    if name == "event_ranking_binding":
        return TournamentRankingSnapshotAuthorityModel(
            **base, event_id="event-1", ranking_week_ordinal=0,
            ranking_snapshot_fingerprint=SHA, authority_fingerprint=SHA,
            adopted_by_command_id="event-rank-1", payload_json="{}")
    if name == "adopted_tournament_result":
        return OwnedTournamentRankingSourceModel(
            **base, edition_id="edition-1", event_id="event-1",
            source_fingerprint=SHA, adopted_by_command_id="result-1",
            payload_json="{}")
    raise AssertionError(name)


@pytest.mark.parametrize("activity", (
    "ranking_candidate", "published_ranking", "world_clock",
    "world_event", "week_transition_receipt",
    "completed_sporting_context", "health_edit_receipt",
    "tour_entry", "ranking_result", "ranking_zero",
    "event_ranking_binding", "adopted_tournament_result",
))
def test_historical_rank_sporting_or_edit_activity_closes_append_without_writes(
    tmp_path, monkeypatch, activity
):
    repo, rid, bid, original, _, _, proposed, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        session.add(_activity_row(activity, rid, bid, original.players[0].player_id))
    before = _pristine_bytes(repo, rid, bid)
    with pytest.raises(ValueError, match="ranking or sporting|historical player"):
        _install(repo, rid, bid, original, proposed, saved)
    assert _pristine_bytes(repo, rid, bid) == before
    assert repo.get_initial_world(run_id=rid, branch_id=bid) == original


@pytest.mark.parametrize("later_table", (
    PlayerLifecycleWeekStateModel, PlayerSportingWeekStateModel,
    PlayerHealthWeekStateModel,
))
def test_later_week_projection_blocks_append_without_overwriting_history(
    tmp_path, monkeypatch, later_table
):
    repo, rid, bid, original, _, _, proposed, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        session.add(later_table(
            run_id=rid, branch_id=bid, week_ordinal=1,
            fingerprint=SHA, payload_json="{}"
        ))
    before = _pristine_bytes(repo, rid, bid)
    with pytest.raises(ValueError, match="later-week"):
        _install(repo, rid, bid, original, proposed, saved)
    assert _pristine_bytes(repo, rid, bid) == before


@pytest.mark.parametrize("status", ("read_only_run", "read_only_branch", "closed_branch"))
def test_append_denied_when_run_or_branch_is_not_writable(
    tmp_path, monkeypatch, status
):
    from beta_engine.infrastructure.db.models import RunContainerModel, RunBranchModel
    repo, rid, bid, original, _, _, proposed, saved = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        run = session.get(RunContainerModel, rid)
        branch = session.get(RunBranchModel, bid)
        if status == "read_only_run":
            run.read_only = 1
        elif status == "read_only_branch":
            branch.read_only = 1
        else:
            branch.status = "archived"
    before = _pristine_bytes(repo, rid, bid)
    with pytest.raises(ValueError, match="writable custom Run/Branch"):
        _install(repo, rid, bid, original, proposed, saved)
    assert _pristine_bytes(repo, rid, bid) == before
