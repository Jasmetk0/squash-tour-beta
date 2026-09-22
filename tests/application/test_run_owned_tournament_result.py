from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.application.run_owned_match_package import build_run_owned_match_package
from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    PointAwardMetadata,
    PointAwardSummary,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.result_authority import (
    build_tournament_result_authority,
    project_tournament_result_legacy_dto,
)


pytestmark = pytest.mark.smoke


def _input(*, qualification=False):
    if qualification:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=2,
            qualifier_spots=1,
        )
        direct = ("A", "B", "C")
        q = ("D", "E")
        placeholders = ("Q1",)
    else:
        capacity = TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        )
        direct = ("A", "B", "C", "D")
        q = ()
        placeholders = ()
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=1234,
        main_seed_count=1,
        qualification_seed_count=1 if qualification else 0,
        field_sequence=1,
        capacity=capacity,
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=q,
        qualifier_placeholder_ids=placeholders,
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:1],
        qualification_seed_player_ids=q[:1] if qualification else (),
    )


def _multi_qualification_input():
    direct = ("A", "B", "C", "D")
    qualification = tuple(f"QF{index:02d}" for index in range(1, 17))
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input-multi-q",
        draw_seed=4321,
        main_seed_count=2,
        qualification_seed_count=4,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=8,
            qualification_draw_size=16,
            qualifier_spots=4,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=direct,
        qualification_player_ids=qualification,
        qualifier_placeholder_ids=("Q1", "Q2", "Q3", "Q4"),
        withdrawn_player_ids=(),
        main_seed_player_ids=direct[:2],
        qualification_seed_player_ids=qualification[:4],
    )


def _multi_qualification_event():
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Multi-Q Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=8,
        qualification_draw_size=16,
        qualifier_spots=4,
    )


def _event(*, qualification=False):
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=2 if qualification else 0,
        qualifier_spots=1 if qualification else 0,
    )


def _complete(draw, package):
    projected = package.model_copy(deep=True)
    qualifier_winners: dict[str, str] = {}

    def complete_bracket(bracket, records):
        winners = {}
        slots = {slot.slot_index: slot for slot in bracket.slots}
        by_id = {record.match_id: record for record in records}
        for node in sorted(
            bracket.nodes,
            key=lambda item: (item.round_number, item.round_sequence),
        ):
            def resolve(source):
                if source.startswith("winner:"):
                    return winners[source.removeprefix("winner:")]
                slot = slots[int(source.removeprefix("slot:"))]
                if slot.entrant_kind == "player":
                    return slot.player_id
                if slot.entrant_kind == "qualifier_placeholder":
                    winner = qualifier_winners.get(slot.placeholder_id)
                    if winner is None:
                        raise AssertionError("qualifier winner missing")
                    return winner
                if slot.entrant_kind == "bye":
                    return None
                raise AssertionError("unsupported source")

            top = resolve(node.source_top)
            bottom = resolve(node.source_bottom)
            record = by_id[node.node_id]
            if top is None or bottom is None:
                winner = bottom if top is None else top
                loser = None
                score = "BYE"
            else:
                winner = top
                loser = bottom
                score = "3-0"
            record.top_player_id = top
            record.bottom_player_id = bottom
            record.winner_player_id = winner
            record.loser_player_id = loser
            record.scoreline = score
            record.status = "completed"
            record.result_fingerprint = (
                f"{node.round_number:02x}{node.round_sequence:02x}".ljust(64, "a")
            )[:64]
            winners[node.node_id] = winner
        terminal = max(
            bracket.nodes,
            key=lambda n: (n.round_number, n.round_sequence),
        )
        return winners[terminal.node_id]

    for index, bracket in enumerate(draw.qualification_brackets, start=1):
        qualifier_winners[bracket.section_id or f"Q{index}"] = complete_bracket(
            bracket,
            projected.qualification_matches,
        )
    complete_bracket(
        draw.main,
        projected.main_draw_matches,
    )
    return projected


def test_canonical_result_derives_champion_finalist_and_stages_without_legacy_service():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert authority.champion_player_id == "A"
    assert authority.finalist_player_id in {"B", "C", "D"}
    assert len(authority.matches) == 3
    stages = {player.player_id: player.reached_stage for player in authority.players}
    assert stages[authority.champion_player_id] == "champion"
    assert stages[authority.finalist_player_id] == "finalist"
    assert sum(stage == "semifinal" for stage in stages.values()) == 2
    assert {
        player.main_entry_status for player in authority.players
    } == {"direct"}
    assert authority.draw_authority_fingerprint == draw.fingerprint


