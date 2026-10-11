from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)


pytestmark = pytest.mark.smoke


def ranking_snapshot(player_points: dict[str, int]):
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=3)
    players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"ranking-token-{player_id}",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player_id in sorted(player_points)
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=points,
        )
        for player_id, points in sorted(player_points.items())
    )
    return calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=target,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=players,
        results=results,
    )


def authority(player_points: dict[str, int] | None = None):
    snapshot = ranking_snapshot(
        player_points
        or {
            "A": 100,
            "B": 90,
            "C": 80,
            "D": 70,
            "E": 60,
            "F": 50,
            "G": 40,
        }
    )
    return TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        ranking_week=snapshot.week,
        ranking_snapshot=snapshot,
        adopted_by_command_id="adopt-ranking",
    )


def app(
    player_id: str,
    window: str,
    *,
    slot: int = 10,
    token: str | None = None,
    eligible: bool = True,
):
    return TournamentEntryApplication(
        application_id=f"app-{player_id}",
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=player_id,
        entry_window=window,
        decision_slot_ordinal=slot,
        nr_tie_break_token=token or f"entry-token-{player_id}",
        eligible=eligible,
    )


@pytest.mark.pr_critical
@pytest.mark.parametrize("main_draw_size", (2, 4, 8, 16, 32, 64, 128))
def test_classic_main_capacity_accepts_supported_power_of_two_sizes(main_draw_size):
    capacity = TournamentEntryFieldCapacity(main_draw_size=main_draw_size)
    assert capacity.main_draw_size == main_draw_size


@pytest.mark.pr_critical
@pytest.mark.parametrize("main_draw_size", (1, 3, 6, 12, 24, 48, 96, 127))
def test_classic_main_capacity_rejects_non_power_of_two_sizes(main_draw_size):
    with pytest.raises(
        ValueError,
        match="Classic Main Draw capacity must be one of 2, 4, 8, 16, 32, 64, 128",
    ):
        TournamentEntryFieldCapacity(main_draw_size=main_draw_size)


def capacity():
    # Three ranking-derived direct places plus one future Q placeholder.
    return TournamentEntryFieldCapacity(
        main_draw_size=4,
        qualification_draw_size=2,
        qualifier_spots=1,
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_initial_field_keeps_main_window_cut_then_ranks_q_pool(reverse):
    auth = authority()
    applications = [
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        # B is ranked above C/D but entered only in the Qualification window.
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    ]
    if reverse:
        applications.reverse()

    field = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=capacity(),
    )

    assert field.direct_main_player_ids == ("A", "C", "D")
    assert field.qualification_player_ids == ("B", "E")
    assert field.below_qualification_cut_player_ids == ("F", "G")
    assert field.withdrawn_player_ids == ()


def test_pre_draw_main_withdrawal_promotes_best_q_and_backfills_q():
    auth = authority()
    applications = [
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=capacity(),
    )

    repaired = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=applications,
        previous=initial,
        withdrawn_player_ids=("D",),
    )

    assert repaired.direct_main_player_ids == ("A", "B", "C")
    assert repaired.qualification_player_ids == ("E", "F")
    assert repaired.below_qualification_cut_player_ids == ("G",)
    assert repaired.withdrawn_player_ids == ("D",)
    assert repaired.base_field_fingerprint == initial.fingerprint


def test_pre_draw_q_withdrawal_backfills_without_changing_main():
    auth = authority()
    applications = [
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=capacity(),
    )

    repaired = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=applications,
        previous=initial,
        withdrawn_player_ids=("E",),
    )

    assert repaired.direct_main_player_ids == ("A", "C", "D")
    assert repaired.qualification_player_ids == ("B", "F")
    assert repaired.below_qualification_cut_player_ids == ("G",)
    assert repaired.withdrawn_player_ids == ("E",)


def test_multi_withdrawal_repair_is_atomic_and_order_independent():
    auth = authority()
    applications = [
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=capacity(),
    )

    forward = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=applications,
        previous=initial,
        withdrawn_player_ids=("D", "E"),
    )
    reverse = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=reversed(applications),
        previous=initial,
        withdrawn_player_ids=("E", "D"),
    )

    assert forward == reverse
    assert forward.direct_main_player_ids == ("A", "B", "C")
    assert forward.qualification_player_ids == ("F", "G")
    assert forward.below_qualification_cut_player_ids == ()
    assert forward.withdrawn_player_ids == ("D", "E")



def test_pre_draw_repair_retry_is_idempotent_and_new_withdrawal_can_follow():
    auth = authority()
    applications = [
        app("A", "main"),
        app("C", "main"),
        app("D", "main"),
        app("B", "qualification"),
        app("E", "qualification"),
        app("F", "qualification"),
        app("G", "qualification"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=capacity(),
    )

    first = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=applications,
        previous=initial,
        withdrawn_player_ids=("D",),
    )
    retry = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=reversed(applications),
        previous=first,
        withdrawn_player_ids=("D",),
    )
    assert retry is first

    second = TournamentEntryFieldResolver.repair_pre_draw(
        authority=auth,
        applications=applications,
        previous=first,
        withdrawn_player_ids=("D", "E"),
    )
    assert second.direct_main_player_ids == ("A", "B", "C")
    assert second.qualification_player_ids == ("F", "G")
    assert second.below_qualification_cut_player_ids == ()
    assert second.withdrawn_player_ids == ("D", "E")


def test_nr_players_are_below_ranked_and_use_slot_then_stable_token():
    auth = authority({"A": 100})
    applications = [
        app("A", "main"),
        app("N2", "qualification", slot=5, token="b"),
        app("N1", "qualification", slot=4, token="z"),
        app("N3", "qualification", slot=5, token="a"),
    ]
    field = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=2,
            qualification_draw_size=3,
            qualifier_spots=1,
        ),
    )

    assert field.direct_main_player_ids == ("A",)
    assert field.qualification_player_ids == ("N1", "N3", "N2")


def test_duplicate_nr_token_and_stale_repair_evidence_fail_closed():
    auth = authority({"A": 100})
    bad = [
        app("A", "main"),
        app("N1", "qualification", slot=4, token="same"),
        app("N2", "qualification", slot=4, token="same"),
    ]
    with pytest.raises(ValueError, match="tie-break tokens"):
        TournamentEntryFieldResolver.build_initial(
            authority=auth,
            applications=bad,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=2,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
        )

    good = [
        app("A", "main"),
        app("N1", "qualification", slot=4, token="n1"),
        app("N2", "qualification", slot=5, token="n2"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=good,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=2,
            qualification_draw_size=2,
            qualifier_spots=1,
        ),
    )
    changed = [
        *good,
        app("N3", "qualification", slot=6, token="n3"),
    ]
    with pytest.raises(ValueError, match="application set changed"):
        TournamentEntryFieldResolver.repair_pre_draw(
            authority=auth,
            applications=changed,
            previous=initial,
            withdrawn_player_ids=("A",),
        )


def test_repair_rejects_player_outside_predecessor_field():
    auth = authority({"A": 100, "B": 90})
    applications = [
        app("A", "main"),
        app("B", "qualification"),
    ]
    initial = TournamentEntryFieldResolver.build_initial(
        authority=auth,
        applications=applications,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=2,
            qualification_draw_size=1,
            qualifier_spots=1,
        ),
    )
    with pytest.raises(ValueError, match="outside predecessor field"):
        TournamentEntryFieldResolver.repair_pre_draw(
            authority=auth,
            applications=applications,
            previous=initial,
            withdrawn_player_ids=("missing",),
        )
