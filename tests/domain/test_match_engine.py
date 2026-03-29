from __future__ import annotations

from statistics import mean

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchTerminationReason,
    RetirementRule,
)
from beta_engine.domain.players import HiddenCareerTraits, Player
from beta_engine.infrastructure.world_config import load_player_identity_config


def _player(
    *,
    player_id: str,
    base: int,
    style: str = "tempo-controller",
    archetype: str = "all-court tactician",
    clutch_delta: int = 0,
) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=base,
        movement=base,
        physical=base,
        mental=max(1, min(99, base + clutch_delta)),
        consistency=base,
        clutch=max(1, min(99, base + clutch_delta)),
        recovery=base,
        play_style=style,
        archetype=archetype,
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _context(match_id: str, player_a: Player, player_b: Player) -> MatchContext:
    return MatchContext(
        match_id=match_id,
        player_a=MatchParticipantContext(player=player_a),
        player_b=MatchParticipantContext(player=player_b),
    )


def test_match_engine_replay_same_seed_same_inputs_same_result() -> None:
    a = _player(player_id="A", base=84)
    b = _player(player_id="B", base=81, style="counter-punching", archetype="durable grinder")
    context = _context("match-replay", a, b)

    result_a = MatchEngine(rng=DeterministicRng(777)).simulate(context)
    result_b = MatchEngine(rng=DeterministicRng(777)).simulate(context)

    assert result_a.model_dump() == result_b.model_dump()


def test_identity_config_vocabularies_are_all_reachable_by_matchup_tables() -> None:
    identity = load_player_identity_config()

    style_vocab = set(identity.play_styles)
    style_left = {left for left, _ in MatchEngine.STYLE_MATCHUP_EDGES}
    style_right = {right for _, right in MatchEngine.STYLE_MATCHUP_EDGES}

    archetype_vocab = set(identity.archetypes)
    archetype_left = {left for left, _ in MatchEngine.ARCHETYPE_MATCHUP_EDGES}
    archetype_right = {right for _, right in MatchEngine.ARCHETYPE_MATCHUP_EDGES}

    assert style_vocab == style_left == style_right
    assert archetype_vocab == archetype_left == archetype_right


def test_matchup_adjustment_is_non_zero_for_generated_vocab_values() -> None:
    adj_styles, _ = MatchEngine._style_and_archetype_adjustment(
        "attacking",
        "retrieving",
        "all-court tactician",
        "all-court tactician",
    )
    adj_archetypes, _ = MatchEngine._style_and_archetype_adjustment(
        "tempo-controller",
        "tempo-controller",
        "quick interceptor",
        "late-blooming worker",
    )

    assert adj_styles != 0.0
    assert adj_archetypes != 0.0


def test_stronger_player_wins_more_often_over_deterministic_seed_samples() -> None:
    strong = _player(player_id="STRONG", base=90)
    weak = _player(player_id="WEAK", base=68)

    strong_wins = 0
    samples = 180
    for seed in range(10, 10 + samples):
        context = _context(f"m-{seed}", strong, weak)
        result = MatchEngine(rng=DeterministicRng(seed)).simulate(context)
        if result.winner_player_id == strong.player_id:
            strong_wins += 1

    assert strong_wins > int(samples * 0.7)


def test_close_players_create_tighter_set_score_patterns_than_mismatches() -> None:
    close_a = _player(player_id="CLOSE-A", base=85, clutch_delta=2)
    close_b = _player(player_id="CLOSE-B", base=84, clutch_delta=1)
    mismatch_a = _player(player_id="MIS-A", base=92)
    mismatch_b = _player(player_id="MIS-B", base=62)

    close_avg_margin: list[float] = []
    mismatch_avg_margin: list[float] = []

    for seed in range(200, 260):
        close_result = MatchEngine(rng=DeterministicRng(seed)).simulate(_context(f"close-{seed}", close_a, close_b))
        mismatch_result = MatchEngine(rng=DeterministicRng(seed)).simulate(
            _context(f"mis-{seed}", mismatch_a, mismatch_b)
        )

        close_margins = [abs(s.winner_games - s.loser_games) for s in close_result.sets]
        mismatch_margins = [abs(s.winner_games - s.loser_games) for s in mismatch_result.sets]

        close_avg_margin.append(mean(close_margins))
        mismatch_avg_margin.append(mean(mismatch_margins))

    assert mean(close_avg_margin) < mean(mismatch_avg_margin)


def test_retirement_path_is_explicit_and_deterministic() -> None:
    a = _player(player_id="RET-A", base=84)
    b = _player(player_id="RET-B", base=83)
    context = MatchContext(
        match_id="retired-match",
        player_a=MatchParticipantContext(player=a),
        player_b=MatchParticipantContext(player=b),
        retirement_rule=RetirementRule(
            enabled=True,
            retired_player_id=a.player_id,
            set_number=3,
        ),
    )

    result = MatchEngine(rng=DeterministicRng(31415)).simulate(context)

    assert result.termination_reason == MatchTerminationReason.RETIREMENT
    assert result.retired_player_id == a.player_id
    assert result.retired_at_set_start == 3
    assert result.winner_player_id == b.player_id
    assert len(result.sets) <= 2
