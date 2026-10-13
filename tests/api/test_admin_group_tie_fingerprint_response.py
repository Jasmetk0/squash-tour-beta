"""The Admin tie reviewer must receive the exact server-computed case fingerprint.

A client must not invent a fallback ordering, recompute incomplete evidence,
or submit a stale tie case without authority identity.
"""
from __future__ import annotations

import pytest

from beta_engine.api.routers.admin_tournament_formats import TournamentGroupTieResolutionState
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsTieCase,
)

pytestmark = pytest.mark.pr_critical


def test_group_tie_review_response_exposes_exact_case_fingerprint():
    case = TournamentGroupStandingsTieCase(
        group_index=1,
        reason="all_sporting_tie_breaks_exhausted",
        player_ids=("athlete-a", "athlete-b"),
        source_match_results=(("group-match-1", "a" * 64),),
    )
    result = TournamentGroupTieResolutionState(
        run_id="run-real",
        branch_id="branch-real",
        event_id="event-real",
        unresolved_case=case,
        unresolved_case_fingerprint=case.fingerprint,
        resolutions=(),
    )
    payload = result.model_dump(mode="json")
    assert payload["unresolved_case_fingerprint"] == case.fingerprint
    assert payload["unresolved_case"]["player_ids"] == ["athlete-a", "athlete-b"]
    assert len(payload["unresolved_case_fingerprint"]) == 64
    assert payload["resolutions"] == []


def test_nonexistent_tie_exposes_null_fingerprint_not_fabricated_case():
    result = TournamentGroupTieResolutionState(
        run_id="run-real",
        branch_id="branch-real",
        event_id="event-real",
        unresolved_case=None,
        unresolved_case_fingerprint=None,
        resolutions=(),
    )
    payload = result.model_dump(mode="json")
    assert payload["unresolved_case"] is None
    assert payload["unresolved_case_fingerprint"] is None
