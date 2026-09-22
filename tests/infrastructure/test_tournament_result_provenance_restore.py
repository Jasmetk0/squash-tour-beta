from __future__ import annotations

import pytest
from sqlalchemy import text

from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)
from beta_engine.infrastructure.db.ranking_state_restore import (
    restore_ranking_revision_state,
)

from test_ranking_fork_tournament_remap import _canonical_source


pytestmark = pytest.mark.pr_critical


@pytest.fixture
def provenance_database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'provenance-restore.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run-one",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run-one",
                branch_id="branch-source",
                display_name="Source",
            )
        )
    try:
        yield factory
    finally:
        engine.dispose()


def _capture(factory):
    with factory.begin() as session:
        session.execute(text("BEGIN"))
        return capture_ranking_revision_state(
            session,
            run_id="run-one",
            branch_id="branch-source",
        )


def test_saved_ranking_restore_preserves_main_entry_provenance(provenance_database):
    source = _canonical_source(with_prize_money=True)
    assert source.canonical_result is not None
    source_statuses = {
        player.player_id: player.main_entry_status
        for player in source.canonical_result.players
    }
    assert source_statuses == {
        "player-a": "wild_card",
        "player-b": "direct",
    }

    with provenance_database.begin() as session:
        OwnedTournamentRankingSourceStore(session).append(source)

    saved = _capture(provenance_database)
    assert len(saved.tournament_sources) == 1
    assert saved.tournament_sources[0].fingerprint == source.fingerprint

    empty = RankingRevisionState(
        run_id="run-one",
        branch_id="branch-source",
        entries=(),
        sources=(),
    )

    with provenance_database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restored_empty = restore_ranking_revision_state(
            session,
            empty.model_dump_json(),
            expected_fingerprint=empty.fingerprint,
            expected_current_fingerprint=saved.fingerprint,
            expected_current_payload=saved.model_dump_json(),
            command_id="provenance-restore-empty",
            run_id="run-one",
            branch_id="branch-source",
        )
    assert restored_empty.fingerprint == empty.fingerprint
    assert _capture(provenance_database).tournament_sources == ()

    current_empty = _capture(provenance_database)
    with provenance_database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restored_saved = restore_ranking_revision_state(
            session,
            saved.model_dump_json(),
            expected_fingerprint=saved.fingerprint,
            expected_current_fingerprint=current_empty.fingerprint,
            expected_current_payload=current_empty.model_dump_json(),
            command_id="provenance-restore-saved",
            run_id="run-one",
            branch_id="branch-source",
        )

    assert restored_saved.fingerprint == saved.fingerprint
    recaptured = _capture(provenance_database)
    assert recaptured.fingerprint == saved.fingerprint
    assert len(recaptured.tournament_sources) == 1

    restored_source = recaptured.tournament_sources[0]
    assert restored_source.fingerprint == source.fingerprint
    assert restored_source.canonical_result is not None
    assert {
        player.player_id: player.main_entry_status
        for player in restored_source.canonical_result.players
    } == source_statuses

    assert restored_source.canonical_awards is not None
    assert source.canonical_awards is not None
    assert (
        restored_source.canonical_awards.fingerprint
        == source.canonical_awards.fingerprint
    )
    assert restored_source.canonical_prize_awards is not None
    assert source.canonical_prize_awards is not None
    assert (
        restored_source.canonical_prize_awards.fingerprint
        == source.canonical_prize_awards.fingerprint
    )
