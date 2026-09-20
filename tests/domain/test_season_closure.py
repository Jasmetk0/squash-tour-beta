import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.season_closing import calculate_season_closing_ranking
from beta_engine.domain.season_closure import (
    SeasonScopedStatisticSnapshot,
    bind_season_closure_marker,
    build_season_closure_package,
)


def _closing():
    week = RankingWeek(season_index=0, week=61)
    players = (
        OfficialRankingPlayer(
            player_id="A",
            tie_break_token="token-A",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
        OfficialRankingPlayer(
            player_id="B",
            tie_break_token="token-B",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ),
    )
    policy = OfficialRankingPolicy(policy_id="season-2000-policy", best_n=15)
    predecessor = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=week,
        policy=policy,
        players=players,
        results=(),
    )
    return calculate_season_closing_ranking(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        policy=policy,
        players=players,
        results=(),
        predecessor=predecessor,
    )


def test_season_closure_package_is_lightweight_and_revision_unbound():
    closing = _closing()
    package = build_season_closure_package(closing_ranking=closing)

    assert package.summary.closing_ranking_fingerprint == closing.fingerprint
    assert package.summary.season_scoped_statistics == ()
    assert package.marker.closing_ranking_fingerprint == closing.fingerprint
    assert package.marker.season_summary_fingerprint == package.summary.fingerprint
    assert [item.rule_kind for item in package.marker.rule_versions] == [
        "official_ranking_policy"
    ]
    assert package.marker.rule_versions[0].rule_id == closing.policy.policy_id
    assert "final_saved_revision_id" not in package.marker.model_dump(mode="json")

    marker = bind_season_closure_marker(
        package.marker,
        final_saved_revision_id="revision-after-season-transition",
    )
    assert marker.final_saved_revision_id == "revision-after-season-transition"
    assert marker.season_summary_fingerprint == package.summary.fingerprint
    assert marker.closing_ranking_fingerprint == closing.fingerprint


def test_season_summary_freezes_only_canonical_explicit_components():
    closing = _closing()
    beta = SeasonScopedStatisticSnapshot(
        component_id="beta",
        component_schema_version="beta.v1",
        payload_json='{"value":2}',
    )
    alpha = SeasonScopedStatisticSnapshot(
        component_id="alpha",
        component_schema_version="alpha.v1",
        payload_json='{"value":1}',
    )
    package = build_season_closure_package(
        closing_ranking=closing,
        season_scoped_statistics=(beta, alpha),
    )
    assert [item.component_id for item in package.summary.season_scoped_statistics] == [
        "alpha",
        "beta",
    ]

    with pytest.raises(ValueError, match="canonical"):
        SeasonScopedStatisticSnapshot(
            component_id="bad",
            component_schema_version="bad.v1",
            payload_json='{ "value": 1 }',
        )

    with pytest.raises(ValueError, match="canonical and unique"):
        build_season_closure_package(
            closing_ranking=closing,
            season_scoped_statistics=(alpha, alpha),
        )