def test_canonical_result_preserves_qualification_provenance_into_main():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(qualification=True),
        command_id="draw",
    )
    event = _event(qualification=True)
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert authority.qualification_winner_ids == ("D",)
    q_winner = next(player for player in authority.players if player.player_id == "D")
    assert q_winner.qualifier is True
    assert q_winner.draw_type == "both"
    assert len(authority.matches) == 4

    dto = project_tournament_result_legacy_dto(
        authority=authority,
        event=event,
        package=completed,
        seed=777,
    )
    assert dto.completion_status == "complete"
    assert dto.summary.qualification_winner_count == 1
    assert dto.summary.completed_matches == 4
    assert dto.qualification_winners[0].player_id == "D"
    assert dto.metadata.draw_package_fingerprint == draw.fingerprint


def test_canonical_result_keeps_withdrawn_q_winner_separate_from_lucky_loser():
    initial = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(qualification=True),
        command_id="draw-q-winner-ll-repair",
    )
    q_winner = "D"
    lucky_loser = "E"

    linked_q_slot = next(
        slot
        for slot in initial.main.slots
        if slot.entrant_kind == "qualifier_placeholder"
    )
    repaired_slots = tuple(
        slot.model_copy(
            update={
                "entrant_kind": "player",
                "player_id": lucky_loser,
                "placeholder_id": None,
                "seed_number": None,
                "is_seed_protected": False,
                "entry_status": "lucky_loser",
                "lucky_loser_placeholder_id": "LL1",
            }
        )
        if slot.slot_index == linked_q_slot.slot_index
        else slot
        for slot in initial.main.slots
    )
    repaired_main = initial.main.model_copy(
        update={
            "slots": repaired_slots,
            "qualifier_placeholder_slots": (),
            "lucky_loser_placeholder_slots": (),
        }
    )
    draw = initial.model_copy(update={"main": repaired_main})

    event = _event(qualification=True)
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert authority.qualification_winner_ids == (q_winner,)
    by_player = {player.player_id: player for player in authority.players}

    withdrawn_winner = by_player[q_winner]
    assert withdrawn_winner.draw_type == "qualification"
    assert withdrawn_winner.qualifier is True
    assert withdrawn_winner.reached_stage == "qualification_winner"

    replacement = by_player[lucky_loser]
    assert replacement.draw_type == "both"
    assert replacement.qualifier is True
    assert replacement.main_entry_status == "lucky_loser"
    assert lucky_loser not in authority.qualification_winner_ids

    q_match = next(
        match
        for match in authority.matches
        if match.draw_type == "qualification"
    )
    assert q_match.winner_player_id == q_winner
    assert q_match.loser_player_id == lucky_loser


@pytest.mark.pr_critical
def test_canonical_result_preserves_wild_card_main_entry_provenance():
    initial = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw-wild-card-result-provenance",
    )
    target = next(
        slot
        for slot in initial.main.slots
        if slot.player_id is not None and slot.seed_number is None
    )
    wild_card_player_id = target.player_id
    repaired_main = initial.main.model_copy(
        update={
            "slots": tuple(
                slot.model_copy(update={"entry_status": "wild_card"})
                if slot.slot_index == target.slot_index
                else slot
                for slot in initial.main.slots
            )
        }
    )
    draw = initial.model_copy(update={"main": repaired_main})
    package = _complete(
        draw,
        build_run_owned_match_package(
            draw=draw,
            event=_event(),
            week=RankingWeek(season_index=0, week=1),
        ),
    )

    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=package,
    )

    by_player = {player.player_id: player for player in authority.players}
    assert by_player[wild_card_player_id].main_entry_status == "wild_card"
    assert all(
        player.main_entry_status == "direct"
        for player in authority.players
        if player.player_id != wild_card_player_id
    )


