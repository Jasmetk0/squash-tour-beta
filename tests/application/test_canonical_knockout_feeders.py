"""Actual MatchEngine proofs for the stateless Q/Main feeder projection.

These are component/kernel tests, not native v4 slot/season/points acceptance.
All players have explicit test eligibility; original FAX source bytes are read-only.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.canonical_knockout_feeders import (
    CanonicalKnockoutFeederPlan,
    freeze_knockout_feeder_plan,
    project_knockout_progress,
)
from beta_engine.application.native_canonical_ranked_awards import (
    prepare_native_canonical_ranked_awards,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.players.calendar_canonical_match import (
    CalendarCanonicalPlayerSource,
)
from beta_engine.domain.players.calendar_match_state import (
    CalendarMatchPlayerState,
    CalendarMatchStatePolicy,
    advance_played_slot,
)
from beta_engine.domain.players.calendar_native_competition import terminal_players
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.players.sporting import PlayerSportingBootstrapPolicy
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    project_player,
)
from beta_engine.domain.tournaments.calendar_global_slots import calculate_match
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from tests.domain.test_match_engine import _player
from tests.infrastructure import test_fax_reference_player_draw as fax_inputs

pytestmark = [pytest.mark.smoke, pytest.mark.pr_critical]


@pytest.fixture(scope="module")
def fax_source(tmp_path_factory):
    return fax_inputs.fax_source.__wrapped__(tmp_path_factory)


@pytest.fixture(scope="module")
def ranking():
    return fax_inputs.ranking_snapshot(fax_inputs.PLAYERS)


def feeder_plan(source, ranking, main_size, *, authored_points=False):
    event = next(e for e in source[0].events if e.main_draw_size == main_size)
    if authored_points:
        # Disposable points, frozen before playing. The original table stays unchanged.
        table = {
            **event.ranking_points_table,
            "qualification_winner": 17,
            "qualification_final": 11,
            "qualification_semifinal": 3,
        }
        if main_size == 32:
            table["qualification_round"] = 0
        event = event.model_copy(update={"ranking_points_table": table})
    inputs = fax_inputs.in_memory_input(event, ranking)
    draw = TournamentDrawAuthorityBuilder.build(draw_input=inputs, command_id="draw")
    return freeze_knockout_feeder_plan(
        source=fax_inputs.package_draw(event, inputs, draw),
        source_saved_revision_id="owned-Saved-source",
        source_saved_content_hash="3" * 64,
        calendar=RunCalendar(61, 37, 2000, 50),
    )


def played(plan):
    biographies = {
        pid: CalendarCanonicalPlayerSource(
            player=_player(player_id=pid, base=55 + i % 25),
            source_generation_fingerprint=f"test-source-{pid}",
            potential_ability=90,
        )
        for i, pid in enumerate(fax_inputs.PLAYERS)
    }
    roster = tuple(
        derive_bootstrap_record(p, PlayerSportingBootstrapPolicy())
        for p in biographies.values()
    )
    initial_roster = roster
    matches = ()
    batches = []
    week = RunWeekPosition(
        calendar=plan.calendar,
        season_index=0,
        week=plan.source.source_event.season_week,
    )
    while True:
        progress = project_knockout_progress(plan=plan, matches=matches)
        if not progress.ready_matches:
            assert progress.champion_player_id is not None
            return plan, matches, tuple(batches), initial_roster, roster
        # This test deliberately plays the full current ready wave from one frozen
        # population snapshot. Production slot/day scheduling is a separate owner.
        snapshot = canonical_hash(
            {
                "plan": plan.fingerprint,
                "players": [p.model_dump(mode="json") for p in roster],
                "accepted": [m.match_id for m in matches],
            }
        )
        slot = SimpleNamespace(
            run_id=plan.source.draw.run_id,
            branch_id=plan.source.draw.branch_id,
            week=week,
            players=roster,
            snapshot_fingerprint=snapshot,
            source_health_fingerprint="4" * 64,
        )
        records = {p.player_id: p for p in roster}
        made = []
        for index, ready in enumerate(progress.ready_matches, len(matches) + 1):
            projections = []
            for pid in ready.player_ids:
                profile = biographies[pid]
                projections.append(
                    project_player(
                        records[pid],
                        source_sporting_fingerprint=snapshot,
                        policy=CanonicalMatchInputProjectionPolicy(),
                        profile_source_fingerprint=profile.source_generation_fingerprint,
                        profile_provenance="Explicit feeder kernel test population, no generated results",
                        age=profile.player.age,
                        name=profile.player.name,
                        nationality=profile.player.nationality,
                        play_style=profile.player.play_style,
                        archetype=profile.player.archetype,
                        hidden_career_traits=profile.player.hidden_career_traits,
                    )
                )
            item = SimpleNamespace(
                match_id=ready.match_id,
                seed=ready.seed,
                sequence=index,
                source_saved_head=plan.source_saved_revision_id,
                projections=tuple(projections),
                health=EffectiveMatchHealthSnapshot(
                    player_profiles=tuple(
                        project_player_health(PlayerHealthProfile(player_id=pid))
                        for pid in ready.player_ids
                    )
                ),
            )
            made.append(calculate_match(slot, item))
        states = tuple(
            CalendarMatchPlayerState(
                player_id=p.player_id,
                current_form=p.current_form,
                match_sharpness=p.match_sharpness,
                long_term_fatigue=p.long_term_fatigue,
            )
            for p in roster
        )
        assert advance_played_slot(
            states, tuple(made), CalendarMatchStatePolicy()
        ) == advance_played_slot(
            states, tuple(reversed(made)), CalendarMatchStatePolicy()
        )
        batches.append((tuple(made), snapshot, roster))
        roster = terminal_players(roster, made)
        matches += tuple(made)


@pytest.fixture(scope="module")
def games(fax_source, ranking):
    return {
        size: played(feeder_plan(fax_source, ranking, size, authored_points=True))
        for size in (24, 32)
    }


def test_all_original_editions_resolve_byes_without_creating_matches(
    fax_source, ranking
):
    for event in fax_source[0].events:
        inputs = fax_inputs.in_memory_input(event, ranking)
        draw = TournamentDrawAuthorityBuilder.build(
            draw_input=inputs, command_id="draw"
        )
        plan = freeze_knockout_feeder_plan(
            source=fax_inputs.package_draw(event, inputs, draw),
            source_saved_revision_id="owned-Saved-source",
            source_saved_content_hash="3" * 64,
            calendar=RunCalendar(61, 37, 2000, 50),
        )
        topology = plan.topology
        assert len(topology.plans) == (35 if event.main_draw_size == 24 else 51)
        assert len(topology.bye_match_ids) == 8
        initial = project_knockout_progress(plan=plan, matches=())
        assert len(initial.bye_advances) == 8
        assert initial.main_blocked_by_qualification
        assert all(m.draw_type == "qualification" for m in initial.ready_matches)
        assert not initial.qualification_winners and initial.champion_player_id is None
        assert (
            CanonicalKnockoutFeederPlan.model_validate_json(plan.model_dump_json())
            == plan
        )


@pytest.mark.parametrize("size, count", [(24, 35), (32, 51)])
def test_actual_q_and_main_matches_feed_real_winners_without_bye_results(
    games, size, count
):
    plan, matches, batches, initial, terminal = games[size]
    done = project_knockout_progress(plan=plan, matches=matches)
    assert len(matches) == count and not done.ready_matches
    assert done.champion_player_id == next(
        m.result.winner_player_id
        for m in matches
        if m.match_id == plan.topology.terminal_group_id
    )
    assert (
        len(done.qualification_winners) == 4 and not done.main_blocked_by_qualification
    )
    assert set(done.accepted_match_ids).isdisjoint(plan.topology.bye_match_ids)
    qfinals = {
        b.section_id: max(b.nodes, key=lambda n: n.round_number).node_id
        for b in plan.source.draw.qualification_brackets
    }
    for q, winner in done.qualification_winners:
        assert winner == next(
            m.result.winner_player_id for m in matches if m.match_id == qfinals[q]
        )
    by_id = {m.match_id: m for m in matches}
    for promotion in plan.topology.qualifier_promotions:
        target = by_id[promotion.target_match_id]
        expected = by_id[promotion.source_match_id].result.winner_player_id
        actual = (
            target.result.player_a_id
            if promotion.target_side == "top"
            else target.result.player_b_id
        )
        assert actual == expected
    assert len(plan.source.draw.main.qualifier_placeholder_slots) == 4
    assert all(
        m.result.rally_log.events and m.result.timeline_log and m.result.stamina_log
        for m in matches
    )
    assert (
        project_knockout_progress(plan=plan, matches=tuple(reversed(matches))) == done
    )
    for batch, snapshot, before in batches:
        assert {m.source_checkpoint_fingerprint for m in batch} == {snapshot}
        by_player = {p.player_id: p for p in before}
        for m in batch:
            for p in m.canonical_projections:
                assert (p.current_form, p.match_sharpness, p.long_term_fatigue) == (
                    by_player[p.player_id].current_form,
                    by_player[p.player_id].match_sharpness,
                    by_player[p.player_id].long_term_fatigue,
                )
    initial_by_id = {p.player_id: p for p in initial}
    entrants = set(
        plan.source.draw_input.direct_main_player_ids
        + plan.source.draw_input.wild_card_player_ids
        + plan.source.draw_input.qualification_player_ids
    )
    assert all(
        p == initial_by_id[p.player_id] for p in terminal if p.player_id not in entrants
    )


@pytest.mark.parametrize("size", [24, 32])
def test_ranked_projection_uses_played_results_and_frozen_stage_awards(games, size):
    plan, matches, _, _, _ = games[size]
    projection = prepare_native_canonical_ranked_awards(plan=plan, matches=matches)
    result, awards = projection.result, projection.awards
    assert result.match_package_fingerprint is None
    assert result.native_feeder_plan_fingerprint == plan.fingerprint
    assert type(result).model_validate_json(result.model_dump_json()) == result
    assert awards.tournament_result_fingerprint == result.fingerprint
    final = next(match for match in matches if match.match_id == plan.topology.terminal_group_id)
    assert result.champion_player_id == final.result.winner_player_id
    assert result.finalist_player_id == final.result.loser_player_id
    expected_records = {match.match_id: match.fingerprint for match in matches}
    assert {
        row.match_id: row.result_fingerprint for row in result.matches if row.scoreline != "BYE"
    } == expected_records
    assert {
        row.match_id: row.winner_player_id for row in result.matches if row.scoreline == "BYE"
    } == dict(plan.topology.bye_winners)
    assert sum(player.wins for player in result.players) == len(matches)
    assert sum(player.losses for player in result.players) == len(matches)
    award_by_player = {award.player_id: award for award in awards.awards}
    assert len(result.qualification_winner_ids) == 4
    table = plan.source.source_event.ranking_points_table
    for player_id in result.qualification_winner_ids:
        award = award_by_player[player_id]
        assert award.qualification_point_stage == "qualification_winner"
        assert award.qualification_points_awarded == 17
        assert award.ranking_points_awarded == table[award.reached_stage] + 17
    if size == 32:
        first_round = [
            award for award in awards.awards if award.reached_stage == "qualification_round"
        ]
        assert first_round and all(award.ranking_points_awarded == 0 for award in first_round)
    else:
        assert prepare_native_canonical_ranked_awards(
            plan=plan, matches=tuple(reversed(matches))
        ) == projection


def test_ranked_projection_rejects_incomplete_results_and_original_point_gap(
    games, fax_source, ranking
):
    plan, matches, _, _, _ = games[24]
    with pytest.raises(ValueError, match="every executable match"):
        prepare_native_canonical_ranked_awards(plan=plan, matches=matches[:-1])
    original = feeder_plan(fax_source, ranking, 24)
    with pytest.raises(ValueError, match="missing=.*qualification_winner"):
        prepare_native_canonical_ranked_awards(plan=original, matches=())


def test_no_main_match_even_direct_opponents_before_all_four_q_finals(games):
    plan, matches, _, _, _ = games[32]
    q = tuple(m for m in matches if ":qualification:" in m.match_id)
    section_finals = {
        max(b.nodes, key=lambda n: n.round_number).node_id
        for b in plan.source.draw.qualification_brackets
    }
    q_winners = {m.result.winner_player_id for m in q if m.match_id in section_finals}
    main = next(
        m
        for m in matches
        if ":main:" in m.match_id
        and {m.result.player_a_id, m.result.player_b_id}.isdisjoint(q_winners)
    )
    with pytest.raises(ValueError, match="complete Qualification"):
        project_knockout_progress(plan=plan, matches=(*q[:-1], main))


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "bye",
        "foreign",
        "seed",
        "owner",
        "saved",
        "calendar",
        "feeder",
        "sequence",
        "same_snapshot",
    ],
)
def test_rejects_detached_out_of_order_and_forged_evidence(games, fault):
    plan, all_matches, batches, _, _ = games[32]
    matches = list(all_matches)
    if fault == "duplicate":
        matches.append(matches[0])
    elif fault == "bye":
        matches[0] = matches[0].model_copy(
            update={"match_id": plan.topology.bye_match_ids[0]}
        )
    elif fault == "foreign":
        matches[0] = matches[0].model_copy(update={"match_id": "other:main:R1-N1"})
    elif fault == "seed":
        matches[0] = matches[0].model_copy(update={"seed": matches[0].seed + 1})
    elif fault == "owner":
        matches[0] = matches[0].model_copy(update={"branch_id": "other"})
    elif fault == "saved":
        matches[0] = matches[0].model_copy(update={"source_saved_head": "other"})
    elif fault == "calendar":
        matches[0] = matches[0].model_copy(
            update={
                "week": matches[0].week.model_copy(
                    update={"calendar": RunCalendar(52, 37, 2000, 50)}
                )
            }
        )
    elif fault == "feeder":
        matches = [all_matches[-1]]
    elif fault == "sequence":
        matches[1] = matches[1].model_copy(update={"sequence": matches[0].sequence})
    else:
        # Keep only a dependent round with all its actual prior matches, but
        # substitute a predecessor snapshot. Evidence validation must reject it.
        later = batches[1][0][0]
        index = next(i for i, m in enumerate(matches) if m.match_id == later.match_id)
        matches[index] = later.model_copy(
            update={"source_checkpoint_fingerprint": batches[0][1]}
        )
    with pytest.raises(ValueError):
        project_knockout_progress(plan=plan, matches=tuple(matches))


def test_caller_mutation_cannot_change_a_prepared_plan(fax_source, ranking):
    plan = feeder_plan(fax_source, ranking, 32)
    source = plan.source.model_copy(deep=True)
    frozen = freeze_knockout_feeder_plan(
        source=source,
        source_saved_revision_id="saved",
        source_saved_content_hash="3" * 64,
        calendar=plan.calendar,
    )
    before = frozen.model_dump_json()
    source.source_event.event_name = "edited after preparation"
    assert frozen.model_dump_json() == before
    frozen.source.source_event.event_name = "nested mutation"
    with pytest.raises(ValueError, match="fingerprint changed"):
        project_knockout_progress(plan=frozen, matches=())


def test_match_seeds_do_not_depend_on_revision_or_command_labels(fax_source, ranking):
    plan = feeder_plan(fax_source, ranking, 32)
    other = plan.model_copy(
        update={
            "source_saved_revision_id": "new-head",
            "source_saved_content_hash": "5" * 64,
        }
    )
    for item in plan.topology.plans:
        assert plan.match_seed(item.match_id) == other.match_seed(item.match_id)
    with pytest.raises(ValueError, match="never BYE"):
        plan.match_seed(plan.topology.bye_match_ids[0])


def rerun(record, batch_roster, *, snapshot=None, reverse_players=False):
    """Generate genuine alternate-context evidence, never edit a winner label."""
    slot = SimpleNamespace(
        run_id=record.run_id,
        branch_id=record.branch_id,
        week=record.week,
        players=batch_roster,
        snapshot_fingerprint=snapshot or record.source_checkpoint_fingerprint,
        source_health_fingerprint=record.source_health_fingerprint,
    )
    item = SimpleNamespace(
        match_id=record.match_id,
        seed=record.seed,
        sequence=record.sequence,
        source_saved_head=record.source_saved_head,
        projections=tuple(reversed(record.canonical_projections))
        if reverse_players
        else record.canonical_projections,
        health=(
            EffectiveMatchHealthSnapshot(
                player_profiles=tuple(reversed(record.effective_health.player_profiles))
            )
            if reverse_players
            else record.effective_health
        ),
    )
    return calculate_match(slot, item)


def test_valid_engine_result_with_wrong_ordered_opponents_is_not_a_feeder_result(games):
    plan, matches, batches, _, _ = games[32]
    wrong = rerun(matches[0], batches[0][2], reverse_players=True)
    wrong.validate_evidence()  # valid engine/anchor/context, wrong Draw participants
    with pytest.raises(ValueError, match="exact feeder opponents"):
        project_knockout_progress(plan=plan, matches=(wrong,))


def test_valid_engine_result_cannot_play_a_dependent_round_on_the_feeders_snapshot(
    games,
):
    plan, _matches, batches, _, _ = games[32]
    target = batches[1][0][0]
    wrong = rerun(target, batches[1][2], snapshot=batches[0][1])
    wrong.validate_evidence()
    prefix = batches[0][0] + (wrong,)
    with pytest.raises(ValueError, match="Dependent rounds cannot share"):
        project_knockout_progress(plan=plan, matches=prefix)


def test_missing_main_feeder_is_rejected_after_qualification_is_complete(games):
    plan, matches, _, _, _ = games[24]
    final_plan = next(
        p for p in plan.topology.plans if p.match_id == plan.topology.terminal_group_id
    )
    missing_id = final_plan.participant_sources[0].removeprefix("winner:")
    with pytest.raises(ValueError, match="unresolved feeder"):
        project_knockout_progress(
            plan=plan, matches=tuple(m for m in matches if m.match_id != missing_id)
        )


def test_unrelated_calendar_metadata_does_not_reseed_matches(fax_source, ranking):
    plan = feeder_plan(fax_source, ranking, 32)
    changed_source = plan.source.model_copy(deep=True)
    changed_source.source_event.event_name = "Renamed, same sporting match identities"
    other = freeze_knockout_feeder_plan(
        source=changed_source,
        source_saved_revision_id="later-saved",
        source_saved_content_hash="6" * 64,
        calendar=plan.calendar,
    )
    assert other.fingerprint != plan.fingerprint
    for match in plan.topology.plans:
        assert other.match_seed(match.match_id) == plan.match_seed(match.match_id)


@pytest.mark.parametrize(
    "kind, expected",
    [
        (
            "ordinary",
            "f2124fb6f75904f12d7da900b2b001cc14c7990224e5f80b6893435072d381c2",
        ),
        ("bye", "54a4461d8e031d5182b62ae03e9da780b1a83df5441d2145d9d27f7b0013391e"),
        (
            "single_q",
            "1801c4432db703354f7d0a59656556af1dbe23c3fc6c67d40fec0e60826a9aff",
        ),
        ("four_q", "c1572e6baf4288ec909d9986349a3d2c2973eb1bdb309ef1dc060a48e5054fee"),
    ],
)
def test_legacy_topology_fingerprints_keep_exact_prechange_payloads(kind, expected):
    from beta_engine.application.canonical_tournament_topology import (
        project_canonical_draw_to_match_topology,
    )
    from tests.application import test_canonical_tournament_topology as legacy

    inputs = (
        legacy._multi_q_draw_input()
        if kind == "four_q"
        else legacy._draw_input(
            with_bye=kind == "bye", with_qualification=kind == "single_q"
        )
    )
    draw = TournamentDrawAuthorityBuilder.build(draw_input=inputs, command_id="draw")
    result = project_canonical_draw_to_match_topology(
        draw=draw, package=legacy._package(draw)
    )
    # Independently computed using the original projector at merged base 7620b89a.
    assert result.fingerprint == expected
