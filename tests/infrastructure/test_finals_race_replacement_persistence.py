import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsRaceRow,
    WorldTourFinalsRaceSnapshot,
    WorldTourFinalsSelectedPlayer,
    decide_race_replacement,
    initial_effective_participant_state,
    preview_race_replacement,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.finals_race_replacement import (
    WorldTourFinalsReplacementConflict,
    WorldTourFinalsReplacementStore,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel

pytestmark = pytest.mark.pr_critical
H = "a" * 64


def sources():
    race = WorldTourFinalsRaceSnapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        cutoff_week=RankingWeek(season_index=0, week=60),
        cutoff_official_ranking_fingerprint=H,
        eligibility_fingerprint=H,
        policy_id="best",
        best_n=1,
        input_fingerprint=H,
        eligible_result_count=0,
        rows=tuple(
            WorldTourFinalsRaceRow(
                rank=i,
                player_id=f"P{i}",
                race_points=0,
                counted_results=(),
                tie_break_token=f"t{i}",
            )
            for i in range(1, 9)
        ),
    )
    selection = WorldTourFinalsParticipantSelectionSnapshot(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=6,
        configuration_fingerprint=H,
        race_snapshot_fingerprint=race.fingerprint,
        direct_entry_winner_event_ids=(),
        participants=tuple(
            WorldTourFinalsSelectedPlayer(
                player_id=f"P{i}",
                race_rank=i,
                race_points=0,
                seed=i,
                qualification_source="race",
            )
            for i in range(1, 7)
        ),
    )
    return race, selection


def test_persisted_decline_accept_history_is_append_only_and_idempotent(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'replacement.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run", timeline_start_season=2000, timeline_end_season=2049
            )
        )
        session.add(
            RunBranchModel(run_id="run", branch_id="branch", display_name="Timeline 1")
        )
    race, selection = sources()
    initial = initial_effective_participant_state(selection, command_id="initial")
    preview = preview_race_replacement(
        race=race,
        selection=selection,
        effective=initial,
        withdrawn_player_id="P3",
        withdrawal_reason="medical reason",
        vacancy_id="v1",
        command_id="preview",
    )
    declined, _ = decide_race_replacement(
        preview=preview,
        race=race,
        selection=selection,
        effective=initial,
        decision="decline",
        command_id="decline-p7",
    )
    accepted, successor = decide_race_replacement(
        preview=declined,
        race=race,
        selection=selection,
        effective=initial,
        decision="accept",
        command_id="accept-p8",
    )
    assert successor is not None
    with factory.begin() as session:
        store = WorldTourFinalsReplacementStore(session)
        assert store.put_state(initial) == store.put_state(initial)
        for authority in (preview, declined, accepted):
            assert store.put_authority(authority) == authority
        assert store.put_state(successor) == successor
        assert [
            a.status
            for a in store.authority_history(
                run_id="run", branch_id="branch", vacancy_id="v1"
            )
        ] == ["awaiting_decision", "awaiting_decision", "accepted"]
        assert tuple(
            p.player_id
            for p in store.latest_state(
                run_id="run", branch_id="branch", target_season_index=0
            ).participants
        ) == ("P1", "P2", "P4", "P5", "P6", "P8")
        with pytest.raises(
            WorldTourFinalsReplacementConflict, match="different request"
        ):
            store.put_authority(
                preview.model_copy(update={"withdrawal_reason": "different"})
            )
    engine.dispose()
