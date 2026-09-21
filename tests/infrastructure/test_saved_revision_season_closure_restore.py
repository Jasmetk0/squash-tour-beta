from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.season_closure import (
    ClosureRuleVersionRef,
    SeasonClosureMarkerCandidate,
    SeasonClosurePackage,
    SeasonSummarySnapshot,
    bind_season_closure_marker,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    install_saved_revision_season_closure,
    load_saved_revision_season_closure,
    rebind_saved_revision_season_closure,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _payload(revision_id: str) -> dict:
    week = RankingWeek(season_index=0, week=61)
    summary = SeasonSummarySnapshot(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        closing_ranking_fingerprint=HASH_A,
    )
    candidate = SeasonClosureMarkerCandidate(
        run_id="run",
        branch_id="branch",
        completed_week=week,
        season_summary_fingerprint=summary.fingerprint,
        closing_ranking_fingerprint=HASH_A,
        rule_versions=(
            ClosureRuleVersionRef(
                rule_kind="official_ranking_policy",
                rule_id="policy",
                fingerprint=HASH_B,
            ),
        ),
    )
    package = SeasonClosurePackage(summary=summary, marker=candidate)
    marker = bind_season_closure_marker(
        candidate,
        final_saved_revision_id=revision_id,
    )
    payload = {"content": {}}
    install_saved_revision_season_closure(
        payload,
        package=package,
        marker=marker,
    )
    return payload


def test_restore_rebinds_season_closure_to_new_saved_revision_identity() -> None:
    payload = _payload("historical-revision")
    historical = load_saved_revision_season_closure(
        payload,
        run_id="run",
        branch_id="branch",
        revision_id="historical-revision",
    )
    assert historical is not None
    historical_summary_fingerprint = historical.parsed_summary.fingerprint
    historical_marker_fingerprint = historical.parsed_marker.fingerprint

    rebound = rebind_saved_revision_season_closure(
        payload,
        run_id="run",
        branch_id="branch",
        source_revision_id="historical-revision",
        target_revision_id="restore-revision",
    )
    assert rebound is not None

    loaded = load_saved_revision_season_closure(
        payload,
        run_id="run",
        branch_id="branch",
        revision_id="restore-revision",
    )
    assert loaded is not None
    assert loaded.parsed_summary.fingerprint == historical_summary_fingerprint
    assert loaded.parsed_marker.final_saved_revision_id == "restore-revision"
    assert loaded.parsed_marker.fingerprint != historical_marker_fingerprint

    with pytest.raises(ValueError, match="identity mismatch"):
        load_saved_revision_season_closure(
            payload,
            run_id="run",
            branch_id="branch",
            revision_id="historical-revision",
        )


def test_restore_rebind_is_noop_without_season_closure_component() -> None:
    payload = {"content": {}}
    assert (
        rebind_saved_revision_season_closure(
            payload,
            run_id="run",
            branch_id="branch",
            source_revision_id="historical-revision",
            target_revision_id="restore-revision",
        )
        is None
    )
    assert payload == {"content": {}}
