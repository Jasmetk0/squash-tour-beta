"""Shared award provenance is computed once, without changing any point fact."""
from types import SimpleNamespace

import pytest

from beta_engine.domain.players.calendar_followup_points import (
    CalendarFollowupEightPointPolicy, CalendarFollowupPointPolicy, derive_followup_awards,
)

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("size", [4, 8])
def test_shared_tournament_provenance_is_hashed_once_per_award_derivation(size):
    pairs = [("a", "b"), ("c", "d"), ("a", "c")]
    stages = {"a": "champion", "b": "semifinal", "c": "finalist", "d": "semifinal"}
    policy_type = CalendarFollowupPointPolicy
    fields = {"category_label": "Reviewed", "champion": 100, "finalist": 60,
              "semifinal": 30, "validity_weeks": 52}
    if size == 8:
        pairs = [("a", "b"), ("c", "d"), ("e", "f"), ("g", "h"),
                 ("a", "c"), ("e", "g"), ("a", "e")]
        stages = {"a": "champion", "b": "quarterfinal", "c": "semifinal",
                  "d": "quarterfinal", "e": "finalist", "f": "quarterfinal",
                  "g": "semifinal", "h": "quarterfinal"}
        policy_type = CalendarFollowupEightPointPolicy
        fields["quarterfinal"] = 15

    class Source:
        entrant_ids = tuple(sorted(stages))
        matches = tuple(SimpleNamespace(result=SimpleNamespace(
            winner_player_id=winner, loser_player_id=loser,
        )) for winner, loser in pairs)
        prepared_policy = policy_type(**fields)
        hash_reads = 0

        @property
        def sporting_fingerprint(self):
            self.hash_reads += 1
            return "a" * 64

    source = Source()
    awards = derive_followup_awards(source)
    assert source.hash_reads == 1
    assert [(a.player_id, a.reached_stage, a.main_points) for a in awards] == [
        (pid, stages[pid], getattr(source.prepared_policy, stages[pid])) for pid in sorted(stages)
    ]
    assert all(a.source_tournament_fingerprint == "a" * 64 for a in awards)
    assert all(a.source_policy_fingerprint == source.prepared_policy.fingerprint for a in awards)
