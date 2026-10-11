from __future__ import annotations

import pytest
from urllib.parse import quote

from tests.api.test_admin_tournament_entry_fields_api import (
    _application,
    _ranking_snapshot,
)
from test_simulation_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import (
    canonical_product_run as _canonical_run,
    save_simulation,
)

from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    TournamentEntryFieldVersionModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)


def _repository(database_url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    return SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )


def _install_viewer_entry_field(
    *,
    database_url: str,
    run_id: str,
    branch_id: str,
    event_id: str,
):
    snapshot = _ranking_snapshot(run_id=run_id, branch_id=branch_id)
    applications = (
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="A",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="C",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="D",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="B",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="E",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="F",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="G",
            window="qualification",
        ),
    )
    repository = _repository(database_url)
    with repository._session_factory.begin() as session:
        session.add(
            PublishedOfficialRankingModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=snapshot.week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        session.flush()
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            ranking_week=snapshot.week,
            command_id="adopt-viewer-ranking",
        )
        return TournamentEntryFieldStore(session).stage_initial(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
            command_id="initial-viewer-field",
        )


@pytest.mark.pr_critical
def test_viewer_entry_field_projects_selected_branch_public_sporting_state(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-entry-field.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run_id = "run"
        branch_id, run_id = _canonical_run(server, run_id)
        event_id = "viewer-event"
        field = _install_viewer_entry_field(
            database_url=database_url,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/{event_id}/entry-field",
            )[0]
            == 404
        )
        save_simulation(server, run_id, branch_id)

        status, payload = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                f"/tournaments/{quote(event_id, safe='')}/entry-field"
            ),
        )

        assert status == 200
        assert payload["schema_version"] == "viewer_tournament_entry_field.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["event_id"] == event_id
        assert payload["field_sequence"] == 1
        assert payload["mode"] == "initial"
        assert payload["main_draw_capacity"] == 4
        assert payload["active_main_entrant_count"] == field.active_main_entrant_count
        assert payload["effective_main_bye_count"] == field.effective_main_bye_count
        assert payload["direct_main_player_ids"] == list(field.direct_main_player_ids)
        assert payload["qualification_player_ids"] == list(
            field.qualification_player_ids
        )
        assert payload["alternate_player_ids"] == list(
            field.below_qualification_cut_player_ids
        )
        assert payload["withdrawn_player_ids"] == list(field.withdrawn_player_ids)

        # A successful sporting Viewer GET is a pure read.
        repository = _repository(database_url)
        with repository._session_factory() as session:
            before = (
                session.query(BranchSavedRevisionModel).count(),
                session.query(TournamentEntryFieldVersionModel).count(),
            )
        assert (
            _request(
                "GET",
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments/{event_id}/entry-field",
            )[0]
            == 200
        )
        with repository._session_factory() as session:
            assert before == (
                session.query(BranchSavedRevisionModel).count(),
                session.query(TournamentEntryFieldVersionModel).count(),
            )

        admin_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event_id}/entry-field"
        )
        status, repaired = _request(
            "POST",
            admin_root + "/pre-draw-withdrawal",
            {
                "schema_version": "canonical_pre_draw_withdrawal_command.v1",
                "command_id": "viewer-live-withdrawal",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "expected_field_fingerprint": field.fingerprint,
                "withdrawn_player_ids": ["D"],
            },
        )
        assert status == 200
        assert repaired["field_sequence"] == 2

        # Live sequence B remains invisible until Save.
        assert (
            _request(
                "GET",
                (
                    f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                    f"/tournaments/{event_id}/entry-field"
                ),
            )[1]
            == payload
        )
        save_simulation(server, run_id, branch_id)
        status, published_repair = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                f"/tournaments/{event_id}/entry-field"
            ),
        )
        assert status == 200
        assert published_repair["field_sequence"] == 2
        assert published_repair["withdrawn_player_ids"] == ["D"]
        assert published_repair != payload

        # Viewer projection deliberately excludes authority/provenance internals.
        assert "field_fingerprint" not in payload
        assert "main_diagnostics" not in payload
        assert "pre_draw_repair_locked_by_draw_input" not in payload


@pytest.mark.pr_critical
def test_viewer_entry_field_returns_not_found_when_selected_branch_has_no_field(
    tmp_path,
) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'viewer-entry-field-missing.sqlite'}"
    ) as server:
        run_id = "run"
        _canonical_run(server, run_id)

        status, _ = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                "/tournaments/missing-event/entry-field"
            ),
        )
        assert status == 404