@pytest.mark.pr_critical
def test_historical_result_payload_without_main_entry_status_keeps_fingerprint():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw-historical-result-provenance",
    )
    week = RankingWeek(season_index=0, week=1)
    package = _complete(
        draw,
        build_run_owned_match_package(draw=draw, event=_event(), week=week),
    )
    current = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    historical_payload = current.model_dump(mode="json")
    for player in historical_payload["players"]:
        player.pop("main_entry_status", None)
    expected = hashlib.sha256(
        json.dumps(
            historical_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    reopened = type(current).model_validate_json(
        json.dumps(
            historical_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    assert all(player.main_entry_status is None for player in reopened.players)
    assert reopened.fingerprint == expected
    assert all(
        "main_entry_status" not in player
        for player in reopened.model_dump(mode="json")["players"]
    )


def test_canonical_result_collects_four_independent_qualification_winners():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_multi_qualification_input(),
        command_id="draw-multi-q",
    )
    event = _multi_qualification_event()
    package = build_run_owned_match_package(
        draw=draw,
        event=event,
        week=RankingWeek(season_index=0, week=1),
    )
    completed = _complete(draw, package)
    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        draw=draw,
        package=completed,
    )

    assert len(authority.qualification_winner_ids) == 4
    assert len(set(authority.qualification_winner_ids)) == 4
    assert set(authority.qualification_winner_ids).issubset(
        {f"QF{index:02d}" for index in range(1, 17)}
    )
    assert len(authority.matches) == 19
    assert all(
        next(
            player
            for player in authority.players
            if player.player_id == winner
        ).draw_type
        == "both"
        for winner in authority.qualification_winner_ids
    )

    dto = project_tournament_result_legacy_dto(
        authority=authority,
        event=event,
        package=completed,
        seed=888,
    )
    assert dto.summary.qualification_winner_count == 4
    assert {
        winner.player_id for winner in dto.qualification_winners
    } == set(authority.qualification_winner_ids)


def test_owned_source_v2_persists_canonical_result_and_v1_remains_supported():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    event = _event()
    week = RankingWeek(season_index=0, week=1)
    package = _complete(
        draw,
        build_run_owned_match_package(draw=draw, event=event, week=week),
    )
    canonical = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    result = project_tournament_result_legacy_dto(
        authority=canonical,
        event=event,
        package=package,
        seed=7,
    )
    awards = EventPointAwardPackage(
        event_id="event",
        season="2000/2001",
        template_id="template",
        seed=8,
        dry_run=False,
        persisted=True,
        applied=False,
        awards=[],
        summary=PointAwardSummary(event_id="event"),
        metadata=PointAwardMetadata(
            event_id="event",
            season="2000/2001",
            seed=8,
            dry_run=False,
            persisted=True,
            applied=False,
            build_fingerprint="4" * 64,
            result_package_fingerprint=result.metadata.build_fingerprint,
            point_distribution_fingerprint="5" * 64,
            point_distribution_source="authored.test",
        ),
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=week,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.metadata.build_fingerprint,
        expected_award_fingerprint=awards.metadata.build_fingerprint,
    )
    v2 = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v2",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=canonical,
        adopted_by_command_id="close",
        provenance_kind="canonical_run_owned_tournament_result",
    )
    assert (
        OwnedTournamentRankingSource.model_validate_json(v2.model_dump_json())
        == v2
    )

    changed_players = list(result.player_results)
    changed_players[0] = changed_players[0].model_copy(
        update={"reached_stage": "unknown"}
    )
    mismatched_result = result.model_copy(
        update={"player_results": changed_players}
    )
    with pytest.raises(
        ValueError, match="Canonical tournament player-result projection mismatch"
    ):
        OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v2",
            binding=binding,
            result=mismatched_result,
            awards=awards,
            canonical_result=canonical,
            adopted_by_command_id="bad-close",
            provenance_kind="canonical_run_owned_tournament_result",
        )

    v1 = OwnedTournamentRankingSource(
        binding=binding,
        result=result,
        awards=awards,
        adopted_by_command_id="legacy-close",
    )
    old_payload = v1.model_dump(mode="json")
    old_payload.pop("canonical_result", None)
    old_payload.pop("canonical_awards", None)
    expected_v1_fingerprint = hashlib.sha256(
        json.dumps(
            old_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    old_json = json.dumps(old_payload, sort_keys=True, separators=(",", ":"))
    reopened = OwnedTournamentRankingSource.model_validate_json(old_json)
    assert reopened.schema_version == "owned_tournament_ranking_source.v1"
    assert reopened.canonical_result is None
    assert reopened.fingerprint == expected_v1_fingerprint


def test_canonical_result_tracks_walkover_without_counting_played_win_or_loss():
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw-walkover",
    )
    event = _event()
    week = RankingWeek(season_index=0, week=1)
    package = _complete(
        draw,
        build_run_owned_match_package(draw=draw, event=event, week=week),
    )
    final_round = max(match.round_number for match in package.main_draw_matches)
    final = next(
        match for match in package.main_draw_matches if match.round_number == final_round
    )
    final.scoreline = "W/O"
    final.result_fingerprint = hashlib.sha256(
        f"walkover|{final.match_id}|{final.winner_player_id}|{final.loser_player_id}".encode()
    ).hexdigest()

    authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    winner = next(
        player
        for player in authority.players
        if player.player_id == final.winner_player_id
    )
    withdrawn = next(
        player
        for player in authority.players
        if player.player_id == final.loser_player_id
    )

    assert winner.reached_stage == "champion"
    assert winner.walkovers_received == 1
    assert winner.wins == 1
    assert withdrawn.reached_stage == "finalist"
    assert withdrawn.retired_or_walkover_loss is True
    assert withdrawn.losses == 0

    dto = project_tournament_result_legacy_dto(
        authority=authority,
        event=event,
        package=package,
        seed=999,
    )
    dto_winner = next(
        player for player in dto.player_results if player.player_id == winner.player_id
    )
    dto_withdrawn = next(
        player
        for player in dto.player_results
        if player.player_id == withdrawn.player_id
    )
    assert dto_winner.walkovers_received == 1
    assert dto_withdrawn.retired_or_walkover_loss is True
    assert next(
        ref for ref in dto.match_result_refs if ref.match_id == final.match_id
    ).scoreline == "W/O"
