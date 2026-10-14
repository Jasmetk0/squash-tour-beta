"""Focused adapter scope test; full authentic rally search belongs to Chromium CI.

Avoid repeating the expensive six-match MatchEngine seed scan in Fast CI.
The real browser job uses the unchanged genuine evidence generator.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db import (
    tournament_group_standings_authority as standings_module,
    tournament_group_tie_resolution_authority as tie_module,
)
from scripts.real_group_cyclic_tie_browser_checks import (
    install_real_match_engine_cyclic_fixture,
)
from tests.domain.test_tournament_group_standings_authority import schedule_four
from tests.infrastructure import real_four_player_cyclic_tie_evidence as generator

pytestmark = pytest.mark.pr_critical


def test_cyclic_matchengine_input_adapter_enforces_exact_run_branch_and_event(
    tmp_path, monkeypatch,
):
    original_tie = tie_module.TournamentGroupMatchScheduleAuthorityStore
    original_standings = standings_module.TournamentGroupMatchScheduleAuthorityStore
    original_receipts = standings_module.TournamentGroupStandingsAuthorityStore._result_receipts
    match_evidence = tuple(f"real-match-evidence-{i}" for i in range(6))
    monkeypatch.setattr(
        generator, "_generate_four_player_cyclic_receipts",
        lambda: (schedule_four(), match_evidence,
                 SimpleNamespace(player_ids=("A", "B", "C"))),
    )
    try:
        install_real_match_engine_cyclic_fixture(tmp_path)
        fixture_store = tie_module.TournamentGroupMatchScheduleAuthorityStore(None)
        kwargs = {"run_id": "run-1", "branch_id": "branch-1", "event_id": "event-1"}
        assert fixture_store.get(**kwargs) is None, "No Run scope was yet supplied"
        (tmp_path / "real-cyclic-tie-scope.json").write_text(json.dumps(kwargs))
        for key in kwargs:
            altered = {**kwargs, key: "foreign"}
            assert fixture_store.get(**altered) is None
        scoped = fixture_store.get(**kwargs)
        assert scoped is not None
        assert (scoped.run_id, scoped.branch_id, scoped.event_id) == (
            "run-1", "branch-1", "event-1"
        )
        assert scoped.group_size == 4 and len(scoped.matches) == 6
        assert tuple(m.match_id for m in scoped.matches) == tuple(
            m.match_id for m in schedule_four().matches
        )
        standings_store = standings_module.TournamentGroupStandingsAuthorityStore(None)
        assert standings_store._result_receipts() == match_evidence
    finally:
        # The fixture must never contaminate other production authority tests.
        tie_module.TournamentGroupMatchScheduleAuthorityStore = original_tie
        standings_module.TournamentGroupMatchScheduleAuthorityStore = original_standings
        standings_module.TournamentGroupStandingsAuthorityStore._result_receipts = original_receipts
