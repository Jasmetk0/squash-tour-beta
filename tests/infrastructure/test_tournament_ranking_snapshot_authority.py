"""Published Official Ranking -> tournament authority persistence and recovery."""

import pytest
from sqlalchemy import select, text

from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.revision_state import (
    RankingRevisionEntry,
    RankingRevisionReceipt,
    RankingRevisionState,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    TournamentRankingSnapshotAuthorityModel,
)
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)
from beta_engine.infrastructure.db.ranking_fork_remap import (
    _remap_tournament_ranking_snapshot_authorities,
)
from beta_engine.infrastructure.db.ranking_state_restore import (
    restore_ranking_revision_state,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityConflict,
    TournamentRankingSnapshotAuthorityStore,
)


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'tournament-ranking.db'}")
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


def ranking(week: int = 1, *, previous=None):
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=week),
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=(),
        results=(),
        previous=previous,
    )


def publish(session, snapshot):
    session.add(
        PublishedOfficialRankingModel(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            week_ordinal=snapshot.week.ordinal,
            snapshot_fingerprint=snapshot.fingerprint,
            payload_json=snapshot.model_dump_json(),
        )
    )
    session.flush()


@pytest.mark.smoke
def test_adopt_requires_publication_is_idempotent_and_conflicts_fail_closed(database):
    first = ranking()
    second = ranking(2, previous=first)
    with database.begin() as session:
        store = TournamentRankingSnapshotAuthorityStore(session)
        with pytest.raises(ValueError, match="published Official Ranking"):
            store.adopt(
                run_id="run",
                branch_id="branch",
                event_id="event-a",
                ranking_week=first.week,
                command_id="adopt-a",
            )
        publish(session, first)
        publish(session, second)
        authority = store.adopt(
            run_id="run",
            branch_id="branch",
            event_id="event-a",
            ranking_week=first.week,
            command_id="adopt-a",
        )
        assert store.adopt(
            run_id="run",
            branch_id="branch",
            event_id="event-a",
            ranking_week=first.week,
            command_id="adopt-a",
        ) == authority
        assert authority.ranking_snapshot == first
        assert authority.ranking_snapshot_fingerprint == first.fingerprint
        with pytest.raises(TournamentRankingSnapshotAuthorityConflict):
            store.adopt(
                run_id="run",
                branch_id="branch",
                event_id="event-a",
                ranking_week=second.week,
                command_id="adopt-a-new-ranking",
            )

    with database() as session:
        stored = TournamentRankingSnapshotAuthorityStore(session).history(
            run_id="run", branch_id="branch"
        )
        assert stored == (authority,)


@pytest.mark.smoke
def test_corrupt_authority_or_publication_is_rejected(database):
    snapshot = ranking()
    with database.begin() as session:
        publish(session, snapshot)
        authority = TournamentRankingSnapshotAuthorityStore(session).adopt(
            run_id="run",
            branch_id="branch",
            event_id="event-a",
            ranking_week=snapshot.week,
            command_id="adopt-a",
        )

    with database.begin() as session:
        row = session.get(
            TournamentRankingSnapshotAuthorityModel,
            ("run", "branch", "event-a"),
        )
        row.authority_fingerprint = "0" * 64
    with database() as session:
        with pytest.raises(ValueError, match="corrupt"):
            TournamentRankingSnapshotAuthorityStore(session).get(
                run_id="run", branch_id="branch", event_id="event-a"
            )

    with database.begin() as session:
        row = session.get(
            TournamentRankingSnapshotAuthorityModel,
            ("run", "branch", "event-a"),
        )
        row.authority_fingerprint = authority.fingerprint
        publication = session.get(
            PublishedOfficialRankingModel,
            ("run", "branch", snapshot.week.ordinal),
        )
        publication.snapshot_fingerprint = "0" * 64
    with database() as session:
        with pytest.raises(ValueError):
            TournamentRankingSnapshotAuthorityStore(session).get(
                run_id="run", branch_id="branch", event_id="event-a"
            )


@pytest.mark.smoke
def test_revision_restore_preserves_exact_event_ranking_authority(database):
    snapshot = ranking()
    with database.begin() as session:
        publish(session, snapshot)
        store = TournamentRankingSnapshotAuthorityStore(session)
        current_authority = store.adopt(
            run_id="run",
            branch_id="branch",
            event_id="event-a",
            ranking_week=snapshot.week,
            command_id="adopt-a",
        )

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        current = capture_ranking_revision_state(
            session, run_id="run", branch_id="branch"
        )
    assert current.tournament_ranking_snapshot_authorities == (current_authority,)

    target_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-b",
        ranking_week=snapshot.week,
        ranking_snapshot=snapshot,
        adopted_by_command_id="adopt-b",
    )
    target = RankingRevisionState.model_validate_json(
        current.model_copy(
            update={
                "tournament_ranking_snapshot_authorities": (target_authority,)
            }
        ).model_dump_json()
    )

    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restored = restore_ranking_revision_state(
            session,
            target.model_dump_json(),
            expected_fingerprint=target.fingerprint,
            expected_current_fingerprint=current.fingerprint,
            command_id="restore-ranking-binding",
            run_id="run",
            branch_id="branch",
        )
        assert restored == target
        store = TournamentRankingSnapshotAuthorityStore(session)
        assert store.get(
            run_id="run", branch_id="branch", event_id="event-a"
        ) is None
        assert store.get(
            run_id="run", branch_id="branch", event_id="event-b"
        ) == target_authority
        rows = session.scalars(
            select(TournamentRankingSnapshotAuthorityModel)
        ).all()
        assert len(rows) == 1


@pytest.mark.pr_critical
def test_branch_fork_remaps_tournament_ranking_snapshot_to_target_publication():
    source_snapshot = ranking()
    target_snapshot = source_snapshot.model_copy(update={"branch_id": "target"})
    source_entry = RankingRevisionEntry(
        snapshot=source_snapshot,
        inputs={
            "players": (),
            "results": (),
            "disciplinary_zeros": (),
            "zeros_from_history": False,
            "command_request_fingerprint": "0" * 64,
        },
        receipts=(
            RankingRevisionReceipt(
                command_id="bootstrap",
                request_fingerprint="0" * 64,
                request_payload_json="{}",
            ),
        ),
    )
    target_entry = RankingRevisionEntry(
        snapshot=target_snapshot,
        inputs=source_entry.inputs,
        receipts=source_entry.receipts,
    )
    source_authority = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event-a",
        ranking_week=source_snapshot.week,
        ranking_snapshot=source_snapshot,
        adopted_by_command_id="adopt-a",
    )

    remapped, mapping = _remap_tournament_ranking_snapshot_authorities(
        (source_authority,),
        run_id="run",
        source_branch_id="branch",
        target_branch_id="target",
        source_entries=(source_entry,),
        target_entries=(target_entry,),
    )

    assert len(remapped) == 1
    target_authority = remapped[0]
    assert target_authority.branch_id == "target"
    assert target_authority.ranking_snapshot == target_snapshot
    assert target_authority.ranking_snapshot_fingerprint == target_snapshot.fingerprint
    assert target_authority.fingerprint != source_authority.fingerprint
    assert mapping[source_authority.fingerprint] == target_authority
