"""Real HTTP and SQLite coverage of the Saved Draw's first-Entry evidence."""

import itertools
from urllib.parse import urlencode

import pytest

from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.domain.tournaments.definitive_wild_card_assignment import (
    DefinitiveWildCardAssignmentAuthority,
)
from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    record_definitive_wild_card_assignment,
)
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from beta_engine.infrastructure.db.tournament_application_submissions import (
    record_valid_application_submission,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.infrastructure import test_fax_reference_player_draw as fax


@pytest.mark.pr_critical
def test_entry_evidence_reads_one_saved_owner_without_inventing_first_entry(
    tmp_path, tmp_path_factory
):
    database_url = f"sqlite:///{tmp_path / 'saved-entry-evidence.db'}"
    calendar, document = fax.fax_source.__wrapped__(tmp_path_factory)
    event = next(e for e in calendar.events if e.main_draw_size == 24)
    ids = itertools.count()

    def endpoint(server, revision_id):
        query = urlencode(
            {
                "season": "2000/2001",
                "expected_saved_revision_id": revision_id,
            }
        )
        return (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event.event_id}/draw/saved-entry-evidence?{query}"
        )

    def save(repo, *, viewer_branch_id=None):
        service = RunWorkingDraftService(
            repository=repo,
            id_factory=lambda kind: f"entry-evidence-{kind}-{next(ids)}",
        )
        draft = service.get_viewer_branch_draft(run_id=run_id, branch_id=branch_id)
        if viewer_branch_id is not None:
            # The repository evidence writers are not a standalone Save command.
            # Stage a real fixture change so the normal full Save captures them.
            draft = service.stage_viewer_branch(
                run_id=run_id,
                branch_id=branch_id,
                viewer_branch_id=viewer_branch_id,
                expected_draft_version=draft.draft_version,
            )
        service.save(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=draft.draft_version,
        )
        return repo.get_branch_revision_state(
            branch_id=branch_id
        ).saved_head_revision_id

    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, initial = _create_run(
            server, display_name="Saved Entry Evidence"
        )
        status, sibling = _request(
            "POST",
            f"{server.base_url}/run-containers/{run_id}/branches",
            {"source_branch_id": branch_id, "source_saved_revision_id": initial},
        )
        assert status == 201, sibling
        repo = server.app.state.runtime.repository
        owner = {"run_id": run_id, "branch_id": branch_id}
        scope = {**owner, "event_id": event.event_id}
        ranking = fax.ranking_snapshot(fax.PLAYERS).model_copy(update=owner)
        applications = tuple(
            a.model_copy(update=owner) for a in fax.applications(event)
        )
        with repo._session_factory.begin() as session:
            put_run_package_state(
                session, fax.copied_state(document).model_copy(update=owner)
            )
            session.add(
                PublishedOfficialRankingModel(
                    **owner,
                    week_ordinal=ranking.week.ordinal,
                    snapshot_fingerprint=ranking.fingerprint,
                    payload_json=ranking.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                **scope,
                ranking_week=ranking.week,
                command_id="ranking",
            )
            TournamentEntryFieldStore(session).stage_initial(
                **scope,
                applications=applications,
                capacity=fax.fax_reference_entry_capacity(event),
                command_id="field",
            )
            wild_card = TournamentWildCardAuthorityStore(session).resolve(
                **scope,
                command_id="wc",
                original_wild_card_player_ids=fax.PLAYERS[-2:],
                decision_week=ranking.week,
                decision_slot_ordinal=1,
            )
            draw_input = TournamentDrawInputAuthorityStore(session).commit(
                **scope,
                command_id="input",
                draw_seed=17,
            )
            TournamentDrawAuthorityStore(session).generate(**scope, command_id="draw")
        assert _request("GET", endpoint(server, initial))[0] == 409
        draw_head = save(repo)
        status, before = _request("GET", endpoint(server, draw_head))
        assert status == 200, before
        assert len(before["entrants"]) == 36
        assert all(row["first_entry"] is None for row in before["entrants"])

        direct = draw_input.direct_main_player_ids[0]
        qualifier = draw_input.qualification_player_ids[0]
        missing_wc = wild_card.slots[1].active_player_id
        wc = DefinitiveWildCardAssignmentAuthority.from_resolution(
            authority=wild_card,
            wildcard_index=wild_card.slots[0].wildcard_index,
            assignment_week=ranking.week,
            decision_slot_ordinal=1,
            provenance="Test definitive WC recorded by the existing writer",
        )
        with repo._session_factory.begin() as session:
            source = next(a for a in applications if a.player_id == direct)
            app = TournamentApplicationSubmissionAuthority(
                **scope,
                player_id=direct,
                application_id=source.application_id,
                entry_window=source.entry_window,
                submission_week=ranking.week,
                decision_slot_ordinal=source.decision_slot_ordinal,
                nr_tie_break_token=source.nr_tie_break_token,
                validation_authority_id="reviewed-entry",
                validation_authority_fingerprint="a" * 64,
                provenance="Test valid application recorded by the existing writer",
            )
            record_valid_application_submission(session, app)
            record_definitive_wild_card_assignment(session, wc)
        assert _request("GET", endpoint(server, draw_head)) == (200, before)

        evidence_head = save(repo, viewer_branch_id=sibling["branch_id"])
        assert evidence_head != draw_head
        assert _request("GET", endpoint(server, draw_head))[0] == 409
        status, after = _request("GET", endpoint(server, evidence_head))
        assert status == 200, after
        assert after["saved_revision_id"] == evidence_head
        actual = {row["player_id"]: row for row in after["entrants"]}
        assert actual[direct] == {
            "player_id": direct,
            "draw_role": "direct_main",
            "first_entry": app.to_tour_entry_trigger().model_dump(mode="json"),
        }
        assert actual[wc.player_id] == {
            "player_id": wc.player_id,
            "draw_role": "wild_card",
            "first_entry": wc.to_tour_entry_trigger().model_dump(mode="json"),
        }
        assert actual[qualifier]["first_entry"] is None
        assert actual[missing_wc]["first_entry"] is None
        assert sum(row["first_entry"] is not None for row in actual.values()) == 2

    with ApiServer(database_url=database_url) as restarted:
        assert _request("GET", endpoint(restarted, evidence_head)) == (200, after)
        repo = restarted.app.state.runtime.repository
        # A well-formed trigger with no real submission must never become evidence.
        with repo._session_factory.begin() as session:
            PlayerTourEntryTriggerStore(session).append(
                PlayerTourEntryTrigger(
                    **scope,
                    player_id=qualifier,
                    trigger_kind="valid_tournament_application",
                    trigger_week=ranking.week,
                    decision_slot_ordinal=10,
                    source_evidence_id="absent-application",
                    source_evidence_fingerprint="b" * 64,
                    provenance="Broken evidence fixture",
                )
            )
        damaged = save(repo, viewer_branch_id=branch_id)
        status, rejected = _request("GET", endpoint(restarted, damaged))
        assert status == 409, rejected
        assert "differs from its valid application" in rejected["detail"]["message"]
