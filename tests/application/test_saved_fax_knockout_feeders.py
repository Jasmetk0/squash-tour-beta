"""Real owner Save, SQLite reopen and frozen-source isolation for feeder plans."""

import itertools
import json

import pytest
from sqlalchemy import select

from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.saved_fax_knockout_feeders import (
    SavedFaxKnockoutFeederService,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    PublishedOfficialRankingModel,
    TournamentDrawAuthorityModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
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
from tests.api.test_saved_revision_history_api import ApiServer, _create_run
from tests.application.test_run_working_draft_save import _repository
from tests.infrastructure import test_fax_reference_player_draw as fax_inputs

pytestmark = [pytest.mark.smoke, pytest.mark.pr_critical]


@pytest.fixture(scope="module")
def fax_source(tmp_path_factory):
    return fax_inputs.fax_source.__wrapped__(tmp_path_factory)


@pytest.mark.parametrize("main_size", [24, 32])
def test_preparation_requires_manual_save_and_reopens_exact_frozen_source(
    tmp_path, fax_source, main_size
):
    path = tmp_path / "source-saved.db"
    url = f"sqlite:///{path}"
    server = ApiServer(database_url=url)
    event = next(e for e in fax_source[0].events if e.main_draw_size == main_size)
    with server:
        run_id, branch_id, initial_revision = _create_run(
            server, display_name="Saved feeder source"
        )
        repo = server.app.state.runtime.repository
        scope = {"run_id": run_id, "branch_id": branch_id, "event_id": event.event_id}
        ranking = fax_inputs.ranking_snapshot(fax_inputs.PLAYERS).model_copy(
            update={"run_id": run_id, "branch_id": branch_id}
        )
        packages = fax_inputs.copied_state(fax_source[1]).model_copy(
            update={"run_id": run_id, "branch_id": branch_id}
        )
        with repo._session_factory.begin() as session:
            put_run_package_state(session, packages)
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=ranking.week.ordinal,
                    snapshot_fingerprint=ranking.fingerprint,
                    payload_json=ranking.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                **scope, ranking_week=ranking.week, command_id="ranking"
            )
            TournamentEntryFieldStore(session).stage_initial(
                **scope,
                applications=tuple(
                    a.model_copy(update={"run_id": run_id, "branch_id": branch_id})
                    for a in fax_inputs.applications(event)
                ),
                capacity=fax_inputs.fax_reference_entry_capacity(event),
                command_id="field",
            )
            TournamentWildCardAuthorityStore(session).resolve(
                **scope,
                command_id="wc",
                original_wild_card_player_ids=fax_inputs.PLAYERS[-2:],
            )
            TournamentDrawInputAuthorityStore(session).commit(
                **scope, command_id="input", draw_seed=17
            )
            TournamentDrawAuthorityStore(session).generate(**scope, command_id="draw")
        service = SavedFaxKnockoutFeederService(repo)
        with pytest.raises(ValueError, match="Save the copied"):
            service.prepare(
                **scope, season="2000/2001", expected_saved_revision_id=initial_revision
            )
        ids = itertools.count()
        owner_save = RunWorkingDraftService(
            repository=repo, id_factory=lambda kind: f"feeder-{kind}-{next(ids)}"
        )
        draft = owner_save.get_viewer_branch_draft(run_id=run_id, branch_id=branch_id)
        owner_save.save(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=draft.draft_version,
        )
        saved_state = repo.get_branch_revision_state(branch_id=branch_id)
        saved_id = saved_state.saved_head_revision_id
        assert saved_id != initial_revision
        kwargs = dict(scope, season="2000/2001", expected_saved_revision_id=saved_id)
        plan = service.prepare(**kwargs)
        assert plan.source_saved_revision_id == saved_id
        assert plan.source_saved_content_hash == saved_state.saved_revision.content_hash
        assert len(plan.topology.plans) == (35 if main_size == 24 else 51)
        with pytest.raises(ValueError, match="source changed"):
            service.prepare(**dict(kwargs, expected_saved_revision_id=initial_revision))
        with pytest.raises(ValueError, match="source changed"):
            service.prepare(**dict(kwargs, run_id="another-run"))
        # Mutate only live rows, including a now-corrupt Draw; Saved is authoritative.
        entity = next(
            e for e in packages.entities if e.source_entity_id == event.event_id
        )
        changed = entity.model_copy(
            update={"payload": dict(entity.payload, event_name="later live edit")}
        )
        edited = packages.model_copy(
            update={
                "entities": tuple(
                    changed if e.source_entity_id == event.event_id else e
                    for e in packages.entities
                )
            }
        )
        with repo._session_factory.begin() as session:
            put_run_package_state(session, edited)
        draft = owner_save.get_viewer_branch_draft(run_id=run_id, branch_id=branch_id)
        owner_save.save(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=draft.draft_version,
        )
        assert (
            repo.get_branch_revision_state(branch_id=branch_id).saved_head_revision_id
            != saved_id
        )
        with pytest.raises(ValueError, match="source changed"):
            service.prepare(**kwargs)
        assert service.reload(plan) == plan
        with pytest.raises(ValueError, match="differs from authenticated Saved"):
            service.reload(
                plan.model_copy(update={"source_saved_content_hash": "9" * 64})
            )
        with pytest.raises(ValueError, match="not reachable"):
            service.reload(
                plan.model_copy(
                    update={"source_saved_revision_id": "unreachable-revision"}
                )
            )
        with repo._session_factory.begin() as session:
            row = session.get(
                TournamentDrawAuthorityModel, (run_id, branch_id, event.event_id)
            )
            row.payload_json = "{}"
        before = repo.get_branch_revision_state(branch_id=branch_id)
        assert service.reload(plan).model_dump_json() == plan.model_dump_json()
        after = repo.get_branch_revision_state(branch_id=branch_id)
        assert after == before
    repo._engine.dispose()
    reopened = _repository(url)
    assert (
        SavedFaxKnockoutFeederService(reopened).reload(plan).model_dump_json()
        == plan.model_dump_json()
    )
    with reopened._session_factory.begin() as session:
        row = session.scalar(
            select(BranchSavedRevisionModel).where(
                BranchSavedRevisionModel.revision_id == saved_id
            )
        )
        damaged = json.loads(row.payload_json)
        damaged["run"]["display_name"] = "rehash was not authorized"
        row.payload_json = json.dumps(damaged)
    with pytest.raises(ValueError):
        SavedFaxKnockoutFeederService(reopened).reload(plan)
    reopened._engine.dispose()
