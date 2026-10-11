"""Saved Revision recovery for archived Season Closing Rankings."""

import pytest
from sqlalchemy import text

from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionState,
    load_ranking_revision_state,
)
from beta_engine.domain.rankings.season_closing import (
    calculate_season_closing_ranking,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    capture_saved_ranking_component,
    restore_saved_ranking_component,
)
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingStore,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'closing-recovery.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
            )
        )
    yield factory
    engine.dispose()


def _evidence():
    week = RankingWeek(season_index=0, week=61)
    policy = OfficialRankingPolicy(policy_id="season-2000-policy", best_n=15)
    predecessor = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week,
        policy=policy,
        players=(),
        results=(),
    )
    closing = calculate_season_closing_ranking(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        policy=policy,
        players=(),
        results=(),
        predecessor=predecessor,
    )
    transition = {
        "world": {
            "run_id": "run",
            "branch_id": "branch",
            "current_ordinal": week.ordinal,
            "ranking_fingerprint": predecessor.fingerprint,
        },
        "publications": [
            {
                "run_id": "run",
                "branch_id": "branch",
                "week_ordinal": week.ordinal,
                "snapshot_fingerprint": predecessor.fingerprint,
                "payload_json": predecessor.model_dump_json(),
            }
        ],
        "receipts": [],
        "events": [],
    }
    state = RankingRevisionState(
        schema_version="ranking_revision_state.v6",
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        season_closing_rankings=(closing,),
        authoritative_transition_state=transition,
    )
    return predecessor, closing, state


def _saved_payload(state):
    return {
        "content": {
            "ranking_preparation": {
                "fingerprint": state.fingerprint,
                "state": state.model_dump(mode="json"),
            }
        }
    }


def test_v6_roundtrip_binds_closing_archive_to_week61_publication():
    predecessor, closing, state = _evidence()
    reopened = load_ranking_revision_state(
        state.model_dump_json(),
        expected_fingerprint=state.fingerprint,
        run_id="run",
        branch_id="branch",
    )
    assert reopened == state
    assert reopened.season_closing_rankings == (closing,)

    with pytest.raises(ValueError, match="Legacy ranking revision state"):
        RankingRevisionState(
            schema_version="ranking_revision_state.v5",
            run_id="run",
            branch_id="branch",
            entries=(),
            sources=(),
            season_closing_rankings=(closing,),
            authoritative_transition_state=state.authoritative_transition_state,
        )

    with pytest.raises(ValueError, match="policy differs"):
        RankingRevisionState(
            schema_version="ranking_revision_state.v6",
            run_id="run",
            branch_id="branch",
            entries=(),
            sources=(),
            season_closing_rankings=(
                closing.model_copy(
                    update={
                        "policy": OfficialRankingPolicy(
                            policy_id="wrong-policy",
                            best_n=predecessor.policy.best_n,
                        )
                    }
                ),
            ),
            authoritative_transition_state=state.authoritative_transition_state,
        )


@pytest.mark.pr_critical
def test_saved_revision_roundtrip_restores_closing_archive_atomically(database):
    predecessor, closing, expected = _evidence()
    saved = _saved_payload(expected)
    empty = {"content": {}}

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=closing.completed_week.ordinal,
                snapshot_fingerprint=predecessor.fingerprint,
                payload_json=predecessor.model_dump_json(),
            )
        )
        session.add(
            AuthoritativeWorldStateModel(
                run_id="run",
                branch_id="branch",
                current_ordinal=closing.completed_week.ordinal,
                ranking_fingerprint=predecessor.fingerprint,
            )
        )
        # The production restore path flushes recovered publications before archive
        # installation. This fixture uses autoflush=False, so mirror that boundary.
        session.flush()
        SeasonClosingRankingStore(session).install_restored(closing)

        payload = {"content": {}}
        capture_saved_ranking_component(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        captured = payload["content"]["ranking_preparation"]
        assert captured["state"]["schema_version"] == "ranking_revision_state.v6"
        assert len(captured["state"]["season_closing_rankings"]) == 1
        saved = payload

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore_saved_ranking_component(
            session,
            current_payload=saved,
            target_payload=empty,
            run_id="run",
            branch_id="branch",
            command_id="drop-closing",
        )
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="branch"
        ) == ()
        assert session.get(
            PublishedOfficialRankingModel,
            ("run", "branch", closing.completed_week.ordinal),
        ) is None

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore_saved_ranking_component(
            session,
            current_payload=empty,
            target_payload=saved,
            run_id="run",
            branch_id="branch",
            command_id="restore-closing",
        )
        restored = SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="branch"
        )
        assert restored == (closing,)
        assert capture_ranking_revision_state(
            session,
            run_id="run",
            branch_id="branch",
        ).season_closing_rankings == (closing,)

    # Lost-response retry is read-only and cannot duplicate the archive.
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore_saved_ranking_component(
            session,
            current_payload=empty,
            target_payload=saved,
            run_id="run",
            branch_id="branch",
            command_id="restore-closing",
        )
        assert SeasonClosingRankingStore(session).history(
            run_id="run", branch_id="branch"
        ) == (closing,)


def test_trusted_install_requires_matching_week61_publication(database):
    _, closing, _ = _evidence()
    with database.begin() as session:
        with pytest.raises(ValueError, match="Official Week 61 publication"):
            SeasonClosingRankingStore(session).install_restored(closing)
